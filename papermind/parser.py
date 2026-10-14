"""PDF parsing + section-aware chunking."""
from __future__ import annotations

import hashlib
import re
from bisect import bisect_right
from dataclasses import dataclass

import pymupdf  # PyMuPDF
import requests

from .config import CHUNK_OVERLAP, CHUNK_SIZE

KNOWN_HEADINGS = {
    "abstract", "introduction", "related work", "background", "method", "methods",
    "methodology", "approach", "experiments", "experimental setup", "results",
    "discussion", "conclusion", "conclusions", "limitations", "acknowledgements",
    "acknowledgments", "references", "appendix",
}
NUMBERED_HEADING = re.compile(r"^(\d+(\.\d+){0,2}\.?|[A-Z]\.)\s+[A-Z][^.!?]{1,80}$")
ARXIV_ID = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")


@dataclass
class Chunk:
    idx: int
    text: str
    section: str
    page: int


@dataclass
class ParsedPaper:
    paper_id: str
    title: str
    n_pages: int
    chunks: list[Chunk]


def paper_id_for(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()[:12]


def is_heading(line: str) -> bool:
    s = line.strip()
    if len(s) > 90 or len(s.split()) > 12:
        return False
    if s.lower().rstrip(":") in KNOWN_HEADINGS:
        return True
    return bool(NUMBERED_HEADING.match(s))


def split_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[tuple[int, str]]:
    """Split on whitespace boundaries. Returns (start_offset, chunk_text) pairs."""
    out: list[tuple[int, str]] = []
    start, n = 0, len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            cut = text.rfind(" ", start + size // 2, end)
            if cut != -1:
                end = cut
        piece = text[start:end].strip()
        if len(piece) > 40:
            out.append((start, piece))
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return out


def _title_from_largest_font(doc: pymupdf.Document) -> str:
    """Titles are usually the largest text on page 1 and may wrap over several lines."""
    try:
        blocks = doc[0].get_text("dict")["blocks"]
    except Exception:  # noqa: BLE001
        return ""
    lines: list[tuple[float, str]] = []
    for b in blocks:
        for ln in b.get("lines", []):
            spans = [s for s in ln["spans"] if s["text"].strip()]
            if spans:
                lines.append((max(s["size"] for s in spans), " ".join(s["text"].strip() for s in spans)))
    if not lines:
        return ""
    top = max(size for size, _ in lines)
    parts, started = [], False
    for size, text in lines:
        if size >= top - 0.5:
            parts.append(text)
            started = True
        elif started:
            break
    title = re.sub(r"\s+", " ", " ".join(parts)).strip()
    return title if 5 < len(title) <= 250 else ""


def _guess_title(doc: pymupdf.Document, first_line: str, filename: str) -> str:
    meta = ((doc.metadata or {}).get("title") or "").strip()
    bad = meta.lower().startswith("microsoft word") or meta.lower().endswith((".pdf", ".tex", ".dvi"))
    if len(meta) > 5 and not bad:
        return meta[:200]
    big = _title_from_largest_font(doc)
    if big:
        return big[:200]
    if first_line:
        return first_line[:200]
    return filename.rsplit(".", 1)[0]


def parse_pdf(data: bytes, filename: str = "paper.pdf") -> ParsedPaper:
    doc = pymupdf.open(stream=data, filetype="pdf")
    sections: list[dict] = []
    cur = {"title": "Front matter", "text": "", "marks": [(0, 1)]}
    first_line = ""

    for pno, page in enumerate(doc, start=1):
        for raw in page.get_text("text").splitlines():
            s = re.sub(r"\s+", " ", raw).strip()
            if not s:
                continue
            if pno == 1 and not first_line:
                first_line = s
            if is_heading(s):
                sections.append(cur)
                cur = {"title": s, "text": "", "marks": [(0, pno)]}
                continue
            cur["marks"].append((len(cur["text"]), pno))
            if len(cur["text"]) > 1 and cur["text"].endswith("-") and cur["text"][-2].isalpha():
                cur["text"] = cur["text"][:-1] + s + " "  # re-join hyphenated words
            else:
                cur["text"] += s + " "
    sections.append(cur)

    chunks: list[Chunk] = []
    for sec in sections:
        if sec["title"].lower().rstrip(":") == "references":
            continue  # reference lists pollute retrieval
        offsets = [m[0] for m in sec["marks"]]
        for start, piece in split_text(sec["text"]):
            page = sec["marks"][max(bisect_right(offsets, start) - 1, 0)][1]
            chunks.append(Chunk(idx=len(chunks), text=piece, section=sec["title"], page=page))

    return ParsedPaper(
        paper_id=paper_id_for(data),
        title=_guess_title(doc, first_line, filename),
        n_pages=doc.page_count,
        chunks=chunks,
    )


def fetch_arxiv(ref: str) -> tuple[bytes, str]:
    """Download a PDF from an arXiv URL or bare id like 1706.03762."""
    m = ARXIV_ID.search(ref.strip())
    if not m:
        raise ValueError("Couldn't find an arXiv id (expected something like 1706.03762).")
    aid = m.group(1) + (m.group(2) or "")
    resp = requests.get(
        f"https://arxiv.org/pdf/{aid}",
        timeout=60,
        headers={"User-Agent": "papermind/0.1"},
    )
    resp.raise_for_status()
    return resp.content, f"arxiv-{aid}.pdf"

"""Upload -> parse -> chunk -> embed -> store."""
from __future__ import annotations

from . import db, store
from .parser import fetch_arxiv, paper_id_for, parse_pdf


def ingest_pdf(data: bytes, filename: str = "paper.pdf") -> tuple[dict, bool]:
    """Returns (paper_row, is_new). Re-uploading the same file is a no-op."""
    existing = db.get_paper(paper_id_for(data))
    if existing:
        return existing, False
    parsed = parse_pdf(data, filename)
    if not parsed.chunks:
        raise ValueError(
            "No extractable text found (is this a scanned PDF?). Run OCR first, e.g. with ocrmypdf."
        )
    store.add_chunks(parsed.paper_id, parsed.title, parsed.chunks)
    db.add_paper(parsed.paper_id, parsed.title, filename, parsed.n_pages, len(parsed.chunks))
    return db.get_paper(parsed.paper_id), True


def ingest_arxiv(ref: str) -> tuple[dict, bool]:
    data, filename = fetch_arxiv(ref)
    return ingest_pdf(data, filename)


def remove_paper(paper_id: str) -> None:
    store.delete_paper(paper_id)
    db.delete_paper(paper_id)

"""Groq-powered (open-source models) answering, summarizing and comparing."""
from __future__ import annotations

import logging

import groq
from groq import Groq

from . import store
from .config import LLM_MODEL, MAX_SUMMARY_CHARS, TOP_K
from .store import Hit

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq()  # reads GROQ_API_KEY
    return _client


log = logging.getLogger("papermind.llm")

# Groq retires models regularly. If the configured model is gone (HTTP 404), we pick the
# first of these that your account can actually use.
FALLBACK_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
_active_model = LLM_MODEL


def current_model() -> str:
    return _active_model


def _request(model: str, system: str, messages: list[dict], max_tokens: int) -> str:
    kwargs: dict = dict(
        model=model,
        max_tokens=max_tokens,
        temperature=0.2,
        messages=[{"role": "system", "content": system}, *messages],
    )
    if "gpt-oss" in model:
        # gpt-oss are reasoning models: keep reasoning short and leave room for it
        kwargs["max_tokens"] = max_tokens + 1000
        kwargs["extra_body"] = {"reasoning_effort": "low"}
    resp = _get_client().chat.completions.create(**kwargs)
    return (resp.choices[0].message.content or "").strip()


def _chat(system: str, messages: list[dict], max_tokens: int = 1500) -> str:
    global _active_model
    try:
        return _request(_active_model, system, messages, max_tokens)
    except groq.NotFoundError:
        available = sorted(m.id for m in _get_client().models.list().data)
        for candidate in FALLBACK_MODELS:
            if candidate in available and candidate != _active_model:
                log.warning("Model %s unavailable, switching to %s", _active_model, candidate)
                _active_model = candidate
                return _request(candidate, system, messages, max_tokens)
        raise RuntimeError(
            f"Groq model '{_active_model}' is not available to your account. "
            f"Models you can use: {', '.join(available)}. "
            "Set LLM_MODEL in your .env to one of them."
        ) from None


def format_context(hits: list[Hit]) -> str:
    blocks = []
    for i, h in enumerate(hits, start=1):
        blocks.append(f"[{i}] {h.title} | section: {h.section} | page {h.page}\n{h.text}")
    return "\n\n".join(blocks)


SYSTEM_QA = (
    "You are a careful research assistant. Answer using ONLY the numbered excerpts provided. "
    "Cite every claim with its source number, like [1] or [2][3]; end every sentence that states "
    "a fact with a citation. If the excerpts don't contain "
    "the answer, say so plainly instead of guessing. Be concise and precise, and keep numbers, "
    "equations and terminology exactly as written in the excerpts."
)


def answer(question: str, hits: list[Hit], history: list[dict] | None = None) -> str:
    if not hits:
        return "I couldn't find any content to answer from. Upload a paper and select it first."
    messages = list(history or [])
    messages.append(
        {
            "role": "user",
            "content": f"Excerpts:\n\n{format_context(hits)}\n\nQuestion: {question}",
        }
    )
    return _chat(SYSTEM_QA, messages)


SYSTEM_SUMMARY = (
    "You summarize research papers for busy readers. Be faithful to the text; do not invent "
    "results. Use this exact structure in markdown:\n"
    "**TL;DR** (2-3 sentences)\n**Problem**\n**Method**\n**Key results** (bullets with numbers)\n"
    "**Limitations**\n**Why it matters**"
)


def summarize(paper_id: str) -> str:
    chunks = store.all_chunks(paper_id)
    if not chunks:
        return "Paper not found in the index."
    title = chunks[0].title
    parts, size, last_section = [], 0, None
    for c in chunks:
        header = f"\n## {c.section}\n" if c.section != last_section else ""
        last_section = c.section
        piece = header + c.text + "\n"
        if size + len(piece) > MAX_SUMMARY_CHARS:
            break
        parts.append(piece)
        size += len(piece)
    return _chat(
        SYSTEM_SUMMARY,
        [{"role": "user", "content": f"Paper: {title}\n\n{''.join(parts)}\n\nSummarize this paper."}],
        max_tokens=1800,
    )


SYSTEM_COMPARE = (
    "You compare research papers. Use ONLY the numbered excerpts. Cite sources like [1][4]. "
    "Structure: a one-paragraph overview, then a markdown table comparing the papers on the "
    "requested aspect (add rows such as problem, method, data, results, limitations where the "
    "excerpts support them; write 'not stated' when missing), then 3-5 bullets on key differences "
    "and when you'd prefer each approach."
)


def compare(paper_ids: list[str], aspect: str, k_per_paper: int = 5) -> tuple[str, list[Hit]]:
    hits: list[Hit] = []
    for pid in paper_ids:
        hits.extend(store.query(aspect, [pid], k=k_per_paper))
    if not hits:
        return "No content found for the selected papers.", []
    text = _chat(
        SYSTEM_COMPARE,
        [
            {
                "role": "user",
                "content": f"Excerpts:\n\n{format_context(hits)}\n\nCompare the papers on: {aspect}",
            }
        ],
        max_tokens=2000,
    )
    return text, hits


def ask(question: str, paper_ids: list[str], k: int = TOP_K, history: list[dict] | None = None):
    hits = store.query(question, paper_ids, k=k)
    return answer(question, hits, history), hits

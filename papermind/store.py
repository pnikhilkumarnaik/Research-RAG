"""Chroma vector store. Uses Chroma's built-in local embedding model (no extra API key).

To use Pinecone or a different embedding model, replace this module and keep
the same function signatures: add_chunks / query / all_chunks / delete_paper.
"""
from __future__ import annotations

from dataclasses import dataclass

import chromadb
from chromadb.utils import embedding_functions

from .config import CHROMA_DIR, TOP_K
from .parser import Chunk

_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
_ef = embedding_functions.DefaultEmbeddingFunction()  # all-MiniLM-L6-v2 via ONNX
_col = _client.get_or_create_collection(
    "papers", embedding_function=_ef, metadata={"hnsw:space": "cosine"}
)


@dataclass
class Hit:
    text: str
    paper_id: str
    title: str
    section: str
    page: int
    score: float  # cosine similarity, higher is better


def add_chunks(paper_id: str, title: str, chunks: list[Chunk]) -> None:
    if not chunks:
        return
    _col.upsert(
        ids=[f"{paper_id}:{c.idx}" for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[
            {"paper_id": paper_id, "title": title, "section": c.section, "page": c.page, "idx": c.idx}
            for c in chunks
        ],
    )


def _where(paper_ids: list[str] | None):
    if not paper_ids:
        return None
    if len(paper_ids) == 1:
        return {"paper_id": paper_ids[0]}
    return {"paper_id": {"$in": paper_ids}}


def query(question: str, paper_ids: list[str] | None = None, k: int = TOP_K) -> list[Hit]:
    total = _col.count()
    if total == 0:
        return []
    res = _col.query(
        query_texts=[question],
        n_results=min(k, total),
        where=_where(paper_ids),
    )
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        hits.append(
            Hit(
                text=doc,
                paper_id=meta["paper_id"],
                title=meta["title"],
                section=meta["section"],
                page=int(meta["page"]),
                score=round(1 - dist, 3),
            )
        )
    return hits


def all_chunks(paper_id: str) -> list[Hit]:
    res = _col.get(where={"paper_id": paper_id}, include=["documents", "metadatas"])
    rows = sorted(zip(res["documents"], res["metadatas"]), key=lambda r: r[1]["idx"])
    return [
        Hit(d, m["paper_id"], m["title"], m["section"], int(m["page"]), 1.0) for d, m in rows
    ]


def delete_paper(paper_id: str) -> None:
    _col.delete(where={"paper_id": paper_id})

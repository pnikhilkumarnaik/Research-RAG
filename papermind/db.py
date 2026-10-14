"""SQLite metadata + notes. Swap for PostgreSQL later (same queries, different driver)."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from .config import SQLITE_PATH


@contextmanager
def _conn():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                filename TEXT,
                n_pages INTEGER,
                n_chunks INTEGER,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id TEXT,
                text TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


init()


def add_paper(pid: str, title: str, filename: str, n_pages: int, n_chunks: int) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO papers (id, title, filename, n_pages, n_chunks) VALUES (?,?,?,?,?)",
            (pid, title, filename, n_pages, n_chunks),
        )


def get_paper(pid: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM papers WHERE id=?", (pid,)).fetchone()
    return dict(row) if row else None


def list_papers() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM papers ORDER BY added_at DESC").fetchall()
    return [dict(r) for r in rows]


def delete_paper(pid: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM papers WHERE id=?", (pid,))
        c.execute("DELETE FROM notes WHERE paper_id=?", (pid,))


def add_note(text: str, paper_id: str | None = None) -> int:
    with _conn() as c:
        cur = c.execute("INSERT INTO notes (paper_id, text) VALUES (?,?)", (paper_id, text))
        return cur.lastrowid


def list_notes(paper_id: str | None = None) -> list[dict]:
    q = (
        "SELECT n.*, p.title AS paper_title FROM notes n "
        "LEFT JOIN papers p ON p.id = n.paper_id"
    )
    args: tuple = ()
    if paper_id:
        q += " WHERE n.paper_id=?"
        args = (paper_id,)
    q += " ORDER BY n.created_at DESC, n.id DESC"
    with _conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def delete_note(note_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM notes WHERE id=?", (note_id,))


def export_notes_markdown() -> str:
    notes = list_notes()
    if not notes:
        return "# Research notes\n\n_No notes yet._\n"
    parts = ["# Research notes\n"]
    for n in notes:
        header = n["paper_title"] or "General"
        parts.append(f"## {header}\n_{n['created_at']}_\n\n{n['text']}\n")
    return "\n".join(parts)

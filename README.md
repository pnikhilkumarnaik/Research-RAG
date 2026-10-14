# PaperMind

Upload research papers (PDF or arXiv) and get cited answers, summaries, comparisons and saved notes.

```
Upload PDF/arXiv -> parse + chunk by section (PyMuPDF) -> embed -> Chroma
                                                                     |
Question -> retrieve top-k chunks -> Groq-hosted open model answers with [n] citations
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your GROQ_API_KEY (free key at console.groq.com)
streamlit run app.py        # UI at http://localhost:8501
```

Optional API backend (for a custom frontend): `uvicorn api:app --reload` (docs at `/docs`).

Run tests: `pip install pytest && pytest -q`

## Layout

| File | Role |
|---|---|
| `papermind/parser.py` | PDF text extraction, heading detection, section-aware chunking, arXiv download |
| `papermind/store.py` | Chroma vector store (local embeddings, no extra key needed) |
| `papermind/llm.py` | Groq prompts for Q&A with citations, summaries, comparisons (the only file that talks to the LLM) |
| `papermind/db.py` | SQLite for paper metadata and notes |
| `papermind/ingest.py` | Pipeline glue; re-uploading the same file is a no-op |
| `app.py` | Streamlit UI (Ask / Summarize / Compare / Notes) |
| `api.py` | FastAPI endpoints for a React/Next.js frontend |

## Weekend plan

- **Day 1 morning:** run it, upload 2-3 papers, ask questions, see where retrieval misses.
- **Day 1 afternoon:** improve parsing (two-column PDFs, tables), tune `CHUNK_SIZE` / `TOP_K`.
- **Day 2 morning:** build a Next.js frontend against `api.py`.
- **Day 2 afternoon:** deploy (see below), add one bonus feature.

## Swapping pieces from your stack diagram

- **Pinecone instead of Chroma:** reimplement `store.py` (`add_chunks`, `query`, `all_chunks`, `delete_paper`). Pinecone needs your own embeddings (e.g. Voyage or OpenAI) since it doesn't embed locally.
- **PostgreSQL instead of SQLite:** port `db.py` to `psycopg`; or use `pgvector` and drop Chroma entirely.
- **LangChain:** optional; this project calls the Groq SDK directly to keep the flow easy to debug.
- **Different model:** the default is `openai/gpt-oss-120b`; change it with `LLM_MODEL` in `.env`. Groq retires models regularly, so if a model returns 404 the app automatically falls back to another one your key can use (see `FALLBACK_MODELS` in `llm.py`); list yours with `curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"`. Groq's free tier has per-minute token limits, so `MAX_SUMMARY_CHARS` defaults to 40,000; long papers are summarized from their first part only.
- **Unstructured instead of PyMuPDF:** replace `parse_pdf` and keep the `ParsedPaper` shape.

## Deployment

- Streamlit: Streamlit Community Cloud or any container host.
- FastAPI backend: Render, Railway, Fly.io or AWS. Vercel is a good fit for a Next.js frontend, but not for this Python backend with a persistent vector DB.
- Persist the `data/` folder (or move to managed Pinecone/Postgres) so indexes survive restarts.

## Bonus roadmap

1. **Evaluation:** write 20 question/answer pairs per paper and measure retrieval hit-rate and answer faithfulness.
2. **Caching:** cache answers by (question, paper_ids) and summaries by paper id.
3. **Auth:** per-user libraries (add `user_id` to papers, notes and Chroma metadata).
4. **Better retrieval:** hybrid BM25 + vectors, reranking, query rewriting for follow-up questions.
5. **Highlights:** store the cited passages with notes and show them in a PDF viewer.

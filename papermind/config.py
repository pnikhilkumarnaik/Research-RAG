import os
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH, override=True)  # the project's .env wins over stale shell variables

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

CHROMA_DIR = DATA_DIR / "chroma"
SQLITE_PATH = DATA_DIR / "papermind.db"

# Open-weight model on Groq. Groq retires models often (llama-3.3-70b-versatile was shut
# down Aug 2026), so check https://console.groq.com/docs/deprecations if you get a 404.
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))      # characters
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))  # characters
TOP_K = int(os.getenv("TOP_K", "6"))
# Groq's free tier has per-minute token limits, so keep the summary input modest.
MAX_SUMMARY_CHARS = int(os.getenv("MAX_SUMMARY_CHARS", "40000"))

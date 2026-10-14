import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

CHROMA_PATH = Path(os.getenv("CHROMA_PATH", ROOT / "chroma_db"))
if not CHROMA_PATH.is_absolute():
    CHROMA_PATH = (ROOT / CHROMA_PATH).resolve()

UPLOAD_DIR = ROOT / "data" / "uploads"
SAMPLE_DIR = ROOT / "data" / "samples"
PROMPT_DIR = ROOT / "prompts"
CSV_PATH = ROOT / "AI_Resume_Screening.csv"

COLLECTION_NAME = "resumes"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 5

EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "minilm").strip().lower()
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()


def llm_enabled() -> bool:
    return bool(GOOGLE_API_KEY)

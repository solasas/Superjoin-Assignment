"""Central configuration, loaded from environment variables (and a .env file
if present). Nothing here is document-specific -- every knob is generic
pipeline behavior so the system works on PDFs it has never seen.
"""
import os
from pathlib import Path

# Load a .env file if present (tiny hand-rolled loader so we don't need an
# extra dependency just for this).
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if _ENV_PATH.exists():
    for _line in _ENV_PATH.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        k, v = _line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

ROOT_DIR = Path(__file__).resolve().parents[2]

LLM_BACKEND = os.environ.get("LLM_BACKEND", "claude_cli")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
EXTRACTION_MODEL = os.environ.get("EXTRACTION_MODEL", "claude-haiku-4-5")
RELATION_MODEL = os.environ.get("RELATION_MODEL", "claude-sonnet-4-5")
LLM_TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "150"))
LLM_CONCURRENCY = int(os.environ.get("LLM_CONCURRENCY", "4"))

DB_PATH = ROOT_DIR / os.environ.get("DB_PATH", "data/knowledge.db")
UPLOAD_DIR = ROOT_DIR / os.environ.get("UPLOAD_DIR", "data/uploads")

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- Chunking / relevance-filtering knobs (used to keep large PDFs cheap) ---

# How many source pages to merge into one LLM extraction call.
PAGES_PER_CHUNK = int(os.environ.get("PAGES_PER_CHUNK", "2"))

# Hard cap on characters sent to the LLM in one extraction call.
MAX_CHUNK_CHARS = int(os.environ.get("MAX_CHUNK_CHARS", "6000"))

# Fraction of chunks (ranked by fact-density heuristic) to actually send to
# the LLM. 1.0 disables the filter and processes every chunk. Lowering this
# is how we keep large PDFs affordable -- see relevance.py.
RELEVANCE_KEEP_FRACTION = float(os.environ.get("RELEVANCE_KEEP_FRACTION", "1.0"))

# Always process at least this many chunks regardless of the fraction above,
# so short documents are never starved.
RELEVANCE_MIN_CHUNKS = int(os.environ.get("RELEVANCE_MIN_CHUNKS", "6"))

# How many candidate fact-pairs to batch into a single relation-classification
# LLM call.
RELATION_BATCH_SIZE = int(os.environ.get("RELATION_BATCH_SIZE", "8"))

# Fuzzy-match threshold (0-1) for merging entity/attribute canonical slugs
# that the LLM phrased slightly differently across separate extraction calls.
CANONICAL_MATCH_THRESHOLD = float(os.environ.get("CANONICAL_MATCH_THRESHOLD", "0.72"))

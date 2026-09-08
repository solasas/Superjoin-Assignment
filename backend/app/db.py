"""SQLite storage layer.

Design notes:
- One flat `facts` table with a fixed set of "core" columns that almost every
  fact has (entity, attribute, value, evidence...) plus a single JSON
  `attributes` column that absorbs whatever *extra*, document-specific
  fields the extractor decided were worth keeping (e.g. "currency",
  "consolidation_scope", "restated"). This is what lets the schema evolve
  as new kinds of documents/facts show up without a migration.
- `schema_registry` tracks which attribute keys have been observed (in the
  core columns AND inside the JSON bag) purely so the UI/API can show how
  the schema has grown -- it's descriptive, not enforced.
- Processing is incremental: ingesting a new document only ever compares its
  *new* facts against facts already in the table; nothing is recomputed.
"""
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

_local = threading.local()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        conn = sqlite3.connect(str(config.DB_PATH), check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


@contextmanager
def tx():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'pending', -- pending|processing|done|error
    page_count INTEGER,
    chunk_count INTEGER DEFAULT 0,
    chunks_processed INTEGER DEFAULT 0,
    fact_count INTEGER DEFAULT 0,
    error TEXT,
    uploaded_at TEXT NOT NULL,
    processed_at TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    text TEXT NOT NULL,
    relevance_score REAL,
    kept INTEGER DEFAULT 1,
    processed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    page_start INTEGER,
    page_end INTEGER,
    statement TEXT NOT NULL,
    fact_type TEXT,
    entity_raw TEXT,
    entity_canonical TEXT,
    attribute_raw TEXT,
    attribute_canonical TEXT,
    value TEXT,
    value_numeric REAL,
    unit TEXT,
    temporal_scope TEXT,
    quote TEXT,
    grounded INTEGER DEFAULT 0,
    confidence REAL,
    attributes TEXT,          -- JSON bag of extra dynamic fields
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_facts_entity ON facts(entity_canonical);
CREATE INDEX IF NOT EXISTS idx_facts_attribute ON facts(attribute_canonical);
CREATE INDEX IF NOT EXISTS idx_facts_document ON facts(document_id);

CREATE TABLE IF NOT EXISTS fact_relations (
    id TEXT PRIMARY KEY,
    fact_id_a TEXT NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
    fact_id_b TEXT NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL, -- CORROBORATES|CONTRADICTS|RECONCILABLE_CONTEXT|UNRELATED
    explanation TEXT,
    confidence REAL,
    created_at TEXT NOT NULL,
    UNIQUE(fact_id_a, fact_id_b)
);
CREATE INDEX IF NOT EXISTS idx_relations_type ON fact_relations(relation_type);

CREATE TABLE IF NOT EXISTS schema_registry (
    attribute_key TEXT PRIMARY KEY,
    kind TEXT NOT NULL,           -- 'core' | 'dynamic'
    first_seen_document_id TEXT,
    first_seen_at TEXT,
    observed_count INTEGER DEFAULT 0,
    example_value TEXT
);

CREATE TABLE IF NOT EXISTS extraction_issues (
    id TEXT PRIMARY KEY,
    document_id TEXT,
    chunk_id TEXT,
    issue_type TEXT,        -- e.g. 'ungrounded_quote', 'parse_error', 'llm_error'
    detail TEXT,
    raw TEXT,
    created_at TEXT NOT NULL
);
"""


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def loads(s):
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    if "attributes" in d:
        d["attributes"] = loads(d["attributes"]) or {}
    return d


def touch_schema_registry(document_id: str, key: str, kind: str, example_value):
    with tx() as conn:
        row = conn.execute(
            "SELECT observed_count FROM schema_registry WHERE attribute_key=?", (key,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO schema_registry (attribute_key, kind, first_seen_document_id, "
                "first_seen_at, observed_count, example_value) VALUES (?,?,?,?,1,?)",
                (key, kind, document_id, _now(), str(example_value)[:200]),
            )
        else:
            conn.execute(
                "UPDATE schema_registry SET observed_count = observed_count + 1 WHERE attribute_key=?",
                (key,),
            )

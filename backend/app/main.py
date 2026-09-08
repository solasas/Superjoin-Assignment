from __future__ import annotations

import asyncio
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Fact Knowledge Layer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep a strong reference to in-flight ingest tasks so the event loop does not
# garbage-collect them mid-run (see the asyncio.create_task docs).
_background_tasks: set[asyncio.Task] = set()


# ---------------------------------------------------------------- documents

@app.post("/api/documents")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    dest = config.UPLOAD_DIR / f"{uuid.uuid4()}_{Path(file.filename).name}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    doc_id = pipeline.create_document_row(filename=file.filename)
    with db.tx() as conn:
        conn.execute("UPDATE documents SET title=? WHERE id=?", (file.filename, doc_id))

    task = asyncio.create_task(_run_ingest(doc_id, str(dest), file.filename))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"id": doc_id, "status": "pending"}


async def _run_ingest(doc_id: str, path: str, title: str):
    try:
        await pipeline.ingest_document(doc_id, path, title)
    except Exception:
        pass  # error state is already recorded on the document row


@app.get("/api/documents")
def list_documents():
    conn = db.get_conn()
    rows = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str):
    conn = db.get_conn()
    row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "document not found")
    chunks = conn.execute(
        "SELECT id, chunk_index, page_start, page_end, relevance_score, kept, processed, length(text) as chars "
        "FROM chunks WHERE document_id=? ORDER BY chunk_index", (doc_id,)
    ).fetchall()
    issues = conn.execute(
        "SELECT * FROM extraction_issues WHERE document_id=? ORDER BY created_at DESC LIMIT 200", (doc_id,)
    ).fetchall()
    return {
        "document": dict(row),
        "chunks": [dict(c) for c in chunks],
        "issues": [dict(i) for i in issues],
    }


@app.get("/api/documents/{doc_id}/file")
def get_document_file(doc_id: str):
    conn = db.get_conn()
    row = conn.execute("SELECT title FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "document not found")
    matches = list(config.UPLOAD_DIR.glob(f"*{Path(row['title']).name}"))
    if not matches:
        raise HTTPException(404, "file not found on disk")
    return FileResponse(matches[0], media_type="application/pdf")


# --------------------------------------------------------------------- facts

@app.get("/api/facts")
def list_facts(
    document_id: str | None = None,
    entity: str | None = None,
    attribute: str | None = None,
    fact_type: str | None = None,
    q: str | None = None,
    grounded_only: bool = False,
    limit: int = Query(500, le=5000),
):
    conn = db.get_conn()
    clauses, params = [], []
    if document_id:
        clauses.append("document_id=?"); params.append(document_id)
    if entity:
        clauses.append("entity_canonical LIKE ?"); params.append(f"%{entity.lower()}%")
    if attribute:
        clauses.append("attribute_canonical LIKE ?"); params.append(f"%{attribute.lower()}%")
    if fact_type:
        clauses.append("fact_type=?"); params.append(fact_type)
    if grounded_only:
        clauses.append("grounded=1")
    if q:
        clauses.append("(statement LIKE ? OR quote LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM facts {where} ORDER BY created_at DESC LIMIT ?", (*params, limit)
    ).fetchall()
    return [db.row_to_dict(r) for r in rows]


@app.get("/api/facts/{fact_id}")
def get_fact(fact_id: str):
    conn = db.get_conn()
    row = conn.execute("SELECT * FROM facts WHERE id=?", (fact_id,)).fetchone()
    if not row:
        raise HTTPException(404, "fact not found")
    fact = db.row_to_dict(row)
    doc = conn.execute("SELECT id, filename, title FROM documents WHERE id=?", (fact["document_id"],)).fetchone()
    fact["document"] = dict(doc) if doc else None
    rel_rows = conn.execute(
        "SELECT * FROM fact_relations WHERE fact_id_a=? OR fact_id_b=?", (fact_id, fact_id)
    ).fetchall()
    fact["relations"] = [dict(r) for r in rel_rows]
    return fact


# ----------------------------------------------------------------- relations

def _hydrate_relation(conn, r: dict) -> dict:
    fa = conn.execute("SELECT * FROM facts WHERE id=?", (r["fact_id_a"],)).fetchone()
    fb = conn.execute("SELECT * FROM facts WHERE id=?", (r["fact_id_b"],)).fetchone()
    out = dict(r)
    out["fact_a"] = db.row_to_dict(fa) if fa else None
    out["fact_b"] = db.row_to_dict(fb) if fb else None
    if fa:
        doc_a = conn.execute("SELECT id, filename, title FROM documents WHERE id=?", (fa["document_id"],)).fetchone()
        out["fact_a"]["document"] = dict(doc_a) if doc_a else None
    if fb:
        doc_b = conn.execute("SELECT id, filename, title FROM documents WHERE id=?", (fb["document_id"],)).fetchone()
        out["fact_b"]["document"] = dict(doc_b) if doc_b else None
    return out


@app.get("/api/relations")
def list_relations(
    relation_type: str | None = None,
    document_id: str | None = None,
    entity: str | None = None,
    limit: int = Query(300, le=2000),
):
    conn = db.get_conn()
    clauses, params = [], []
    if relation_type:
        clauses.append("relation_type=?"); params.append(relation_type.upper())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM fact_relations {where} ORDER BY created_at DESC LIMIT ?", (*params, limit)
    ).fetchall()
    hydrated = [_hydrate_relation(conn, dict(r)) for r in rows]

    if document_id:
        hydrated = [
            h for h in hydrated
            if (h["fact_a"] and h["fact_a"]["document_id"] == document_id)
            or (h["fact_b"] and h["fact_b"]["document_id"] == document_id)
        ]
    if entity:
        e = entity.lower()
        hydrated = [
            h for h in hydrated
            if (h["fact_a"] and e in (h["fact_a"]["entity_canonical"] or ""))
            or (h["fact_b"] and e in (h["fact_b"]["entity_canonical"] or ""))
        ]
    return hydrated


@app.get("/api/relations/{relation_id}")
def get_relation(relation_id: str):
    conn = db.get_conn()
    row = conn.execute("SELECT * FROM fact_relations WHERE id=?", (relation_id,)).fetchone()
    if not row:
        raise HTTPException(404, "relation not found")
    return _hydrate_relation(conn, dict(row))


# --------------------------------------------------------------------- misc

@app.get("/api/schema")
def get_schema():
    conn = db.get_conn()
    rows = conn.execute(
        "SELECT * FROM schema_registry ORDER BY kind, observed_count DESC"
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/stats")
def get_stats():
    conn = db.get_conn()
    docs = conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]
    facts = conn.execute("SELECT COUNT(*) c FROM facts").fetchone()["c"]
    grounded = conn.execute("SELECT COUNT(*) c FROM facts WHERE grounded=1").fetchone()["c"]
    rel_counts = conn.execute(
        "SELECT relation_type, COUNT(*) c FROM fact_relations GROUP BY relation_type"
    ).fetchall()
    issues = conn.execute("SELECT COUNT(*) c FROM extraction_issues").fetchone()["c"]
    return {
        "documents": docs,
        "facts": facts,
        "facts_grounded": grounded,
        "relations_by_type": {r["relation_type"]: r["c"] for r in rel_counts},
        "extraction_issues": issues,
    }


# --------------------------------------------------------------- static UI

_FRONTEND_DIR = config.ROOT_DIR / "frontend"
if _FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (_FRONTEND_DIR / "index.html").read_text()

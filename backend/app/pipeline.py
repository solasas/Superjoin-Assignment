"""Orchestrates one document's journey from raw PDF to facts + relations.

ingest_document() is the single entry point used by both the API
(background task on upload) and the CLI batch-ingest script, so there's
exactly one code path for "what happens when a PDF comes in" regardless of
whether it arrived through the UI or a script.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from . import config, db, relations
from .extraction import extract_facts_from_chunk, persist_facts
from .ingest import extract_pages, group_pages_into_chunks
from .llm_client import get_llm_client
from .relevance import select_relevant


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_document_row(filename: str, title: str | None = None) -> str:
    doc_id = str(uuid.uuid4())
    with db.tx() as conn:
        conn.execute(
            "INSERT INTO documents (id, filename, title, status, uploaded_at) VALUES (?,?,?,?,?)",
            (doc_id, filename, title or filename, "pending", _now()),
        )
    return doc_id


def _set_status(doc_id: str, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    with db.tx() as conn:
        conn.execute(f"UPDATE documents SET {cols} WHERE id=?", (*fields.values(), doc_id))


async def ingest_document(doc_id: str, pdf_path: str, doc_title: str, only_pages: set[int] | None = None):
    llm = get_llm_client()
    try:
        _set_status(doc_id, status="processing")

        pages = extract_pages(pdf_path, only_pages=only_pages)
        chunks = group_pages_into_chunks(pages)
        kept_chunks, all_chunks = select_relevant(
            chunks, config.RELEVANCE_KEEP_FRACTION, config.RELEVANCE_MIN_CHUNKS
        )

        with db.tx() as conn:
            for c in all_chunks:
                chunk_id = f"{doc_id}:{c.index}"
                conn.execute(
                    "INSERT INTO chunks (id, document_id, chunk_index, page_start, page_end, text, "
                    "relevance_score, kept) VALUES (?,?,?,?,?,?,?,?)",
                    (chunk_id, doc_id, c.index, c.page_start, c.page_end, c.text, c.relevance_score, int(c.kept)),
                )

        _set_status(
            doc_id,
            page_count=len(pages),
            chunk_count=len(all_chunks),
        )

        semaphore = asyncio.Semaphore(config.LLM_CONCURRENCY)
        new_fact_ids: list[str] = []
        processed = 0
        lock = asyncio.Lock()

        async def process_chunk(c):
            nonlocal processed
            chunk_id = f"{doc_id}:{c.index}"
            async with semaphore:
                facts = await extract_facts_from_chunk(llm, c, doc_id, chunk_id, doc_title)
            if facts:
                persist_facts(facts)
                async with lock:
                    new_fact_ids.extend(f["id"] for f in facts)
            with db.tx() as conn:
                conn.execute("UPDATE chunks SET processed=1 WHERE id=?", (chunk_id,))
            async with lock:
                processed += 1
                _set_status(doc_id, chunks_processed=processed, fact_count=len(new_fact_ids))

        await asyncio.gather(*(process_chunk(c) for c in kept_chunks))

        # Cross-document relation matching -- only new facts vs existing ones.
        pairs = relations.generate_candidate_pairs(new_fact_ids)
        classified = await relations.classify_pairs(llm, pairs)
        relations.persist_relations(classified)

        _set_status(
            doc_id,
            status="done",
            fact_count=len(new_fact_ids),
            processed_at=_now(),
        )
    except Exception as e:  # keep the document row informative instead of stuck "processing"
        _set_status(doc_id, status="error", error=str(e)[:2000], processed_at=_now())
        raise

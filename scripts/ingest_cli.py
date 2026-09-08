#!/usr/bin/env python3
"""Batch-ingest one or more PDFs straight into the knowledge layer without
going through the HTTP API -- handy for seeding a demo, for scripted /
CI-style testing, or for bulk-loading "many PDFs" (one of the brownie-point
extensions). Uses the exact same pipeline.ingest_document() the API calls,
so behavior is identical either way.

Usage:
    python scripts/ingest_cli.py path/to/one.pdf path/to/two.pdf ...
    python scripts/ingest_cli.py --glob "starter_dataset/**/*.pdf"

    # Scope a large PDF to specific pages (e.g. you already know the board
    # report and financial statements are on pages 22, 24 and 51):
    python scripts/ingest_cli.py "path/to/big.pdf:22,24,51"
"""
import argparse
import asyncio
import glob
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import db, pipeline  # noqa: E402


def _parse_pages_spec(spec: str) -> set[int]:
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            pages.update(range(int(lo), int(hi) + 1))
        else:
            pages.add(int(part))
    return pages


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="*", help="PDF file paths, optionally 'path.pdf:pages' e.g. 'report.pdf:1,5,10-12'")
    ap.add_argument("--glob", help="glob pattern for PDFs, e.g. 'starter_dataset/**/*.pdf'")
    args = ap.parse_args()

    specs = list(args.pdfs)
    if args.glob:
        specs += sorted(glob.glob(args.glob, recursive=True))
    if not specs:
        ap.error("no PDFs given (pass paths or --glob)")

    db.init_db()

    for spec in specs:
        only_pages = None
        if ":" in spec and not Path(spec).exists():
            path_part, pages_part = spec.rsplit(":", 1)
            spec, only_pages = path_part, _parse_pages_spec(pages_part)
        p = Path(spec)
        if not p.exists():
            print(f"[skip] {p} does not exist")
            continue
        title = p.name
        doc_id = pipeline.create_document_row(filename=title)
        page_note = f" (pages {sorted(only_pages)})" if only_pages else ""
        print(f"[{doc_id}] ingesting {p}{page_note} ...")
        t0 = time.time()
        try:
            await pipeline.ingest_document(doc_id, str(p), title, only_pages=only_pages)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        conn = db.get_conn()
        row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        print(
            f"  done in {time.time()-t0:.1f}s | pages={row['page_count']} "
            f"chunks={row['chunk_count']} facts={row['fact_count']} status={row['status']}"
        )


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Dump the current knowledge layer to plain JSON + a short Markdown digest.

This is what lets a reviewer inspect real output (facts, evidence, and
cross-document relations) without running the pipeline or holding an API
key. It reads whatever is in the DB -- nothing here is specific to the
starter documents.

    python scripts/export_sample.py                 # -> sample_output/
    python scripts/export_sample.py --out some_dir
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import config  # noqa: E402


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(config.DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def _rows(c, sql, params=()):
    return [dict(r) for r in c.execute(sql, params).fetchall()]


def _load_attrs(rows):
    for r in rows:
        if "attributes" in r:
            try:
                r["attributes"] = json.loads(r["attributes"]) if r["attributes"] else {}
            except (TypeError, ValueError):
                r["attributes"] = {}
    return rows


def build_export(c) -> dict:
    docs = _rows(c, "SELECT id, filename, title, status, page_count, chunk_count, "
                   "fact_count, uploaded_at, processed_at FROM documents ORDER BY uploaded_at")
    facts = _load_attrs(_rows(c, "SELECT * FROM facts ORDER BY document_id, page_start"))
    relations = _rows(c, "SELECT * FROM fact_relations ORDER BY relation_type, created_at")
    issues = _rows(c, "SELECT * FROM extraction_issues ORDER BY created_at")
    schema = _rows(c, "SELECT * FROM schema_registry ORDER BY kind, observed_count DESC")

    facts_by_id = {f["id"]: f for f in facts}
    doc_name = {d["id"]: d["filename"] for d in docs}

    # Inline both facts (with their evidence) into every relation so a
    # relation is readable on its own.
    rel_out = []
    for r in relations:
        fa, fb = facts_by_id.get(r["fact_id_a"]), facts_by_id.get(r["fact_id_b"])
        rel_out.append({
            **r,
            "fact_a": _brief(fa, doc_name) if fa else None,
            "fact_b": _brief(fb, doc_name) if fb else None,
        })

    rel_counts: dict[str, int] = {}
    for r in relations:
        rel_counts[r["relation_type"]] = rel_counts.get(r["relation_type"], 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "documents": len(docs),
            "facts": len(facts),
            "facts_grounded": sum(1 for f in facts if f["grounded"]),
            "relations_by_type": rel_counts,
            "extraction_issues": len(issues),
        },
        "documents": docs,
        "facts": facts,
        "relations": rel_out,
        "extraction_issues": issues,
        "schema_registry": schema,
    }


def _brief(f: dict, doc_name: dict) -> dict:
    return {
        "id": f["id"],
        "document": doc_name.get(f["document_id"], f["document_id"]),
        "page": f["page_start"],
        "statement": f["statement"],
        "entity": f["entity_raw"],
        "attribute": f["attribute_raw"],
        "value": f["value"],
        "unit": f["unit"],
        "temporal_scope": f["temporal_scope"],
        "quote": f["quote"],
        "grounded": bool(f["grounded"]),
    }


def write_markdown(export: dict, path: Path):
    s = export["summary"]
    lines = [
        "# Sample output",
        "",
        f"Generated {export['generated_at']} from `{config.DB_PATH.name}`.",
        "Regenerate with `python scripts/export_sample.py`.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Documents | {s['documents']} |",
        f"| Facts | {s['facts']} ({s['facts_grounded']} grounded) |",
    ]
    for k, v in sorted(s["relations_by_type"].items()):
        lines.append(f"| Relations: {k} | {v} |")
    lines.append(f"| Extraction issues | {s['extraction_issues']} |")
    lines += ["", "## Relations by type", ""]

    for rtype in ("CORROBORATES", "CONTRADICTS", "RECONCILABLE_CONTEXT"):
        rels = [r for r in export["relations"] if r["relation_type"] == rtype]
        lines.append(f"### {rtype} ({len(rels)})")
        lines.append("")
        for r in rels[:12]:
            a, b = r["fact_a"], r["fact_b"]
            if not a or not b:
                continue
            lines += [
                f"- **A** ({a['document']} p.{a['page']}): {a['statement']}",
                f"  - evidence: \"{a['quote']}\"",
                f"- **B** ({b['document']} p.{b['page']}): {b['statement']}",
                f"  - evidence: \"{b['quote']}\"",
                f"  - **{rtype}** (confidence {r['confidence']}): {r['explanation']}",
                "",
            ]
        if len(rels) > 12:
            lines.append(f"_({len(rels) - 12} more in `relations.json`)_")
            lines.append("")

    path.write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "sample_output"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if not config.DB_PATH.exists():
        ap.error(f"no database at {config.DB_PATH} -- ingest something first")

    c = _conn()
    export = build_export(c)

    (out / "facts.json").write_text(json.dumps(export["facts"], indent=2, ensure_ascii=False))
    (out / "relations.json").write_text(json.dumps(export["relations"], indent=2, ensure_ascii=False))
    (out / "documents.json").write_text(json.dumps(export["documents"], indent=2, ensure_ascii=False))
    (out / "extraction_issues.json").write_text(json.dumps(export["extraction_issues"], indent=2, ensure_ascii=False))
    (out / "schema_registry.json").write_text(json.dumps(export["schema_registry"], indent=2, ensure_ascii=False))
    (out / "summary.json").write_text(json.dumps(
        {"generated_at": export["generated_at"], **export["summary"]}, indent=2))
    write_markdown(export, out / "README.md")

    s = export["summary"]
    print(f"wrote {out}/ : {s['facts']} facts, "
          f"{sum(s['relations_by_type'].values())} relations, "
          f"{s['extraction_issues']} issues")


if __name__ == "__main__":
    main()

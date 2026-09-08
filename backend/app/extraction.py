"""Turn one chunk of source text into zero or more grounded Fact records.

The extraction prompt is deliberately schema-light: it asks for a fixed set
of "core" fields that make cross-document comparison possible (entity,
attribute, value, evidence quote, ...) plus an open `extra` object for
whatever document-specific detail the model thinks is worth keeping. That
`extra` bag is what lets the effective schema grow as new kinds of
documents are ingested, without any code change or migration.

Every extracted fact is grounded before being trusted: the `quote` field
must actually appear (allowing for minor whitespace/OCR noise) in the
source chunk. Facts that don't ground are still stored, but flagged
`grounded=0` and demoted in confidence, and logged as an extraction issue --
see PIPELINE_NOTES / the "extraction failures" story in the README.
"""
from __future__ import annotations

import difflib
import re
import uuid
from datetime import datetime, timezone

from . import config, db
from .ingest import Chunk
from .llm_client import LLMClient, LLMError, parse_json_loose

EXTRACTION_SYSTEM_PROMPT = (
    "You are a meticulous fact-extraction engine used inside a document "
    "analysis pipeline. You only ever output the JSON asked for -- no "
    "prose, no markdown code fences, no commentary before or after."
)

EXTRACTION_PROMPT_TEMPLATE = """You are given one excerpt of text from a source document. The excerpt may span multiple pages; each page's text is preceded by a "[page N]" marker.

Extract every discrete, checkable factual claim in the excerpt: numeric facts (financial figures, growth rates, counts, dates, percentages, ratios) as well as semantic/status facts (roles, relationships, locations, classifications, qualitative statements). Do NOT invent facts that are not stated in the text, and do not extract vague marketing language with no checkable content.

For each fact, output an object with exactly these fields:
- "statement": a short, self-contained natural-language sentence stating the fact (resolve pronouns/abbreviations using nearby context if you can)
- "entity_raw": the primary subject of the fact, exactly as named in the text (a company, person, place, product, or other named thing)
- "entity_canonical": your best normalized snake_case slug for that real-world entity, so the same entity gets the same slug even if it is worded differently elsewhere (e.g. "Delhivery Limited" and "the Company" in a Delhivery filing should both be "delhivery")
- "attribute_raw": what aspect/metric of the entity this fact describes, in natural words (e.g. "revenue from services", "EBITDA margin", "board status", "registered office address")
- "attribute_canonical": normalized snake_case slug for that attribute
- "value": the stated value, as text, close to how it appears (e.g. "8,142", "1.6%", "resigned", "Gurugram, Haryana")
- "value_numeric": the value as a plain JSON number if it is fundamentally numeric (strip currency symbols/commas/units, keep sign), else null
- "unit": unit or currency if applicable (e.g. "INR Cr", "%", "Mn tons", "USD bn"), else null
- "temporal_scope": the time period or as-of date this fact applies to, if stated or clearly implied (e.g. "FY24", "as of March 31, 2024", "Q4 FY24", "CY2024"), else null
- "fact_type": your best short category label, e.g. "numeric", "categorical", "textual" -- introduce a new short lowercase_snake label if none of those fit, this is allowed to evolve per document
- "quote": the exact verbatim substring copied character-for-character from the excerpt that is the direct evidence for this fact (not paraphrased -- must be found in the excerpt text)
- "page": the integer page number (from the nearest preceding "[page N]" marker) that the quote came from
- "confidence": your confidence 0-1 that this is a correctly extracted, unambiguous fact
- "extra": a JSON object for any additional structured detail worth keeping that doesn't fit the fields above (e.g. {{"scope": "consolidated"}}, {{"currency": "INR"}}, {{"restated": true}}, {{"role": "Independent Director"}}). Use an empty object {{}} if there is nothing to add. Keys should be short lowercase_snake_case.

Respond with ONLY a JSON array of these objects, nothing else. If there are no clear facts in the excerpt, respond with [].

DOCUMENT: "{doc_title}"
EXCERPT (pages {page_start}-{page_end}):
---
{chunk_text}
---
"""


def build_extraction_prompt(chunk: Chunk, doc_title: str) -> str:
    return EXTRACTION_PROMPT_TEMPLATE.format(
        doc_title=doc_title,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        chunk_text=chunk.text[: config.MAX_CHUNK_CHARS + 500],
    )


_WS_RE = re.compile(r"\s+")


def _normalize_for_match(s: str) -> str:
    return _WS_RE.sub(" ", s or "").strip().lower()


def is_grounded(quote: str, source_text: str) -> bool:
    """A quote is grounded if it (or something very close to it, allowing
    for whitespace/hyphenation noise from PDF text extraction) actually
    appears in the chunk it was supposedly pulled from.
    """
    if not quote or not quote.strip():
        return False
    q = _normalize_for_match(quote)
    t = _normalize_for_match(source_text)
    if not q:
        return False
    if q in t:
        return True
    # Fuzzy fallback: slide a window and check similarity, catches cases
    # where the model normalized a hyphen/space or copied one word wrong.
    if len(q) > 200:
        q = q[:200]
    best = 0.0
    window = len(q)
    step = max(window // 4, 1)  # finer stride so we don't miss a good alignment
    for i in range(0, max(len(t) - window, 0) + 1, step):
        seg = t[i : i + window]
        ratio = difflib.SequenceMatcher(None, q, seg).ratio()
        best = max(best, ratio)
        if best > 0.78:
            return True
    return best > 0.78


REQUIRED_FIELDS = [
    "statement", "entity_raw", "entity_canonical", "attribute_raw",
    "attribute_canonical", "value", "fact_type", "quote",
]


async def extract_facts_from_chunk(
    llm: LLMClient, chunk: Chunk, doc_id: str, chunk_id: str, doc_title: str
) -> list[dict]:
    prompt = build_extraction_prompt(chunk, doc_title)
    try:
        raw = await llm.complete(prompt, model=config.EXTRACTION_MODEL, system=EXTRACTION_SYSTEM_PROMPT)
        items = parse_json_loose(raw)
    except (LLMError, ValueError) as e:
        with db.tx() as conn:
            conn.execute(
                "INSERT INTO extraction_issues (id, document_id, chunk_id, issue_type, detail, raw, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), doc_id, chunk_id, "llm_error", str(e), "", _now()),
            )
        return []

    if not isinstance(items, list):
        with db.tx() as conn:
            conn.execute(
                "INSERT INTO extraction_issues (id, document_id, chunk_id, issue_type, detail, raw, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), doc_id, chunk_id, "parse_error", "expected a JSON array", str(items)[:2000], _now()),
            )
        return []

    facts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        missing = [f for f in REQUIRED_FIELDS if not item.get(f)]
        if missing:
            with db.tx() as conn:
                conn.execute(
                    "INSERT INTO extraction_issues (id, document_id, chunk_id, issue_type, detail, raw, created_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), doc_id, chunk_id, "missing_fields", ",".join(missing), db.dumps(item), _now()),
                )
            continue

        grounded = is_grounded(item.get("quote", ""), chunk.text)
        confidence = float(item.get("confidence") or 0.5)
        if not grounded:
            confidence = min(confidence, 0.35)
            with db.tx() as conn:
                conn.execute(
                    "INSERT INTO extraction_issues (id, document_id, chunk_id, issue_type, detail, raw, created_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), doc_id, chunk_id, "ungrounded_quote", item.get("quote", "")[:300], db.dumps(item), _now()),
                )

        page = item.get("page")
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = chunk.page_start
        page = max(chunk.page_start, min(page, chunk.page_end))

        value_numeric = item.get("value_numeric")
        try:
            value_numeric = float(value_numeric) if value_numeric is not None else None
        except (TypeError, ValueError):
            value_numeric = None

        fact_id = str(uuid.uuid4())
        fact = dict(
            id=fact_id,
            document_id=doc_id,
            chunk_id=chunk_id,
            page_start=page,
            page_end=page,
            statement=str(item.get("statement"))[:1000],
            fact_type=str(item.get("fact_type"))[:50],
            entity_raw=str(item.get("entity_raw"))[:300],
            entity_canonical=_slugify(item.get("entity_canonical") or item.get("entity_raw")),
            attribute_raw=str(item.get("attribute_raw"))[:300],
            attribute_canonical=_slugify(item.get("attribute_canonical") or item.get("attribute_raw")),
            value=str(item.get("value"))[:300],
            value_numeric=value_numeric,
            unit=(str(item.get("unit"))[:50] if item.get("unit") else None),
            temporal_scope=(str(item.get("temporal_scope"))[:100] if item.get("temporal_scope") else None),
            quote=str(item.get("quote"))[:1000],
            grounded=1 if grounded else 0,
            confidence=max(0.0, min(1.0, confidence)),
            attributes=db.dumps(item.get("extra") or {}),
            created_at=_now(),
        )
        facts.append(fact)

    return facts


def _slugify(s) -> str:
    s = str(s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:100] or "unknown"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def persist_facts(facts: list[dict]):
    if not facts:
        return
    with db.tx() as conn:
        for f in facts:
            conn.execute(
                """INSERT INTO facts (
                    id, document_id, chunk_id, page_start, page_end, statement, fact_type,
                    entity_raw, entity_canonical, attribute_raw, attribute_canonical,
                    value, value_numeric, unit, temporal_scope, quote, grounded, confidence,
                    attributes, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    f["id"], f["document_id"], f["chunk_id"], f["page_start"], f["page_end"],
                    f["statement"], f["fact_type"], f["entity_raw"], f["entity_canonical"],
                    f["attribute_raw"], f["attribute_canonical"], f["value"], f["value_numeric"],
                    f["unit"], f["temporal_scope"], f["quote"], f["grounded"], f["confidence"],
                    f["attributes"], f["created_at"],
                ),
            )
        for f in facts:
            for core in ("entity_canonical", "attribute_canonical", "fact_type", "unit", "temporal_scope"):
                if f.get(core):
                    db.touch_schema_registry(f["document_id"], f"core:{core}", "core", f[core])
            extra = db.loads(f["attributes"]) or {}
            for k, v in extra.items():
                db.touch_schema_registry(f["document_id"], f"extra:{k}", "dynamic", v)

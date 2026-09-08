"""Cross-document fact comparison.

Two-stage, recall-then-precision design:

1. Candidate generation (cheap, deterministic): group facts by fuzzy-matched
   canonical entity, then within an entity group, by fuzzy/overlapping
   attribute -- this is intentionally generous (it will over-generate) so we
   don't miss a match just because two extraction calls (run independently,
   possibly from different documents) phrased the same metric slightly
   differently ("revenue from services" vs "total revenue").

2. Adjudication (LLM, precise): every candidate pair is handed to the model
   with both facts' full context (value, unit, temporal scope, entity,
   attribute, and the verbatim evidence quote) and classified into one of
   CORROBORATES / CONTRADICTS / RECONCILABLE_CONTEXT / UNRELATED, with a
   short explanation. UNRELATED candidates (the false positives from stage
   1) are simply dropped rather than stored.

Only NEW facts (from the document just ingested) are ever compared against
the existing knowledge base -- old fact-pairs are never re-classified. That
is what makes ingesting document N+1 an incremental operation instead of a
full rebuild.
"""
from __future__ import annotations

import difflib
import itertools
import uuid
from datetime import datetime, timezone

from . import config, db
from .llm_client import LLMClient, LLMError, parse_json_loose

RELATION_SYSTEM_PROMPT = (
    "You are a careful analyst comparing factual claims extracted from different "
    "documents. You only ever output the JSON asked for -- no prose, no markdown "
    "fences, no commentary."
)

RELATION_PROMPT_TEMPLATE = """You will be shown a list of candidate fact pairs. Each pair contains two facts, possibly from different documents, that were flagged as *possibly* about the same underlying real-world thing. For each pair, decide the relationship between fact A and fact B.

Use exactly one of these relation_type values:
- "CORROBORATES": both facts assert essentially the same underlying truth (same entity, same metric/attribute, matching or consistent value once you account for rounding, and a comparable scope/time), even though the wording, units, or level of precision differ.
- "CONTRADICTS": same entity, same metric/attribute, the same (or clearly overlapping) scope and time period, but materially different / incompatible values or statuses, with no reasonable contextual explanation for the difference.
- "RECONCILABLE_CONTEXT": the values or statuses differ, but the difference is explainable by context stated or implied in the facts themselves -- e.g. different time periods, different scope (consolidated vs standalone, one segment vs whole company, one subsidiary vs group), different units/currency/basis, or a legitimate change over time (e.g. a person's role status changed between an earlier and a later document).
- "UNRELATED": on inspection the two facts are not actually comparable (different entities, or superficially similar but actually different metrics) -- this pairing was a false positive from candidate generation.

For each pair also give:
- "explanation": one or two sentences citing the concrete values/dates/scopes from BOTH facts that justify your classification. Be specific (quote numbers/periods), not generic.
- "confidence": 0-1

Respond with ONLY a JSON array, one object per input pair, in the same order, each shaped as:
{{"pair_index": <int>, "relation_type": "...", "explanation": "...", "confidence": <float>}}

CANDIDATE PAIRS:
{pairs_json}
"""


def _norm(s: str) -> str:
    return (s or "").strip().lower()


_LEGAL_SUFFIXES = (
    "_limited", "_ltd", "_llc", "_inc", "_incorporated", "_corp", "_corporation",
    "_plc", "_pvt", "_private", "_co", "_company", "_group", "_holdings",
)


def _strip_legal_suffix(s: str) -> str:
    for suf in _LEGAL_SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf) + 1:
            return s[: -len(suf)]
    return s


def _similarity(a: str, b: str) -> float:
    """Fuzzy similarity tuned for short canonical slugs: exact match after
    stripping common legal suffixes ("delhivery" vs "delhivery_limited")
    counts fully; substring containment gets a strong partial score
    (handles one call producing a more/less specific slug than another for
    the same real-world thing); everything else falls back to plain
    character-level similarity.
    """
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    sa, sb = _strip_legal_suffix(a), _strip_legal_suffix(b)
    if sa == sb:
        return 0.97
    if sa in sb or sb in sa:
        shorter, longer = (sa, sb) if len(sa) < len(sb) else (sb, sa)
        return 0.72 + 0.25 * (len(shorter) / max(len(longer), 1))
    return difflib.SequenceMatcher(None, sa, sb).ratio()


def _fuzzy_group_key(value: str, existing_keys: list[str], threshold: float) -> str:
    """Map `value` onto an existing canonical key if it's a close fuzzy
    match, otherwise return `value` itself as a new key. This absorbs
    minor slug differences the extractor produced across separate calls
    (e.g. "delhivery" vs "delhivery_limited").
    """
    v = _norm(value)
    if not v:
        return v
    best_key, best_score = None, 0.0
    for k in existing_keys:
        score = _similarity(v, k)
        if score > best_score:
            best_key, best_score = k, score
    if best_key is not None and best_score >= threshold:
        return best_key
    return v


def _fetch_fact_dicts(conn, fact_ids: list[str]) -> dict[str, dict]:
    if not fact_ids:
        return {}
    placeholders = ",".join("?" * len(fact_ids))
    rows = conn.execute(f"SELECT * FROM facts WHERE id IN ({placeholders})", fact_ids).fetchall()
    return {r["id"]: db.row_to_dict(r) for r in rows}


def generate_candidate_pairs(new_fact_ids: list[str]) -> list[tuple[str, str]]:
    """For each new fact, find existing facts (from OTHER documents) that
    plausibly refer to the same entity+attribute, using fuzzy matching over
    canonical slugs. Returns a de-duplicated list of (fact_id_a, fact_id_b)
    pairs, sorted so fact_id_a < fact_id_b (undirected).
    """
    conn = db.get_conn()
    new_facts = _fetch_fact_dicts(conn, new_fact_ids)
    if not new_facts:
        return []

    all_rows = conn.execute(
        "SELECT id, document_id, entity_canonical, attribute_canonical, fact_type FROM facts"
    ).fetchall()
    existing = [dict(r) for r in all_rows if r["id"] not in new_facts]

    existing_entity_keys = sorted({_norm(r["entity_canonical"]) for r in existing if r["entity_canonical"]})

    pairs: set[tuple[str, str]] = set()
    already_related = {
        (r["fact_id_a"], r["fact_id_b"])
        for r in conn.execute("SELECT fact_id_a, fact_id_b FROM fact_relations").fetchall()
    }

    for nf_id, nf in new_facts.items():
        entity_key = _fuzzy_group_key(nf["entity_canonical"], existing_entity_keys, config.CANONICAL_MATCH_THRESHOLD)

        same_entity = [
            r for r in existing
            if r["document_id"] != nf["document_id"]
            and _similarity(r["entity_canonical"], entity_key) >= config.CANONICAL_MATCH_THRESHOLD
        ]
        if not same_entity:
            continue

        nf_attr = _norm(nf["attribute_canonical"])
        for r in same_entity:
            attr_ratio = _similarity(r["attribute_canonical"], nf_attr)
            token_overlap = _token_overlap(r["attribute_canonical"], nf["attribute_canonical"])
            if attr_ratio >= 0.55 or token_overlap >= 0.35:
                a, b = sorted([nf_id, r["id"]])
                if (a, b) not in already_related:
                    pairs.add((a, b))

    return sorted(pairs)


def _token_overlap(a: str, b: str) -> float:
    ta, tb = set((a or "").split("_")), set((b or "").split("_"))
    ta.discard(""); tb.discard("")
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _fact_brief(f: dict, label: str) -> dict:
    return {
        "label": label,
        "document_id": f["document_id"],
        "entity": f["entity_raw"],
        "attribute": f["attribute_raw"],
        "value": f["value"],
        "value_numeric": f["value_numeric"],
        "unit": f["unit"],
        "temporal_scope": f["temporal_scope"],
        "statement": f["statement"],
        "quote": f["quote"],
    }


async def classify_pairs(llm: LLMClient, pairs: list[tuple[str, str]]) -> list[dict]:
    """Classify candidate pairs in batches, return relation dicts ready to
    persist (UNRELATED pairs are dropped).
    """
    if not pairs:
        return []
    conn = db.get_conn()
    all_ids = sorted({fid for pair in pairs for fid in pair})
    facts_by_id = _fetch_fact_dicts(conn, all_ids)

    results: list[dict] = []
    batch_size = config.RELATION_BATCH_SIZE
    for i in range(0, len(pairs), batch_size):
        batch = pairs[i : i + batch_size]
        payload = []
        for idx, (a_id, b_id) in enumerate(batch):
            fa, fb = facts_by_id.get(a_id), facts_by_id.get(b_id)
            if not fa or not fb:
                continue
            payload.append({
                "pair_index": idx,
                "fact_a": _fact_brief(fa, "A"),
                "fact_b": _fact_brief(fb, "B"),
            })
        if not payload:
            continue

        prompt = RELATION_PROMPT_TEMPLATE.format(pairs_json=db.dumps(payload))
        try:
            raw = await llm.complete(prompt, model=config.RELATION_MODEL, system=RELATION_SYSTEM_PROMPT)
            classifications = parse_json_loose(raw)
        except (LLMError, ValueError) as e:
            with db.tx() as conn2:
                conn2.execute(
                    "INSERT INTO extraction_issues (id, document_id, chunk_id, issue_type, detail, raw, created_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), None, None, "relation_llm_error", str(e), "", _now()),
                )
            continue

        if not isinstance(classifications, list):
            continue

        for c in classifications:
            if not isinstance(c, dict):
                continue
            idx = c.get("pair_index")
            if not isinstance(idx, int) or idx < 0 or idx >= len(batch):
                continue
            relation_type = str(c.get("relation_type", "")).strip().upper()
            if relation_type not in ("CORROBORATES", "CONTRADICTS", "RECONCILABLE_CONTEXT", "UNRELATED"):
                continue
            if relation_type == "UNRELATED":
                continue
            a_id, b_id = batch[idx]
            results.append({
                "id": str(uuid.uuid4()),
                "fact_id_a": a_id,
                "fact_id_b": b_id,
                "relation_type": relation_type,
                "explanation": str(c.get("explanation", ""))[:1000],
                "confidence": max(0.0, min(1.0, float(c.get("confidence") or 0.5))),
                "created_at": _now(),
            })

    return results


def persist_relations(relations: list[dict]):
    if not relations:
        return
    with db.tx() as conn:
        for r in relations:
            conn.execute(
                "INSERT OR IGNORE INTO fact_relations "
                "(id, fact_id_a, fact_id_b, relation_type, explanation, confidence, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (r["id"], r["fact_id_a"], r["fact_id_b"], r["relation_type"], r["explanation"], r["confidence"], r["created_at"]),
            )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

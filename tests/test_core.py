"""Small, dependency-free sanity checks for the parts of the pipeline that
have no LLM in the loop (grounding, relevance scoring, JSON parsing,
canonical fuzzy-matching). Run with:  python3 tests/test_core.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.extraction import is_grounded, _slugify  # noqa: E402
from app.relevance import score_chunk  # noqa: E402
from app.llm_client import parse_json_loose, strip_json_fences  # noqa: E402
from app.relations import _fuzzy_group_key, _token_overlap  # noqa: E402

passed = failed = 0


def check(label, condition):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"FAIL: {label}")


# --- grounding ---
source = "FY24 revenue from services stood at ₹8,142 Cr, up 12.7% YoY."
check("exact quote grounds", is_grounded("₹8,142 Cr", source))
check("quote with extra whitespace still grounds", is_grounded("₹8,142  Cr", source))
check("quote not in source does not ground", not is_grounded("₹9,999 Cr", source))
check("empty quote never grounds", not is_grounded("", source))
check("near-identical quote (minor OCR noise) still grounds via fuzzy fallback",
      is_grounded("revenue from servces stood at Rs 8,142 Cr", source))

# --- slugify ---
check("slugify normalizes case/punctuation", _slugify("Delhivery Limited") == "delhivery_limited")
check("slugify handles empty", _slugify("") == "unknown")

# --- relevance scoring ---
dense = "Revenue from Operations 74,540.82 66,586.61 81,415.38 72,253.01 as of March 31, 2024"
boilerplate = "Table of Contents\n\n\n\n\n\n\n\n"
check("numeric/table-like text scores higher than boilerplate", score_chunk(dense) > score_chunk(boilerplate))
check("near-empty page scores very low", score_chunk("x") < 1)

# --- LLM JSON parsing robustness ---
check("strips ```json fences", strip_json_fences("```json\n[1,2,3]\n```") == "[1,2,3]")
check("parses clean JSON", parse_json_loose('[{"a": 1}]') == [{"a": 1}])
check("recovers JSON array embedded in stray prose",
      parse_json_loose('Sure, here you go:\n[{"a": 1}]\nHope that helps!') == [{"a": 1}])

# --- fuzzy canonical matching ---
existing = ["delhivery", "reserve_bank_of_india"]
check("near-identical entity slug maps onto existing canonical key",
      _fuzzy_group_key("delhivery_limited", existing, 0.8) == "delhivery")
check("unrelated entity slug is not force-merged",
      _fuzzy_group_key("international_monetary_fund", existing, 0.8) == "international_monetary_fund")
check("attribute token overlap catches 'revenue' vs 'total revenue'",
      _token_overlap("revenue_from_services", "total_revenue_from_services") >= 0.4)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

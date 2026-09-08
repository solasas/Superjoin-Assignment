"""A cheap, content-based (never filename/document-specific) heuristic for
ranking chunks by how likely they are to contain extractable facts.

This exists for the "large PDFs without significant performance issues"
brownie point: a 300-page filing is mostly cover pages, tables of contents,
boilerplate legal language and repeated disclaimers. Sending every page to
an LLM is slow and expensive for very little yield. Instead we score every
chunk with regex features that correlate with "this text asserts checkable
facts" -- density of numbers, currency/percentage symbols, dates, and
Title-Case token runs (a cheap proxy for named entities) -- and only send
the top-scoring chunks to the LLM.

This is intentionally generic: it has no knowledge of "revenue" or
"director" or any other domain word, so it works the same way on a
logistics prospectus or a central bank report.
"""
import re

_NUMBER_RE = re.compile(r"\d[\d,]*\.?\d*")
_PERCENT_RE = re.compile(r"%")
_CURRENCY_RE = re.compile(r"[₹$€£]|(?<![A-Za-z])(?:Rs\.?|INR|USD|Cr|Lakh|Mn|Bn)(?![A-Za-z])")
_DATE_RE = re.compile(
    r"\b(?:19|20)\d{2}\b|\bFY\s?\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
    re.IGNORECASE,
)
_TITLECASE_RUN_RE = re.compile(r"(?:[A-Z][a-zA-Z&.'-]*\s+){1,4}[A-Z][a-zA-Z&.'-]*")
_BOILERPLATE_HINTS = re.compile(
    r"table of contents|this page (?:is|has been) intentionally left blank|"
    r"continued from previous page|see accompanying notes",
    re.IGNORECASE,
)


def score_chunk(text: str) -> float:
    n_chars = max(len(text), 1)
    numbers = len(_NUMBER_RE.findall(text))
    percents = len(_PERCENT_RE.findall(text))
    currency = len(_CURRENCY_RE.findall(text))
    dates = len(_DATE_RE.findall(text))
    titlecase_runs = len(_TITLECASE_RUN_RE.findall(text))

    density = (numbers * 1.0 + percents * 1.5 + currency * 1.5 + dates * 1.2 + titlecase_runs * 0.5)
    score = density / (n_chars / 500.0)  # per ~500 chars, so length-independent

    if _BOILERPLATE_HINTS.search(text):
        score *= 0.3
    if n_chars < 80:
        score *= 0.2  # near-empty pages (covers, section dividers)

    return round(score, 4)


def select_relevant(chunks, keep_fraction: float, min_keep: int):
    """Return (kept_chunks, all_scored) where kept_chunks is the subset to
    actually send to the LLM. Chunks are annotated in place with
    `.relevance_score` and `.kept`.
    """
    scored = []
    for c in chunks:
        c.relevance_score = score_chunk(c.text)
        scored.append(c)

    if keep_fraction >= 1.0 or len(scored) <= min_keep:
        for c in scored:
            c.kept = True
        return scored, scored

    ranked = sorted(scored, key=lambda c: c.relevance_score, reverse=True)
    n_keep = max(min_keep, int(round(len(scored) * keep_fraction)))
    keep_ids = {id(c) for c in ranked[:n_keep]}

    for c in scored:
        c.kept = id(c) in keep_ids

    kept = [c for c in scored if c.kept]
    return kept, scored

# Fact Knowledge Layer

Reads PDFs, extracts checkable facts (numbers, statuses, dates, locations),
grounds every fact in the exact source text, and classifies how facts across
documents relate: **corroborate**, **contradict**, or **reconcilable through
context** (time, scope, units, data vintage).

Built for the Superjoin engineering intern assignment.

## Video Demo

**▶ [Watch the demo (≤3 min)](PASTE_LINK_HERE)** — a PDF ingested, then a walk
through the four required cases with the evidence and the system's reasoning
for each.

Silent screen-capture fallback: [`docs/walkthrough.gif`](docs/walkthrough.gif)
/ [`docs/walkthrough.mp4`](docs/walkthrough.mp4). Narration script:
[`docs/narration.md`](docs/narration.md).

---

## Setup and Run Instructions

### Requirements

- Python 3.10+
- One LLM backend:
  - **Claude Code CLI** (`claude`), logged in — `LLM_BACKEND=claude_cli`
    (default). No API key; slower per call.
  - **Anthropic API key** — `LLM_BACKEND=anthropic_api`. Faster, portable.

### Install

```bash
git clone <this-repo> && cd fact-knowledge-layer
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # set LLM_BACKEND / ANTHROPIC_API_KEY
```

Python 3.10+ is required — the API uses `X | None` annotations evaluated at
import time.

### Run

```bash
./run.sh                 # http://localhost:8000
```

A single-page UI to upload PDFs and browse facts, relations, and the evolving
schema.

### Command line

```bash
python scripts/ingest_cli.py path/to/one.pdf path/to/two.pdf
python scripts/ingest_cli.py --glob "starter_dataset/**/*.pdf"
python scripts/ingest_cli.py "big_report.pdf:22,24,51"   # scope to pages
```

### Offline tests

```bash
python tests/test_core.py
```

Grounding, relevance scoring, JSON recovery, fuzzy matching — the parts with
no LLM call.

### Inspect results without running anything

`data/knowledge.db` (the run this README describes — 6 documents, 423 facts,
153 relations) is committed, so `./run.sh` opens a fully populated UI with no
API key. `sample_output/` holds the same data as JSON + Markdown; regenerate
with `python scripts/export_sample.py`.

---

## Starter dataset

Two independent sets of real, public PDFs (`starter_dataset/`):

- **`delhivery/`** — Delhivery Limited's 2022 IPO prospectus, FY24 annual
  report, and Q4 FY24 earnings presentation. One company, three formats and
  dates.
- **`india-macroeconomy/`** — the Economic Survey 2024-25, RBI Annual Report
  2024-25, and IMF 2025 Article IV report. Three institutions on the same
  economy in the same period.

No code is specific to either set.

---

## The four required cases

Real, unedited output on the starter PDFs. Reproduce with:

```bash
python scripts/ingest_cli.py \
  "starter_dataset/delhivery/01-delhivery-prospectus-2022-excerpt.pdf:1,30" \
  "starter_dataset/delhivery/03-delhivery-q4-fy24-earnings-presentation.pdf:6,8" \
  "starter_dataset/delhivery/02-delhivery-annual-report-fy24-excerpt.pdf:22,24,51"
```

(Page-scoped rather than full — see [Limitations](#limitations-and-next-steps).)

### 1. Corroborated fact

**Delhivery's FY24 revenue, stated two ways in documents ~2 months apart.**

- **A** — *Q4 FY24 Earnings Presentation*, p.6 — quote: *"₹8,142 Cr"*
- **B** — *FY24 Annual Report*, p.22 — quote: *"Revenue from Operations ... 81,415.38"*

**`CORROBORATES`:**
> "Fact A reports ₹8,142 Cr which equals ₹81,420 million, while Fact B reports
> ₹81,415.38 million — both for FY24. The difference of 4.62 million is only
> 0.006% and is attributable to rounding."

Different units (crore vs. million) and labels ("revenue from services" vs.
"revenue from operations, consolidated") for the same figure.

The same behavior held on the unrelated macro set, with zero code changes:
RBI — *"Headline inflation eased by 73 bps to 4.6 per cent in 2024-25"*; IMF —
*"...down from 4.6 percent (FY2024/25 average)"* → `CORROBORATES` ("FY2024/25
and 2024-25 refer to the same Indian fiscal year"). Real GDP growth for
FY2024-25 (6.5%, RBI vs. IMF) matched the same way.

### 2. Genuine contradiction

**Two postal codes for the same street address.**

- **A** — *2022 IPO Prospectus*, p.30 — quote: *"Plot 5, Sector 44 / Gurugram 122002 / Haryana, India"* (three lines in the source)
- **B** — *FY24 Annual Report* (BRSR), p.51 — quote: *"Plot No. 5, Sector 44, Gurugram, Haryana 122001"*

**`CONTRADICTS`** (confidence 0.85):
> "Both facts describe the corporate office at Plot 5, Sector 44, Gurugram,
> Haryana, but Fact A gives the PIN code as 122002 while Fact B gives it as
> 122001. The location details are otherwise identical, making the differing
> postal codes a material contradiction."

Both quotes are verbatim from their pages, so this is a real two-digit
discrepancy between a 2022 filing and a 2024 filing — the kind a proofreader
reading either document alone would miss.

### 3. Apparent contradiction reconciled by context

**A director active in 2022, resigned by 2023 — two documents, over a year apart.**

- **A** — *2022 IPO Prospectus*, p.30 — quote: *"Donald Francis Colleran(1) 09431299 ... Non-Executive Nominee Director"*
- **B** — *FY24 Annual Report*, p.24: "Donald Francis Colleran ... ceased to be
  a Director at the conclusion of the 12th AGM on September 27, 2023..."

**`RECONCILABLE_CONTEXT`:**
> "Fact A states Donald Francis Colleran was a Non-Executive Nominee Director
> as of the Prospectus date, while Fact B reports he ceased to be a Director on
> September 27, 2023. This reflects a legitimate change in status over time."

The assignment's own example, found for real. The system reconciled the same
pattern for two more directors (Suvir Suren Sujan, Sandeep Kumar Barasia) and
for numeric drift over time (gateway count 123 → 111; active customers
23,613 → 33,000+).

**A second kind of context — reporting period, not elapsed time.** Economic
Survey (p.28): inflation *"4.9 per cent in April-December 2024"* (9 months) vs.
RBI (p.17): *"4.6 per cent in 2024-25"* (full year) → `RECONCILABLE_CONTEXT`
("partial-year rate vs. full-year rate"). The same pattern reconciled H1-FY25
GDP growth (6.0%) against the full-year figure (6.5%).

### 4. Extraction / reasoning failure

Three real failure modes, all surfaced through the `extraction_issues` table
and the `grounded` flag rather than by re-reading output:

**(a) Column-interleaved cover page → wrong facts.** Page 1 of the 2022
prospectus lays out registered office / corporate office / contact as parallel
columns; `pdfplumber`'s plain-text extraction linearizes them into interleaved
prose. The extractor mislabeled and merged the two addresses. Both bad facts
were caught (`grounded=0`, confidence capped at 0.35, logged) — but one still
fed a spurious `CONTRADICTS` against the correct page-30 fact. *Fix:*
layout/table-aware extraction on multi-column pages, and exclude `grounded=0`
facts from relation candidates entirely (currently down-weighted, not excluded).

**(b) Wide table rows → correct facts, failed grounding.** Facts from dense
tables were factually right but their `quote` wasn't a contiguous substring of
the linearized text (e.g. `"Revenue from Operations ... 81,415.38"` elides
intervening cells) → `grounded=0`, a false negative. *Fix:* extract tables into
real rows/cells; relax grounding to an in-order subsequence check.

**(c) Fiscal vs. calendar quarters — a reasoning failure.** Both facts cleanly
extracted and grounded. IMF, p.10: *"real GDP growth of 7.8 percent in
2025Q2"*; Economic Survey, p.20: *"5.4 per cent in ... Q2 FY25"*. The
classifier treated `2025Q2` and `Q2 FY25` as the same quarter and returned
`CONTRADICTS`. They are ~9 months apart (Apr–Jun 2025 vs. Jul–Sep 2024); the
facts are likely not in tension. This is why the output is labeled
"contradicts" / "reconcilable" rather than "true" / "false" — every call is a
checkable claim against cited evidence. *Fix:* normalize `temporal_scope` into
an explicit calendar-vs-fiscal form during extraction; have the relation prompt
reason about fiscal-year conventions before equating scopes.

All of these remain in the `facts` / `fact_relations` / `extraction_issues`
tables, filterable via `grounded_only=true` on `/api/facts`.

---

## Approach

### Pipeline

```
PDF --(pdfplumber)--> pages --(chunker)--> chunks --(relevance filter)--> kept chunks
    --(LLM extraction, per chunk)--> grounded, schema-tagged facts
    --(fuzzy entity/attribute match)--> candidate pairs (new vs. existing)
    --(LLM classification, batched)--> CORROBORATES / CONTRADICTS / RECONCILABLE_CONTEXT
```

Every step is document-agnostic — no filename, company name, or fixed schema
is hardcoded. The documents define what a fact is.

### Fact schema: fixed core + open extension

Core columns on every fact: `entity`, `attribute`, `value`, `value_numeric`,
`unit`, `temporal_scope`, `fact_type`, plus grounding evidence (`quote`,
`page`, `document_id`) — the minimum for comparing two facts.

Beyond that, each fact carries an open `attributes` JSON bag the extractor
fills with document-specific detail (`{"scope": "consolidated"}`,
`{"role": "Independent Director"}`, ...). The `schema_registry` table
(`/api/schema`, "Schema" tab) records every key seen, when, and how often —
the effective schema grows as new document types arrive, with no migration.

### Grounding

Every `quote` is checked against its source chunk (exact, with a fuzzy fallback
for PDF noise). A quote that can't be found is still stored but flagged
`grounded=0`, demoted in confidence, and logged to `extraction_issues` — which
is how the case-4 failures were found.

### Comparing facts: recall first, then precision

Two documents rarely word the same fact identically ("revenue from services"
vs. "Revenue from Operations, Group"; "resigned" vs. "ceased to be a
Director"). Two stages:

1. **Candidate generation** — group by fuzzy match on the canonical entity slug
   (legal-suffix stripping, substring-aware), then by attribute similarity or
   token overlap. Intentionally over-inclusive.
2. **Adjudication** — each pair goes to the LLM with both facts' full context
   (value, unit, scope, entity, attribute, verbatim quote) and is classified,
   with a cited explanation. `UNRELATED` pairs are dropped. Deliberately a
   judgment call, not a threshold rule.

### Scale — large PDFs, many PDFs, incremental

- **Relevance pre-filter** (`relevance.py`) — a content-only heuristic scoring
  chunks by density of numbers, currency, percentages, dates, and Title-Case
  runs. Filters boilerplate before the LLM. Tunable via
  `RELEVANCE_KEEP_FRACTION`.
- **Page-scoped ingestion** — `ingest_cli.py path.pdf:22,24,51` processes only
  the named pages while keeping their true page numbers for citations.
- **Incremental** — ingesting document *N+1* only compares its new facts
  against stored ones; existing pairs are never re-classified. O(new facts),
  persisted in SQLite.
- **Dynamic schema** — no migration for a new fact type.

### AI tools used

- **Building the project** — designed and written in a Claude Code session.
- **In the application** — an LLM does fact extraction (`extraction.py`) and
  relation classification (`relations.py`) through a pluggable client
  (`llm_client.py`) with two backends: `claude_cli` (default; used to generate
  every example here) and `anthropic_api` (recommended for new runs — faster
  and cheaper per call).

---

## Limitations and Next Steps

Run behind this README — 6 documents, 14 curated pages:

| Metric | Value |
|---|---|
| Facts extracted | 423 |
| Grounded / ungrounded | 326 / 97 (77%) |
| `CORROBORATES` / `CONTRADICTS` / `RECONCILABLE_CONTEXT` | 17 / 4 / 132 |
| Per-document ingest time (`claude_cli`, `LLM_CONCURRENCY=1`) | 129–1048 s |

- **`claude_cli` latency.** Each headless call pays CLI startup plus
  orchestration overhead — roughly 45–350 s per page, serial. For this
  submission I page-scoped the six PDFs to the sections most likely to hold
  comparable facts (board tables, revenue statements, macro headline figures)
  instead of ingesting all ~300 pages. The pipeline itself has no such limit:
  with `LLM_BACKEND=anthropic_api` and parallel calls, full documents process
  in minutes. This breadth-vs-time tradeoff is the first thing I'd change with
  a real API key.
- **Extraction failures, quantified.** 97/423 facts (23%) are `grounded=0`,
  all logged as `ungrounded_quote`. Case 4 covers representative examples;
  fixing (a)/(b) means layout/table-aware parsing, (c) means normalizing
  fiscal-vs-calendar scope.
- **Canonicalization is fuzzy-string, not semantic.** Catches "Delhivery" vs.
  "Delhivery Limited"; misses "top line" for "revenue". An embedding step (or
  LLM canonicalization against a running registry) would close the gap.
- **No table-structure-aware extraction.** `pdfplumber.extract_text()`
  linearizes multi-column layouts (see case 4). A layout-aware or vision pass
  fixes it at higher cost per page.
- **No PDF deep-link in the UI.** Facts cite page + quote;
  `/api/documents/{id}/file` serves the raw PDF, but the page isn't rendered
  with the quote highlighted.
- **Relation cost scales with candidate pairs.** Fine here; at large scale,
  pre-filter with a numeric-diff heuristic before spending an LLM call.
- **SQLite** is fine for a prototype; Postgres for concurrent writes and JSON
  querying at scale.

---

## Additional Notes

- No credentials in the repo. `.env.example` documents every variable; `.env`
  is gitignored.
- Starter PDFs are included under `starter_dataset/` (public filings); their
  own READMEs note sources and retained pages.
- `data/knowledge.db` and `sample_output/` are committed so results are
  inspectable without an API key. Other runtime artifacts (`data/uploads/`,
  WAL files, `.venv/`) are gitignored.
- Git history groups the codebase by subsystem; the project was built in one
  continuous Claude Code session.

---

## Submission checklist

- [x] **Runs from these instructions, accepts new PDFs** — `./run.sh` (UI
  upload) or `scripts/ingest_cli.py`, same path.
- [x] **Facts + evidence + cross-document relations** — `/api/facts` (each with
  `quote`, `page`, `document_id`, `grounded`), `/api/relations` (both facts,
  both quotes, explanation). In the UI and `sample_output/`.
- [x] **The four required cases** — [above](#the-four-required-cases), real
  output with evidence and reasoning for 1–3, a genuine failure and fixes for 4.
- [x] **Approach documented** — [Approach](#approach),
  [Limitations and Next Steps](#limitations-and-next-steps).
- [ ] **Demo video (≤3 min)** — link at the top once recorded.

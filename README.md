# Fact Knowledge Layer

A small system that reads PDFs, pulls out checkable facts (numbers, statuses,
dates, locations...), grounds every fact in the exact source text it came
from, and then automatically figures out which facts across different
documents **corroborate**, **contradict**, or are only an **apparent**
contradiction once you account for context (time, scope, units, data
vintage).

Built for the Superjoin engineering intern assignment. This README covers
setup, a walkthrough of the four required cases (with real evidence from the
provided starter documents), the approach/architecture, and honest
limitations.

## Video Demo

**▶ [Watch the demo (≤3 min)](PASTE_LINK_HERE)** — a PDF being ingested,
followed by a walk through the four required cases with the evidence and the
system's own reasoning for each.

A silent screen-capture of the same UI walkthrough is committed at
[`docs/walkthrough.gif`](docs/walkthrough.gif) (and `docs/walkthrough.mp4`) as
a fallback; the narration script is at [`docs/narration.md`](docs/narration.md).

---

## Setup and Run Instructions

### 1. Requirements

- Python 3.10+
- Either:
  - **Claude Code CLI** (`claude`) installed and logged in on this machine
    (`LLM_BACKEND=claude_cli`, the default) — zero extra setup, but slower
    per call (see [Approach](#approach)), **or**
  - An **Anthropic API key** (`LLM_BACKEND=anthropic_api`) — faster,
    portable, no local CLI dependency.

### 2. Install

Python **3.10+** is required — the API uses `X | None` type annotations that
FastAPI evaluates at import time on older interpreters.

```bash
git clone <this-repo>
cd fact-knowledge-layer
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit LLM_BACKEND / ANTHROPIC_API_KEY if needed
```

`run.sh` and the `scripts/` entry points also work without activating the
venv, as long as `./.venv` exists.

### 3. Run the server

```bash
./run.sh
# or: uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` — a single-page UI to upload PDFs and browse
facts / relations / the (evolving) schema.

### 4. Or run everything from the command line

Useful for bulk-loading a folder of PDFs, or for reproducing this README's
results without clicking through the UI:

```bash
python scripts/ingest_cli.py path/to/one.pdf path/to/two.pdf
python scripts/ingest_cli.py --glob "starter_dataset/**/*.pdf"

# Scope a big PDF to specific pages you already know matter (see Approach):
python scripts/ingest_cli.py "big_report.pdf:22,24,51"
```

### 5. Run the offline sanity tests

```bash
python3 tests/test_core.py
```

(Grounding, relevance scoring, JSON-recovery and fuzzy entity-matching --
the parts of the pipeline that don't need a live LLM call.)

### 6. Inspect results without running anything

`data/knowledge.db` (the run this README is written against — 6 documents,
423 facts, 153 relations) is committed, so `./run.sh` brings up a fully
populated UI with no API key and no ingestion. `sample_output/` additionally
holds a plain JSON + Markdown dump of that same knowledge base for quick
review. Regenerate the dump after any ingest with:

```bash
python scripts/export_sample.py
```

---

## The starter dataset

Two independent sets of real, public PDFs were provided (`starter_dataset/`):

- `delhivery/` — an IPO prospectus (2022), the FY24 annual report, and the
  Q4 FY24 earnings presentation of Delhivery Limited, an Indian logistics
  company. Same company, three very different document formats and dates.
- `india-macroeconomy/` — the Economic Survey 2024-25, the RBI Annual Report
  2024-25, and the IMF's 2025 Article IV report on India. Three different
  institutions writing about the same economy in the same period.

Nothing in the code is specific to either dataset -- see
[Approach](#approach) for how the system stays generic.

---

## The four required cases

Everything below is **real output** from the running system on the actual
starter PDFs (not hand-picked or edited) -- reproduce it with:

```bash
python scripts/ingest_cli.py \
  "starter_dataset/delhivery/01-delhivery-prospectus-2022-excerpt.pdf:1,30" \
  "starter_dataset/delhivery/03-delhivery-q4-fy24-earnings-presentation.pdf:6,8" \
  "starter_dataset/delhivery/02-delhivery-annual-report-fy24-excerpt.pdf:22,24,51"
```

(Why only those pages and not all ~227 -- see [Limitations](#limitations-and-next-steps).)

### 1. Corroborated fact

**Delhivery's FY24 revenue, stated two ways in two documents ~2 months apart.**

- Fact A -- *Q4 FY24 Earnings Presentation*, p.6: "**Delhivery's revenue from
  services in FY24 was ₹8,142 Cr**" (quote: *"₹8,142 Cr"*)
- Fact B -- *FY24 Annual Report*, p.22: "**Consolidated revenue from
  operations for FY24 was ₹81,415.38 million**" (quote: *"Revenue from
  Operations ... 81,415.38"*)

**System's classification: `CORROBORATES`** (confidence not manually
tuned -- this is the model's own output)
> "Fact A reports ₹8,142 Cr which equals ₹81,420 million, while Fact B
> reports ₹81,415.38 million -- both for FY24. The difference of 4.62
> million is only 0.006% and is attributable to rounding."

The two documents use different units (crore vs. million) and different
labels ("revenue from services" vs. "revenue from operations, consolidated")
for what is, once converted, the same number -- exactly the "expressed
differently" case the assignment describes. The system also independently
corroborated Delhivery's PIN-code reach (18,793, stated identically in the
earnings deck and the MD&A section of the annual report), Deepak Kapoor's
board title, and Sahil Barua's CEO title across documents.

**This generalizes past the corporate dataset, unprompted.** Ingesting the
completely different `india-macroeconomy/` set (Economic Survey, RBI Annual
Report, IMF Article IV -- three institutions, three writing styles, zero
code changes) produced the same behavior. Cleanest example: RBI states
*"Headline inflation eased by 73 bps to 4.6 per cent in 2024-25"*; the IMF
report independently states *"Headline inflation has declined to 1.5 percent
in September 2025, down from 4.6 percent (FY2024/25 average)"*. Classified
`CORROBORATES`: *"Both facts report headline inflation of 4.6 percent for
the same period ... FY2024/25 and 2024-25 refer to the same Indian fiscal
year. The values and time periods match exactly."* Real GDP growth for
FY2024-25 (6.5%, RBI vs. IMF) corroborated the same way.

### 2. Genuine / likely contradiction

**Two different postal codes for the same street address.**

- Fact A -- *2022 IPO Prospectus*, p.30: "**Delhivery Limited's corporate
  office is located at Plot 5, Sector 44, Gurugram 122002, Haryana,
  India**" (quote: *"Plot 5, Sector 44\nGurugram 122002\nHaryana, India"*)
- Fact B -- *FY24 Annual Report* (BRSR section), p.51: "**Delhivery
  Limited's corporate address is Plot No. 5, Sector 44, Gurugram, Haryana
  122001**" (quote: *"Plot No. 5, Sector 44, Gurugram, Haryana 122001"*)

**System's classification: `CONTRADICTS`** (confidence 0.85)
> "Both facts describe the corporate office/address at Plot 5, Sector 44,
> Gurugram, Haryana, but Fact A gives the PIN code as 122002 while Fact B
> gives it as 122001. The location details are otherwise identical, making
> the differing postal codes a material contradiction."

Both facts are individually well-grounded (the quotes are verbatim from
their respective pages), so this isn't an extraction artifact -- it's a
genuine two-digit discrepancy between a 2022 filing and a 2024 filing for
what is otherwise the same "Plot 5, Sector 44, Gurugram" address, almost
certainly a typo in one of the two real, public documents. This is exactly
the kind of small, easy-to-miss inconsistency an automated cross-document
check is useful for -- a human proofreader skimming either document alone
would have no reason to notice it.

(The system also flagged a second candidate contradiction -- 30 vs. 29
"automated sort centers" between two nearby quarters -- which turned out on
inspection to be a grounding/table-extraction artifact rather than a real
data conflict; see Case 4.)

### 3. Apparent contradiction reconciled by context

**A director listed as active in 2022, resigned by 2023 -- across two documents, over a year apart.**

- Fact A -- *2022 IPO Prospectus*, p.30: "**Donald Francis Colleran is
  Non-Executive Nominee Director of Delhivery Limited**" (quote: *"Donald
  Francis Colleran(1) 09431299 ... Non-Executive Nominee Director"*)
- Fact B -- *FY24 Annual Report*, p.24: "**Donald Francis Colleran,
  Non-Executive Director, ceased to be a Director at the conclusion of the
  12th AGM on September 27, 2023, as he was liable to retire by rotation and
  not proposed for re-election due to unwillingness**"

**System's classification: `RECONCILABLE_CONTEXT`**
> "Fact A states Donald Francis Colleran was a Non-Executive Nominee
> Director as of the Prospectus date, while Fact B reports he ceased to be a
> Director on September 27, 2023. This reflects a legitimate change in
> status over time."

This is the assignment's own example, found for real: the prospectus is
dated May 2022; the annual report describes events through FY24
(ended March 2024) and explicitly dates the change (Sept 27, 2023). The
system found two more instances of the same pattern in this dataset --
**Suvir Suren Sujan** (director in the 2022 prospectus, "resigned from the
Board effective August 24, 2023" per the FY24 report) and **Sandeep Kumar
Barasia** (Executive Director in 2022, "resigned ... effective July 01, 2024,
due to personal reasons" per the same report) -- each correctly reconciled
by time rather than flagged as a contradiction. The system also reconciled
several purely numeric apparent-conflicts this way, e.g. gateway count
(123 as of Q4 FY22 vs. 111 as of March 2024) and active-customer count
(23,613 as of Q4 FY22 vs. over 33,000 as of March 2024), both explained as
"network/customer base changed over time" rather than contradictions.

**A second flavor of "context": reporting period, not just elapsed time.**
The macro dataset produced a cleaner, different kind of reconciliation --
same fiscal year, different *slice* of it. Economic Survey (p.28): *"Retail
headline inflation ... has softened from 5.4 per cent in FY24 to **4.9 per
cent in April-December 2024**"* (a 9-month partial-year figure) vs. RBI
Annual Report (p.17): *"headline inflation eased by 73 bps to **4.6 per
cent in 2024-25**"* (the full fiscal year). Classified `RECONCILABLE_CONTEXT`:
> "Fact A reports 4.9% inflation for April-December 2024 (nine months of
> FY25), while Fact B reports 4.6% for the full fiscal year 2024-25. The
> partial-year rate (4.9%) vs. full-year rate (4.6%) indicates lower
> inflation in the remaining months (Jan-Mar 2025)."

The same partial-year-vs-full-year pattern also reconciled Economic Survey's
H1-FY25 real GDP growth (6.0%) against RBI/IMF's full-year FY25 figure
(6.5%) -- a period-scope explanation, not a time-elapsed one, and a good
illustration of "sensible handling of context" generalizing to a domain
(macroeconomic statistics) the system was never told anything about.

### 4. Extraction / reasoning failure

Two distinct, real failure modes turned up, both traceable through the
`extraction_issues` table and the `grounded` flag rather than by manually
re-reading every fact:

**(a) Column-interleaved cover page → wrong facts, not just ungrounded ones.**
Page 1 of the 2022 prospectus lays out "Registered Office / Corporate
Office / Telephone / Website / Contact Person" as parallel table columns.
`pdfplumber`'s plain-text extraction linearizes that into one run of prose
that interleaves fragments from different columns (e.g. *"N24-N34, S24-S34,
Air Cargo Logistics **Plot 5, Sector 44**, Sunil Kumar Bansal Tel: ... Centre-II,
Opposite Gate 6 Cargo **Gurugram 122002** ... Terminal, ... New Delhi
110037..."*). The extractor, reading this linearized mess, genuinely
**mislabeled** the registered office and corporate office addresses --
merging them into one fact and swapping which address went with which
label. Both bad facts were caught: their quotes didn't match the source
closely enough (`grounded=0`, confidence capped at 0.35, logged to
`extraction_issues`), and the same clean facts extracted moments later from
page 30's plain-prose layout (`grounded=1`, confidence 0.95) were correct.
One of these bad facts even fed into a spurious `CONTRADICTS` relation
against the (correct) page-30 fact -- a concrete example of how an
ungrounded fact can cascade into a wrong relation if not filtered out.
*How I'd improve it:* use `pdfplumber`'s layout/table detection (or a
vision-capable pass on the page image) instead of plain linear text
extraction for pages with clear multi-column structure, and exclude
`grounded=0` facts from relation candidate generation entirely (currently
they're included, just down-weighted).

**(b) Wide table rows → correct facts, but quotes that fail grounding.**
Several facts pulled from dense multi-column tables (the Q4 FY24 revenue
table, the operating-metrics table, a sentence split across a column break
on p.24) were **factually correct** but their `quote` field wasn't a
literal contiguous substring of the linearized source text -- e.g. the
model wrote `"Revenue from Operations ... 81,415.38"` (eliding the two
numbers in between) instead of copying the full four-number table row
verbatim, or reconstructed a sentence that was actually split across two
interleaved columns in the raw text. These get `grounded=0` even though the
underlying fact is right -- a **false negative** in the grounding check,
the mirror image of failure (a). *How I'd improve it:* extract tables with
`pdfplumber.extract_table()` (or similar) into actual rows/columns so a
quote can cite one unambiguous cell instead of a linearized row, and relax
grounding to accept "quote's tokens are a subsequence of the source, in
order" rather than requiring a contiguous span.

**(c) A reasoning failure, not just an extraction one: fiscal vs. calendar
quarters.** This one isn't about messy PDF layout at all -- both facts are
cleanly extracted and fully grounded. IMF Article IV, p.10: *"real GDP
growth of **7.8 percent in 2025Q2**"*. Economic Survey, p.20: *"India's GDP
... grew by 6.7 per cent and **5.4 per cent in Q1 and Q2 FY25**,
respectively."* The relation classifier matched these as the same metric,
same quarter, and flagged it:

> **`CONTRADICTS`** (system's actual output): "Both facts measure India's
> real GDP growth at constant prices for **Q2 FY25** (2025Q2 = Q2 FY25),
> but report materially different values: 7.8% (Fact A) vs. 5.4% (Fact B).
> The 2.4 percentage point gap for the same metric in the same quarter is
> substantial and unexplained."

That equivalence is wrong. The IMF's "2025Q2" is calendar-year notation
(April-June 2025); India's fiscal Q2 FY25 is July-September **2024** --
these two "Q2"s are roughly nine months apart, not the same quarter at all.
The underlying facts are probably not in tension; the *relation
classification* made an incorrect temporal-scope equivalence based on
surface label similarity ("2025Q2" ~ "Q2 FY25"), which is a genuine
reasoning gap rather than a data problem. It's a good illustration of why
this system labels its output "contradicts" / "reconcilable" rather than
"true" / "false": every classification is a claim a human should be able to
spot-check against the cited evidence, and this is exactly the kind of
claim that doesn't survive the check. *How I'd improve it:* have the
extractor normalize `temporal_scope` into an explicit, disambiguated form
(calendar-quarter vs. fiscal-quarter, with the fiscal year convention
stated) instead of passing through whatever label the source document
happened to use, and have the relation prompt reason explicitly about
fiscal-year conventions before treating two scopes as equal.

None of these three failures were hidden or cherry-picked out of the
results -- all are sitting in the same `facts` / `fact_relations` /
`extraction_issues` tables as everything else, filterable via
`grounded_only=true` on `/api/facts`.

---

## Approach

### Pipeline

```
PDF --(pdfplumber)--> pages --(chunker)--> chunks --(relevance filter)--> kept chunks
     --(LLM extraction, per chunk)--> facts (grounded + schema-tagged)
     --(fuzzy entity/attribute matching)--> candidate fact pairs (new vs. existing)
     --(LLM relation classification, batched)--> CORROBORATES / CONTRADICTS /
        RECONCILABLE_CONTEXT / UNRELATED (UNRELATED dropped)
```

Every step is written to be **document-agnostic**: nothing hardcodes a
filename, a company name, or a fixed fact schema. The documents themselves
tell the extractor what a "fact" looks like each time.

### Fact schema: fixed core + open extension

Every fact has the same core columns -- `entity`, `attribute`, `value`,
`value_numeric`, `unit`, `temporal_scope`, `fact_type`, and the grounding
evidence (`quote`, `page`, `document_id`). That's the minimum needed to
compare two facts at all.

On top of that, each fact carries an open `attributes` JSON bag that the
extraction prompt is free to fill with whatever document-specific detail
seems worth keeping (`{"scope": "consolidated"}`, `{"role": "Independent
Director"}`, `{"estimate_type": "first_advance_estimate"}`...). A
`schema_registry` table (exposed at `/api/schema` and the "Schema" tab in
the UI) tracks every key that's shown up so far, when it first appeared, and
how often -- so you can literally watch the effective schema grow as new
kinds of documents get ingested, with no migration.

### Grounding

An extracted fact is only as trustworthy as its evidence. Every fact's
`quote` is checked against the actual source chunk text (exact match, with a
fuzzy fallback for PDF-extraction noise like a dropped hyphen or a
mis-decoded currency symbol). A fact whose quote can't be found in its own
source chunk is still stored -- but flagged `grounded=0` and demoted to low
confidence, and logged in `extraction_issues`, rather than silently trusted.
This is also how the extraction-failure case (#4 above) was actually found:
by reading the `extraction_issues` table, not by manually proofreading
output.

### Comparing facts across documents: recall first, then precision

Two facts from different documents rarely use identical wording for "the
same thing" ("revenue from services" vs. "Revenue from Operations, Group";
"Delhivery" vs. "the Company"; "resigned" vs. "ceased to be a Director").
Matching is deliberately two-stage:

1. **Candidate generation (cheap, generous):** facts are grouped by a fuzzy
   match on their extractor-assigned canonical entity slug (stripping
   common legal suffixes, substring-aware similarity -- not just edit
   distance), then, within an entity group, by attribute-slug similarity or
   token overlap. This stage is intentionally over-inclusive.
2. **Adjudication (LLM, precise):** every candidate pair is handed to the
   model with both facts' full context -- value, unit, temporal scope,
   entity, attribute, and the verbatim evidence quote -- and classified as
   `CORROBORATES`, `CONTRADICTS`, `RECONCILABLE_CONTEXT`, or `UNRELATED`
   (dropped), with a short cited explanation. This is where the false
   positives from stage 1 get filtered back out, and where the actual
   "corroborate vs. contradict vs. reconcile" judgment call happens --
   deliberately not a rule ("if numbers differ by >5%, flag it"), because
   the right call depends on reading the surrounding context the same way a
   person would.

### Large PDFs / many PDFs / incremental ingestion

- **Relevance pre-filter:** a cheap, content-only heuristic (`relevance.py`)
  scores each chunk by density of numbers, currency symbols, percentages,
  dates and Title-Case runs -- a proxy for "this text asserts checkable
  facts" -- with no knowledge of what the document is about. On a long
  filing this is most of the boilerplate, cover pages and repeated
  disclaimers filtered out before they ever reach the LLM. It's a knob
  (`RELEVANCE_KEEP_FRACTION`), not a hard rule, so you can trade recall for
  cost/latency.
- **Page-scoped ingestion:** `ingest_cli.py path.pdf:22,24,51` (or the
  equivalent `only_pages` argument to `ingest_document`) processes only the
  named pages of a large PDF while keeping their *true* page numbers for
  citations -- useful when you already know which sections matter, or when
  a document is too large to fully process within a time/cost budget. This
  is a real feature, not just a demo shortcut (see [Limitations](#limitations-and-next-steps)
  for how this was actually used to build this README).
- **Incremental knowledge base:** ingesting document *N+1* only ever
  compares its *new* facts against facts already stored -- existing
  fact-pairs are never re-classified, so adding a document is O(new facts),
  not O(all facts²). Facts and relations persist in SQLite across restarts.
- **Dynamic schema:** covered above -- no migration needed for a new kind of
  fact.

### AI tools used

- **This whole project** (design, code, this README) was built inside a
  Claude Code / Claude (Cowork) session -- i.e. by talking to Claude, which
  wrote and iterated on the code directly in this repo.
- **The application itself** uses an LLM for two jobs: fact extraction
  (`extraction.py`) and relation classification (`relations.py`), via a
  small pluggable client (`llm_client.py`) with two interchangeable
  backends:
  - `claude_cli` (default): shells out to the local `claude` CLI in
    headless mode. This is what was used to actually generate every example
    in this README, since no external API key was available in the build
    environment -- see the honest cost of that choice below.
  - `anthropic_api`: calls the Anthropic Messages API directly with
    `ANTHROPIC_API_KEY`. This is the recommended path for anyone re-running
    this against new PDFs -- much faster and cheaper per call.

---

## Limitations and Next Steps

**Real numbers from the run behind this README** (6 documents, 14 curated
pages, reproducible with the command in
[The four required cases](#the-four-required-cases)):

| | |
|---|---|
| Documents ingested | 6 |
| Facts extracted | 423 |
| Grounded / ungrounded | 326 / 97 (77% grounded) |
| `CORROBORATES` relations | 17 |
| `CONTRADICTS` relations | 4 |
| `RECONCILABLE_CONTEXT` relations | 132 |
| Per-document ingest time | 129s-1048s (see below) |

- **`claude_cli` backend latency.** Every headless CLI call pays full CLI
  startup + (observed) internal multi-model orchestration overhead. Actual
  per-document wall-clock times from the run behind this README (one page
  per LLM call, `LLM_CONCURRENCY=1`): 129s for 1 page/68 facts, 199s for 1
  page/72 facts, 313s for 3 pages/47 facts, 731s for 3 pages/113 facts,
  862s for 3 pages/99 facts, and 1048s for a single dense IMF page that
  yielded 24 facts. That's roughly 45-350s *per page*, not per document --
  and it's serial: this sandbox's 2 vCPUs meant `LLM_CONCURRENCY=4` (the
  default) made every concurrent call time out, so the real run used
  `LLM_CONCURRENCY=1`. Practical effect: for this submission, rather than
  ingesting all ~300 pages across the six starter PDFs end-to-end, the demo
  run used the `path.pdf:pages` page-scoping feature to target the specific
  sections (board/director tables, revenue statements, macro headline
  figures) most likely to contain comparable cross-document facts. The
  *pipeline itself* has no such limitation -- `RELEVANCE_KEEP_FRACTION`,
  chunk size, and concurrency are all env-configurable, and with
  `LLM_BACKEND=anthropic_api` (a handful of parallel HTTP calls instead of
  spawning a CLI process per call) there's no reason full documents
  couldn't be processed unattended, well within minutes rather than hours.
  This tradeoff (breadth of pages processed vs. reliability/time in this
  specific sandbox) is the single biggest thing I'd change with more time
  or a real API key.
- **Extraction failures, quantified.** 97 of 423 facts (23%) came back
  `grounded=0` -- all logged as `ungrounded_quote` issues in
  `extraction_issues`, inspectable via `grounded_only=true` on `/api/facts`.
  Case #4 above walks through representative real examples of both flavors
  found in this data: (a) a linearized multi-column cover page causing the
  extractor to genuinely mislabel and merge two different facts (a true
  extraction bug, and the more concerning of the two), and (b) correct
  facts pulled from wide tables whose `quote` wasn't a *contiguous*
  substring of the source text (a false negative in the grounding check
  itself, not a wrong fact). A third, different kind of failure --
  reasoning rather than extraction -- also turned up: the relation
  classifier equated the IMF's calendar-quarter "2025Q2" with India's
  fiscal "Q2 FY25", nine months apart. Fixing (a)/(b) mostly means better
  layout/table-aware PDF parsing (see next bullet); fixing (c) means
  normalizing `temporal_scope` into an explicit fiscal-vs-calendar form
  during extraction and having the relation prompt reason about fiscal-year
  conventions explicitly rather than trusting label similarity.
- **Entity/attribute canonicalization is fuzzy-string-based, not
  semantic.** It catches "Delhivery" vs. "Delhivery Limited" and "revenue"
  vs. "total revenue", but would miss e.g. "top line" as a synonym for
  "revenue" with no lexical overlap. An embedding-based similarity step (or
  asking the LLM to canonicalize against a running registry instead of
  independently per chunk) would catch more of these at the cost of
  complexity.
- **No table-structure-aware extraction.** Text comes from
  `pdfplumber.extract_text()`, which linearizes multi-column layouts and
  can interleave unrelated columns of a complex table into nonsense text
  (see case #4). A layout-aware extractor (or feeding page images to a
  vision-capable model) would fix this at higher cost per page.
- **No UI-side citation deep-link into the PDF page image** -- facts cite a
  page number and the exact quote, but the UI doesn't render the PDF page
  itself with the quote highlighted. `/api/documents/{id}/file` serves the
  raw PDF, so a viewer could jump to the page; highlighting the exact quote
  on the rendered page is the natural next step.
- **Relation classification cost scales with candidate pairs.** Fine at
  this scale; at real "many PDFs" scale you'd want to cache/skip
  re-classifying pairs whose facts haven't changed (already true) and
  probably pre-filter candidates further with a cheap numeric-diff
  heuristic before spending an LLM call on obviously-identical values.
- Single-writer SQLite is fine for a prototype; a real deployment would want
  Postgres for concurrent writes and better JSON querying of the
  `attributes` bag.

---

## Additional Notes

- No credentials are committed. `.env.example` documents every variable;
  `.env` is gitignored.
- The starter PDFs are included under `starter_dataset/` for reproducibility
  (they're public filings/reports); their own README files (provided with
  the assignment) note original sources and which pages were retained in
  each curated excerpt.
- `data/knowledge.db` and `sample_output/` are committed on purpose so the
  results are inspectable without an API key or a pipeline run. Every other
  runtime artifact (`data/uploads/`, SQLite WAL files, `.venv/`) is
  gitignored.
- Git history was initialized late: the project was built in one continuous
  Claude Code session (see [Approach](#approach)), so the commits group the
  codebase by subsystem rather than replaying that session turn by turn.

---

## Submission checklist

- [x] **Runs from these instructions and accepts new PDFs** — `./run.sh` → UI
  at `localhost:8000` (drag-and-drop upload), or `python scripts/ingest_cli.py`.
  Both go through the same `ingest_document()` path.
- [x] **Results contain facts, source evidence, and cross-document
  relationships** — `/api/facts` returns each fact with its verbatim `quote`,
  `page`, `document_id`, and `grounded` flag; `/api/relations` returns each
  relation with both facts, both evidence quotes, and the classifier's
  explanation. All browsable in the UI and dumped to `sample_output/`.
- [x] **The four required cases** — [documented above](#the-four-required-cases)
  with real, unedited system output: evidence and reasoning for the
  corroboration, the contradiction, and the context-reconciled case, plus a
  genuine extraction/reasoning failure and how it is handled and would be
  improved.
- [x] **Approach documented** — [Approach](#approach) and
  [Limitations and Next Steps](#limitations-and-next-steps).
- [ ] **Demo video (≤3 min)** — link at the top of this README once recorded.

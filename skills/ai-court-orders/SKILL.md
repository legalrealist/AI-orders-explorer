---
name: ai-court-orders
description: Query the AI Court Orders dataset — 900+ U.S. court standing orders, local rules, and judicial decisions about AI use in legal filings (judges sanctioning hallucinated ChatGPT citations, AI-disclosure standing orders, etc.). Use when asked about a judge's or court's AI rules, AI-sanctions cases, AI-disclosure requirements, which judges have AI standing orders, the AI-hallucination sanctions landscape, or to look up a specific AI court order or its PDF. Trigger phrases include "AI court order", "AI standing order", "judge AI rules", "AI sanctions case", "hallucinated citation sanctions", "AI disclosure requirement", "state bar AI opinion".
---

# AI Court Orders

A curated, regularly-refreshed dataset of **900+ U.S. court orders and opinions on AI use in legal proceedings** (May 2023–present), plus state-bar AI ethics opinions. Each record carries the judge, court, state, date, order type, AI type, who it applies to, a plain-English summary, the consequence/outcome, a source link, and — where archived — a self-hosted PDF of the primary document.

Query it with the `orders` CLI: `python3 scripts/orders_cli.py <command>`. Output is **JSON by default** (parse it directly); add `--format table` for human reading.

## When to use

- A user asks what AI rules a **specific judge or court** has, or whether one issued an AI standing order.
- Researching the **AI-sanctions landscape** — who's been sanctioned for hallucinated/fabricated AI citations, attorney vs. pro-se, monetary amounts.
- Finding **AI-disclosure / verification requirements** by jurisdiction.
- Looking up a **specific case** and its primary-source PDF.
- Pulling a **state bar's** AI ethics opinion.

## Anti-triggers (use something else)

- General legal research unrelated to AI use in filings → this dataset is AI-specific only.
- Live PACER/docket lookups or full opinion text → this has summaries + links/PDFs, not full text.
- Non-U.S. matters beyond the few Canada/UK/NZ records present.

## Commands

```bash
python3 scripts/orders_cli.py search "<query>" [filters] [--limit N] [--full]
python3 scripts/orders_cli.py list [filters] [--limit N]
python3 scripts/orders_cli.py get <id>
python3 scripts/orders_cli.py facets <field> [--limit N]     # distinct values + counts
python3 scripts/orders_cli.py stats
python3 scripts/orders_cli.py pdf <id>                        # self-hosted PDF + source links
python3 scripts/orders_cli.py bar [<state>]                   # state bar AI opinions
```

**Filters** (on `search` / `list` / `facets`): `--judge`, `--court`, `--state`, `--type`, `--consequence`, `--ai-type`, `--applies-to`, `--source`, `--jurisdiction`, `--tag`, `--requires`, `--date-from YYYY-MM-DD`, `--date-to YYYY-MM-DD`, `--has-pdf`, `--has-link`, `--count` (print only the match count), `--limit N`, `--full`. (`--count`/`--limit`/`--full` are `search`/`list` only.)

- **`--court`** is normalized in the data (each federal district has one canonical spelling, e.g. `S.D.N.Y.`) and the filter is also alias-aware (`sdny`, `southern district of new york` all work); bankruptcy/appeals courts for the same district are kept distinct.
- **`--judge`** is title-insensitive substring match — `--judge "Pamela Pepper"` matches `Chief Judge Pamela Pepper`, `--judge Wang` matches `Judge Nina Y. Wang`.
- **`--applies-to`** matches multi-value records — `--applies-to Attorneys` matches `Attorneys,Pro Se Litigants`.
- `--state`, `--type`, `--consequence`, `--ai-type`, `--source`, `--jurisdiction` are exact (case-insensitive) — values are fully normalized enums.
- **`--count`** answers "how many X" without counting the array yourself.
- **`--requires`** filters on the per-record `reqs` dict: a record matches when `reqs[KEY]` is set (truthy). Meaningful keys: `disclose` (~128 records), `certify_if_ai` (~106), `verify` (~40), `prohibited` (~20), `certify_all` (~17), `proprietary` (~13). Any key is accepted; an unknown key matches nothing. This is the fastest way to answer "which courts require AI disclosure / a certification?"
- **`facets`** drops court-wide placeholders (`All Judges`, `District Wide`) and empty values by default, so `facets judge` ranks real jurists; pass `--all` to include placeholders. It honors every `search`/`list` filter, so `facets court --consequence sanctions_attorney` ranks courts by attorney-sanction count and `facets court --requires disclose` ranks them by disclosure requirements.

**Known data gaps (agents: filters skip empty values):** ~164 records (17%) have no `judge`, ~28 no `state_abbr`, a few no `applies_to` — these are holes in the upstream source, not bugs. A `--judge`/`--state` filter naturally excludes records whose field is empty. Use `stats` to see totals.

**Enums:**
- `type`: `Judicial Opinion`, `Standing Order`, `Local Rules`, `Administrative Order`, `Practice Direction`
- `consequence`: `sanctions_attorney`, `sanctions_party`, `warning`, or null
- `ai-type`: `Gen AI`, `Any AI`
- `applies-to`: `Attorneys`, `Pro Se Litigants`, `Any Parties`

`search` / `list` return a compact projection (`id, date, state, type, court, judge, consequence, name, summary, pdf, link`); add `--full` for the entire record (reqs, sanction_types, applicableTo, etc.). `get <id>` always returns the full record. In `--format table`, the summary is truncated to one line under each record's name.

## Recipes

```bash
# Attorney sanctions for AI-hallucinated citations, newest first in the result set
orders_cli.py search "hallucinated citations" --consequence sanctions_attorney

# Does a specific judge have an AI standing order?
orders_cli.py list --judge "Judge Nina Y. Wang" --type "Standing Order"

# All AI orders in a state within a date window
orders_cli.py list --state Texas --date-from 2026-01-01 --format table

# Which judges appear most often
orders_cli.py facets judge --limit 20

# Which courts require AI disclosure (or a certification)?
orders_cli.py list --requires disclose --format table
orders_cli.py facets court --requires disclose --limit 20

# Which courts sanction attorneys most for AI misuse?
orders_cli.py facets court --consequence sanctions_attorney --limit 20

# A case's primary-source PDF (self-hosted) + fallback links
orders_cli.py get 42        # full record
orders_cli.py pdf 42        # {pdf, link, original_link}

# A state bar's AI ethics opinion
orders_cli.py bar California
```

## Notes for agents

- **Parse JSON**, don't scrape table output. Default output is JSON.
- `id` is **not stable** across data refreshes (the dataset re-indexes on each merge). For a durable handle to a document, use the `pdf` URL or `link`.
- `pdf` is populated only for records whose primary document was archived (~a third and growing); when empty, use `link`/`original_link`.
- The CLI fetches from `legalhack.io` and falls back to the repo's local `data/processed/*.json` when offline (override the host with `ORDERS_DATA_BASE`).
- Exit code `3` means "no record with that id".

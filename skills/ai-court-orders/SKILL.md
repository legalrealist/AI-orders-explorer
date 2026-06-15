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

**Filters** (on `search` / `list`): `--judge`, `--court`, `--state`, `--type`, `--consequence`, `--ai-type`, `--applies-to`, `--source`, `--jurisdiction`, `--tag`, `--date-from YYYY-MM-DD`, `--date-to YYYY-MM-DD`, `--has-pdf`, `--has-link`.

**Enums:**
- `type`: `Judicial Opinion`, `Standing Order`, `Local Rules`, `Administrative Order`, `Practice Direction`
- `consequence`: `sanctions_attorney`, `sanctions_party`, `warning`, or null
- `ai-type`: `Gen AI`, `Any AI`
- `applies-to`: `Attorneys`, `Pro Se Litigants`, `Any Parties`

`search` / `list` return a compact projection (`id, date, state, type, judge, consequence, name, pdf, link`); add `--full` for the entire record (summary, reqs, sanction_types, applicableTo, etc.). `get <id>` always returns the full record.

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

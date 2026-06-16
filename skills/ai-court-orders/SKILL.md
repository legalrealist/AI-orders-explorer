---
name: ai-court-orders
description: Query the AI Court Orders dataset — 900+ U.S. court standing orders, local rules, and judicial decisions about AI use in legal filings (judges sanctioning hallucinated ChatGPT citations, AI-disclosure standing orders, etc.). Use when asked about a judge's or court's AI rules, AI-sanctions cases, AI-disclosure requirements, which judges have AI standing orders, the AI-hallucination sanctions landscape, or to look up a specific AI court order or its PDF. Trigger phrases include "AI court order", "AI standing order", "judge AI rules", "AI sanctions case", "hallucinated citation sanctions", "AI disclosure requirement", "state bar AI opinion".
---

# AI Court Orders

A curated, regularly-refreshed dataset of **900+ U.S. court orders and opinions on AI use in legal proceedings** (May 2023–present), plus state-bar AI ethics opinions. Each record carries the judge, court, state, date, order type, AI type, who it applies to, a plain-English summary, the consequence/outcome, a source link, and — where archived — a self-hosted PDF of the primary document.

Query it with the bundled `orders_cli.py`: `python3 orders_cli.py <command>`. The CLI ships alongside this skill (and lives at `scripts/orders_cli.py` inside the AI-orders-explorer repo) — run whichever path exists. It fetches data from legalhack.io with a local fallback, so no other files are required. Output is **JSON by default** (parse it directly); add `--format table` for human reading.

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
python3 orders_cli.py search "<query>" [filters] [--limit N] [--full]
python3 orders_cli.py list [filters] [--limit N]
python3 orders_cli.py get <id>
python3 orders_cli.py facets <field> [--limit N]     # distinct values + counts
python3 orders_cli.py stats
python3 orders_cli.py pdf <id>                        # self-hosted PDF + source links
python3 orders_cli.py bar [<state>]                   # state bar AI opinions
```

**Filters** (on `search` / `list` / `facets`): `--judge`, `--court`, `--state`, `--type`, `--consequence`, `--ai-type`, `--ai-tool`, `--applies-to`, `--source`, `--jurisdiction`, `--tag`, `--requires`, `--date-from YYYY-MM-DD`, `--date-to YYYY-MM-DD`, `--has-pdf`, `--has-link`, `--pending`, `--final`, `--count` (print only the match count), `--limit N`, `--full`. (`--count`/`--limit`/`--full` are `search`/`list` only.)

- **`--court`** is normalized in the data (each federal district has one canonical spelling, e.g. `S.D.N.Y.`) and the filter is also alias-aware (`sdny`, `southern district of new york` all work); bankruptcy/appeals courts for the same district are kept distinct.
- **`--judge`** is title-insensitive substring match — `--judge "Pamela Pepper"` matches `Chief Judge Pamela Pepper`, `--judge Wang` matches `Judge Nina Y. Wang`.
- **`--applies-to`** matches multi-value records — `--applies-to Attorneys` matches `Attorneys,Pro Se Litigants`.
- `--state`, `--type`, `--consequence`, `--ai-type`, `--ai-tool`, `--source`, `--jurisdiction` are exact (case-insensitive) — values are fully normalized enums.
- **`--ai-tool`** filters by the *specific* AI product when the order names one (e.g. `--ai-tool ChatGPT`, `--ai-tool Claude`). `--ai-type` is the coarse `Gen AI`/`Any AI` split; `--ai-tool` is the named product. ~80 records name a tool; the rest are blank. `facets ai_tool` gives the full breakdown.
- **`--count`** answers "how many X" without counting the array yourself.
- **`--requires`** filters on the per-record `reqs` dict: a record matches when `reqs[KEY]` is set (truthy). Meaningful keys: `disclose` (~128 records), `certify_if_ai` (~106), `verify` (~40), `prohibited` (~20), `certify_all` (~17), `proprietary` (~13). Any key is accepted; an unknown key matches nothing. This is the fastest way to answer "which courts require AI disclosure / a certification?"
- **`--pending` / `--final`** distinguish *proposed* from *imposed* sanctions via the per-record `pending` boolean. `pending: true` (~7 records) marks a sanction that is not yet final — an order to show cause, a magistrate's Report & Recommendation awaiting adoption, or a deferred/pending ruling. `--pending` returns only those; `--final` excludes them. Records without the flag (and all non-litigation orders) count as final. Use `--final` when ranking sanctions by amount/severity so a threatened sanction isn't counted as imposed.
- **`facets`** drops court-wide placeholders (`All Judges`, `District Wide`) and empty values by default, so `facets judge` ranks real jurists; pass `--all` to include placeholders. It honors every `search`/`list` filter, so `facets court --consequence sanctions_attorney` ranks courts by attorney-sanction count and `facets court --requires disclose` ranks them by disclosure requirements.

**Known data gaps (agents: filters skip empty values):** ~54 records (6%) have no `judge`, ~28 no `state_abbr`, a few no `applies_to` — these are holes in the upstream source (no judge named anywhere in the record), not bugs. A `--judge`/`--state` filter naturally excludes records whose field is empty. Use `stats` to see totals.

**Enums:**
- `type`: `Judicial Opinion`, `Standing Order`, `Local Rules`, `Administrative Order`, `Practice Direction`
- `consequence`: `sanctions_attorney`, `sanctions_party`, `warning`, or null
- `ai-type`: `Gen AI`, `Any AI`
- `ai-tool` (specific product, when named): `ChatGPT`, `Claude`, `Google Gemini`, `Microsoft Copilot`, `Westlaw CoCounsel`, `Grok`, `Perplexity`, `Callidus AI`, … or empty (~80 records named)
- `applies-to`: `Attorneys`, `Pro Se Litigants`, `Any Parties`

`search` / `list` return a compact projection (`id, slug, date, state, type, court, judge, consequence, pending, ai_tool, name, summary, pdf, link`); add `--full` for the entire record (reqs, sanction_types, applicableTo, `last_verified`, etc.). `get <id>` always returns the full record. In `--format table`, the summary is truncated to one line under each record's name.

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

# Which courts sanction attorneys most for AI misuse? (final, imposed sanctions only)
orders_cli.py facets court --consequence sanctions_attorney --final --limit 20

# Proposed / not-yet-final sanctions (show-cause, R&R, deferred rulings)
orders_cli.py list --pending --format table

# Which specific AI tools show up in cases (ChatGPT vs Claude vs Copilot …)
orders_cli.py facets ai_tool
orders_cli.py list --ai-tool Claude --format table

# A case's primary-source PDF (self-hosted) + fallback links
orders_cli.py get 42        # full record
orders_cli.py pdf 42        # {pdf, link, original_link}

# A state bar's AI ethics opinion
orders_cli.py bar California
```

## Notes for agents

- **Parse JSON**, don't scrape table output. Default output is JSON.
- `id` is **not stable** across data refreshes (the dataset re-indexes on each merge). For a durable handle, use the per-case `slug` on litigation records — `get <slug>` resolves it (e.g. `get hatfield-v-pirani`) — or the `pdf` URL / `link`. `last_verified` carries the upstream curator's last-checked date.
- `pdf` is populated only for records whose primary document was archived (~a third and growing); when empty, use `link`/`original_link`.
- The CLI fetches from `legalhack.io` (override the host with `ORDERS_DATA_BASE`), falling back to the repo's local `data/processed/*.json` when run inside the AI-orders-explorer checkout. A standalone skill install has no local copy, so it needs network access.
- Exit code `3` means "no record with that id"; exit code `4` means the dataset couldn't be reached (network down and no local copy).

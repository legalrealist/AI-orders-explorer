# AI Court Orders Explorer

Has your judge issued an AI standing order? What happens when attorneys use ChatGPT to draft filings?

This is a searchable database of **730+ court orders and opinions on AI use in legal proceedings**, from May 2023 to present. Search by judge, state, court, order type, or outcome — with free links to original sources on CourtListener. No Westlaw or Lexis required.

**[Search the database →](https://legalhack.io/explorer)** | **[Charts & trends →](https://legalhack.io/data/charts)** | Companion to the [LegalRealist AI Landscape](https://legalrealist.ai) series ([analysis post](https://legalrealist.ai/posts/31-ai-court-orders-explorer/))

## What's in the data

**736 entries** across **61 jurisdictions** (May 2023 – May 2026):

| Type | Count |
|------|-------|
| Judicial Opinions | 547 |
| Standing Orders | 121 |
| Administrative Orders | 35 |
| Local Rules | 29 |
| Practice Directions | 4 |

**Outcomes tracked:**

| Consequence | Count |
|-------------|-------|
| Warning issued | 288 |
| Sanctions on attorney | 145 |
| Sanctions on party | 93 |

Each entry includes judge name, court, state, date, order type, AI type (generative AI vs other), who it applies to, a plain-English summary, disclosure/verification requirements, and consequence.

## Data sources

| Source | What it provides |
|--------|-----------------|
| [Ropes & Gray AI Court Order Tracker](https://www.ropesgray.com/en/sites/artificial-intelligence-court-order-tracker) | Primary source — court orders & opinions via Sitecore API |
| [LegalAIGovernance](https://legalaigovernance.com/) | Bar opinions (`bar_opinions.json`) |
| [CourtListener](https://www.courtlistener.com/) | Free-link replacement for paywalled Lexis citations |

All data sourced from public court records. The pipeline deduplicates on date + state + judge, converts entries via AI with regex fallback, and replaces paywalled links with free alternatives where available.

## Why this exists

Courts are issuing AI orders at an accelerating pace — standing orders requiring disclosure, opinions sanctioning attorneys for AI-generated hallucinated citations, local rules mandating verification. But there's no single place to search them by judge, jurisdiction, or outcome.

This project fills that gap: a free, searchable, regularly updated database with direct links to source documents. If you're advising a client on AI disclosure obligations, preparing for a hearing before a specific judge, or researching the sanctions landscape, this is the starting point.

## Updating the data

```bash
export OPENROUTER_API_KEY="…"   # required: AI conversion of new entries
export CL_API_KEY="…"           # optional: CourtListener link replacement

python3 scripts/update.py             # incremental: fetch new entries, swap Lexis→CL links
python3 scripts/update.py --backfill  # one-time: replace Lexis links across all existing entries
```

The pipeline is incremental — it appends new entries without regenerating existing records. New entries are fetched from the R&G Sitecore API, deduplicated, converted to the explorer schema via OpenRouter AI (with regex fallback), and written to `data/processed/explorer_data.json`.

## Output files

- **`data/processed/explorer_data.json`** — the full dataset (also mirrored to `charts/data/`)
- **`data/processed/bar_opinions.json`** — state bar AI guidance
- **`charts/explorer.html`** — the explorer web app
- **`charts/*.html`** — standalone Plotly trend charts

## For developers

The explorer is a single-page HTML app (`charts/explorer.html`) with no build step — just HTML + vanilla JS + Plotly. The data pipeline is Python.

When hosted on legalhack.io, the explorer includes a brand header (marked by HTML comments). To run standalone elsewhere, delete that block.

## License

Data sourced from public court records via [Ropes & Gray](https://www.ropesgray.com/en/sites/artificial-intelligence-court-order-tracker), [LegalAIGovernance](https://legalaigovernance.com/), and [CourtListener](https://www.courtlistener.com/). Scripts and analysis are open source.

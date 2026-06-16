---
title: "feat: Practitioner-ergonomics pass on orders_cli.py"
date: 2026-06-15
type: feat
depth: standard
status: ready
---

# feat: Practitioner-ergonomics pass on `orders_cli.py`

## Summary

Three small, low-risk additions to the `orders` CLI ([scripts/orders_cli.py](scripts/orders_cli.py)) that make the questions practitioners actually ask answerable without dropping into custom Python:

1. **`--requires <key>`** — filter on the `reqs` dict so *"which courts require AI disclosure / a certification / verification?"* is a one-liner. 128 records flag `disclose`, 106 `certify_if_ai`, 40 `verify`, 20 `prohibited`, 17 `certify_all`, 13 `proprietary` — all currently unreachable from the CLI.
2. **Filter-aware `facets`** — let `facets` accept the same filters as `search`/`list`, enabling cross-tabs like sanctions-by-court or standing-orders-by-court (this session needed hand-written Counter scripts for exactly this).
3. **Summary snippet in `--format table`** — surface a truncated `summary` line so a human scanning results sees *what each order says*, not just its name.

Scope is **CLI + SKILL.md only**. No data regeneration, no schema migration, no changes to the ingest/update pipeline ([scripts/update.py](scripts/update.py), [scripts/normalize.py](scripts/normalize.py)). Data-quality work (backfilling sparse `reqs`, repairing weak links) is explicitly out of scope.

---

## Problem Frame

The CLI exposes the dataset well for full-text and enum-field queries, but two practitioner-critical capabilities are missing and one output mode is thin:

- **`reqs` is well-populated but completely unqueryable.** The richest practitioner signal in the dataset — what a court actually *requires* (disclosure, certification, verification, prohibition) — lives in the per-record `reqs` dict and has no filter flag. A practitioner asking "which courts require AI disclosure?" cannot get an answer from the CLI.
- **No aggregation respects filters.** `facets` runs over the entire dataset only. Ranking questions ("who sanctions the most?", "which courts have the most standing orders?") require exporting `--full` JSON and counting by hand.
- **`table` output hides the summary.** The projection shows `name` but not `summary`, so the human-readable mode omits the one field that says what the order holds.

These are friction points hit directly during dogfooding this session.

---

## Requirements

- **R1.** A `--requires <key>` filter on `search` and `list` returns only records whose `reqs[key]` is truthy. Supported on both subcommands via the shared filter args.
- **R2.** `--requires` accepts any `reqs` key; the practitioner-meaningful set (`disclose`, `certify_if_ai`, `certify_all`, `verify`, `prohibited`, `proprietary`) is documented in `--help` and SKILL.md.
- **R3.** `facets <field>` accepts every filter `search`/`list` accepts (`--court`, `--state`, `--type`, `--consequence`, `--requires`, date range, etc.) and computes counts over the filtered subset.
- **R4.** `--format table` for record results shows a third line: a truncated `summary` (omitted cleanly when the record has no summary).
- **R5.** `summary` is available in the data the table renderer sees, without bloating the default JSON projection contract more than necessary, and the SKILL.md projection field list stays accurate.
- **R6.** Existing behavior is preserved: JSON-by-default, exit code 3 for unknown id, placeholder-dropping in facets, all current filters. All existing tests in [scripts/tests/test_orders_cli.py](scripts/tests/test_orders_cli.py) continue to pass.
- **R7.** SKILL.md filter list, facets description, and recipes reflect the new capabilities.

---

## Key Technical Decisions

- **KTD1 — `--requires` is a single-key truthiness filter, not a multi-key expression.** One `--requires disclose` matches `reqs.disclose` truthy. This mirrors the existing flat flag style (`--has-pdf`, `--consequence`) and keeps the data-noise surface small. Compound logic (disclose AND verify) is out of scope; a practitioner can pipe or re-filter. Rationale: the `reqs` values are heterogeneous (booleans, strings like `rules: "FRCP 11"`), so "truthy" is the only uniformly safe predicate.
- **KTD2 — `--requires` validates loosely.** Any key string is accepted (forward-compatible with new `reqs` keys from future data refreshes); an unknown key simply matches nothing rather than erroring. `--help` lists the meaningful set as guidance. Rationale: matches the dataset's "filters skip empty values" philosophy already documented in SKILL.md.
- **KTD3 — Filter-aware facets reuses `apply_filters`, no new code path.** `cmd_facets` runs `apply_filters(load_orders(), filters)` before `facet(...)`. The facets subparser gains the same filter args as `search`/`list` via `_add_filter_args`-style sharing. Rationale: zero duplication; cross-tabs are correct by construction because they use the identical filter engine.
- **KTD4 — `summary` joins the projection; table truncates, JSON keeps full text.** Add `summary` to `_LIST_FIELDS` so both JSON and table consumers get it. The table renderer truncates to a fixed width (~120 chars); JSON returns the full string. Rationale: agents parsing the projection benefit from the summary too, and a single projection list keeps one source of truth. The SKILL.md "compact projection" note is updated to list `summary`.

---

## Implementation Units

### U1. Add `--requires` filter

**Goal:** Expose the `reqs` dict as a CLI filter on `search` and `list`.
**Requirements:** R1, R2, R6
**Dependencies:** none
**Files:**
- [scripts/orders_cli.py](scripts/orders_cli.py) — modify
- [scripts/tests/test_orders_cli.py](scripts/tests/test_orders_cli.py) — modify

**Approach:**
- Add `requires` to the dict returned by `_filters_from_args` (read from `a.requires`).
- Add `--requires` to `_add_filter_args` with help text naming the meaningful keys (`disclose, certify_if_ai, certify_all, verify, prohibited, proprietary`).
- In `apply_filters`, add a clause: if `filters.get('requires')`, skip records where `not (r.get('reqs') or {}).get(filters['requires'])`.
- Place the clause alongside the other optional-filter clauses (after `applies_to`, before/near `has_pdf`).

**Patterns to follow:** the existing `has_pdf`/`has_link` boolean clauses in `apply_filters` and the `--has-pdf` arg registration in `_add_filter_args`.

**Test scenarios:**
- `apply_filters` with `requires='disclose'` returns only the record whose `reqs.disclose` is truthy (use a fixture record with `reqs={'disclose': True}` and one with `reqs={}`).
- `requires` for a key present-but-falsy (`reqs={'disclose': False}`) excludes that record.
- `requires` for a string-valued key (`reqs={'rules': 'FRCP 11'}`) includes the record (truthy non-bool).
- `requires` for an unknown key returns zero records, no exception.
- A record with no `reqs` key at all is excluded, no exception (KTD2 / R6 null-safety).
- `--requires` composes with another filter (e.g. `--type "Standing Order" --requires disclose`) — AND semantics.

**Verification:** `python3 scripts/orders_cli.py list --requires disclose --count` returns a nonzero count near 128; `--requires certify_if_ai --count` near 106.

### U2. Make `facets` filter-aware

**Goal:** `facets` computes counts over the filtered subset, enabling cross-tabs.
**Requirements:** R3, R6
**Dependencies:** U1 (so `--requires` is among the facet filters)
**Files:**
- [scripts/orders_cli.py](scripts/orders_cli.py) — modify
- [scripts/tests/test_orders_cli.py](scripts/tests/test_orders_cli.py) — modify

**Approach:**
- Add the shared filter args to the `facets` subparser. The `facets` parser currently defines its own `--limit` and `--all`; reconcile so `_add_filter_args` (which also adds `--limit`) does not double-register. Either: (a) call a filter-args helper that excludes `--limit`/`--full`/`--count`, or (b) keep `facets` defining `--limit`/`--all` and add only the filter flags it needs. Prefer (a): extract the filter-flag registration so `facets` gets `--judge/--court/--state/--type/--consequence/--ai-type/--applies-to/--source/--jurisdiction/--tag/--date-from/--date-to/--has-pdf/--has-link/--requires` without the result-shaping flags.
- In `cmd_facets`: build filters via `_filters_from_args(a)` and run `facet(apply_filters(load_orders(), filters), a.field, a.limit, include_all=a.all)`.
- Guard `_filters_from_args` against attributes the facets parser doesn't define (it has no `--full`/`--count`) — read with `getattr(a, ..., None)` or ensure the facets parser defines exactly the filter attrs `_filters_from_args` reads.

**Approach note (refactor seam):** Split `_add_filter_args` into `_add_filter_flags(p)` (the query filters) and the result-shaping flags (`--limit`/`--full`/`--count`), so `search`/`list` call both and `facets` calls only `_add_filter_flags` plus its own `--limit`/`--all`. This is the cleanest way to avoid `--limit` collision and keep one source of truth for filter flags.

**Patterns to follow:** `cmd_list` delegating to `cmd_search`; the existing `_filters_from_args` / `_add_filter_args` pairing.

**Test scenarios:**
- `facet` over a filtered subset: `apply_filters(RECS, {'consequence': 'sanctions_attorney'})` then `facet(..., 'court')` returns counts only for sanctioned records.
- `cmd_facets` end-to-end (via `redirect_stdout`, mirroring existing CLI tests) with `--consequence sanctions_attorney` field `court` produces the expected court→count map.
- `facets` with `--requires disclose` field `court` counts only disclosure-requiring records by court.
- `facets` with no filters reproduces the current whole-dataset behavior (regression guard).
- `facets --all` still includes placeholders after the refactor.
- `--limit` on `facets` still truncates and does not collide with any filter arg (argparse builds without error).

**Verification:** `python3 scripts/orders_cli.py facets court --consequence sanctions_attorney` returns C.D. Cal. at the top with a count matching the hand-counted 16 from this session.

### U3. Summary snippet in table output + projection

**Goal:** Table mode shows a truncated summary; `summary` is in the projection.
**Requirements:** R4, R5, R6
**Dependencies:** none (independent of U1/U2)
**Files:**
- [scripts/orders_cli.py](scripts/orders_cli.py) — modify
- [scripts/tests/test_orders_cli.py](scripts/tests/test_orders_cli.py) — modify

**Approach:**
- Add `'summary'` to `_LIST_FIELDS` (after `name`).
- In `_print_table`'s record branch, after the `name` line, print a third indented line with the summary truncated to ~120 chars, only when `r.get('summary')` is non-empty.
- Confirm `get`/`pdf`/`stats`/`facets` table rendering is unaffected (they route through the dict/value branches, not the record branch).

**Patterns to follow:** the existing two-line record format in `_print_table` (`[id] date state type consequence` / indented `name`).

**Test scenarios:**
- `_project(record)` now includes a `summary` key (regression on `_LIST_FIELDS` contents).
- Table output for a record with a long summary contains a truncated summary line (assert substring + max length).
- Table output for a record with empty/missing summary prints no summary line and does not error.
- JSON projection output for the same record contains the **full** untruncated summary (truncation is table-only).
- `facets` table output (value/count rows) is unchanged — no summary line leaks into the facet branch.

**Verification:** `python3 scripts/orders_cli.py list --limit 3 --format table` shows a summary line under each name; `... --limit 3` (JSON) shows full `summary` values.

### U4. Update SKILL.md

**Goal:** Documentation matches the new CLI surface.
**Requirements:** R2, R7
**Dependencies:** U1, U2, U3
**Files:**
- [.claude/skills/ai-court-orders/SKILL.md](.claude/skills/ai-court-orders/SKILL.md) — modify

**Approach:**
- Add `--requires` to the **Filters** list with the meaningful-key enumeration and the "matches any truthy `reqs` key; unknown keys match nothing" note.
- Update the **`facets`** bullet to state it now honors all `search`/`list` filters, with a cross-tab recipe (e.g. `facets court --consequence sanctions_attorney`).
- Update the projection description (currently `id, date, state, type, judge, consequence, name, pdf, link`) to include `summary`.
- Add 1–2 recipes: "which courts require AI disclosure" (`list --requires disclose`) and "sanctions by court" (`facets court --consequence sanctions_attorney`).

**Test scenarios:** `Test expectation: none — documentation-only change.` Verify by re-reading the edited sections for accuracy against the shipped CLI `--help`.

**Verification:** SKILL.md filter list, facets note, projection list, and recipes all describe behavior the CLI actually exhibits.

---

## Scope Boundaries

**In scope:** filter/aggregation/output changes to [scripts/orders_cli.py](scripts/orders_cli.py), matching tests in [scripts/tests/test_orders_cli.py](scripts/tests/test_orders_cli.py), and SKILL.md documentation.

### Deferred to Follow-Up Work
- **Data-quality remediation** — backfilling sparse `reqs` flags during ingest, repairing weak/stale links (e.g. the Judge Walton record pointing at a court webpage rather than the order PDF). Touches [scripts/update.py](scripts/update.py)/[scripts/normalize.py](scripts/normalize.py) and the dataset; a separate, larger effort.
- **Compound `--requires` expressions** (AND/OR across multiple `reqs` keys) — KTD1 keeps the first cut single-key.
- **`--sort`** — unnecessary: `explorer_data.json` ships pre-sorted date-descending, so results are already newest-first.

---

## Risks & Dependencies

- **`--limit` collision on the `facets` parser** (U2). The `facets` subparser already defines `--limit`; naive reuse of `_add_filter_args` double-registers it and argparse raises at build time. Mitigated by the `_add_filter_flags` split in U2's approach note — verify the parser builds in a test.
- **`_filters_from_args` attribute access** (U2). It reads `a.full`/etc. indirectly via callers; the facets parser must define every attribute `_filters_from_args` reads, or that helper must use `getattr` defaults. Covered by the "argparse builds without error" + end-to-end facets test scenarios.
- **Projection contract change** (U3). Adding `summary` to `_LIST_FIELDS` changes default JSON output shape. Low risk (additive), but SKILL.md must be updated in lockstep (U4) so the documented projection stays accurate.

---

## Verification Strategy

- Run `python3 -m pytest scripts/tests/test_orders_cli.py` — all existing + new tests green.
- Manual spot-checks (the per-unit Verification lines) against the live/local dataset: disclosure count ~128, certify_if_ai ~106, sanctions-by-court led by C.D. Cal. (16).
- Re-read SKILL.md against `orders ... --help` for doc/code parity.

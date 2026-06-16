#!/usr/bin/env python3
"""Re-derive LAG-sourced fields offline and apply them to explorer_data.json.

No network: reads the cached LAG source (data/sources/lag_cases.json), re-runs
the converter (fixed judge prose-fallback + outcome-enriched summary), and
enriches existing records in place by docket/party identity. Never adds or drops
records. Then renormalizes and validates before writing.

  judge   : filled when a record currently has none.
  summary : replaced for LAG-only 'rails' records (LAG is the source of truth);
            'both'/'rg' records keep their authoritative R&G summary.

Usage:
    python3 scripts/apply_lag_fixes.py            # dry run (report only)
    python3 scripts/apply_lag_fixes.py --write     # apply and write outputs
"""

import json
import os
import sys

import lag_cases
import lag_convert
import lag_merge
import normalize
import schema

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
EXPLORER_PATH = os.path.join(PROJECT_DIR, 'data', 'processed', 'explorer_data.json')
CHARTS_PATH = os.path.join(PROJECT_DIR, 'charts', 'data', 'explorer_data.json')


def _identity(rec):
    blob = (rec.get('name', '') or '') + ' ' + (rec.get('summary', '') or '')
    docket = lag_merge.extract_docket(blob)
    party = lag_merge.extract_parties(rec.get('name', '')) or lag_merge.extract_parties(blob)
    return docket, party


def build_lag_index(lag_recs):
    by_docket, by_party = {}, {}
    for lr in lag_recs:
        docket, party = _identity(lr)
        if docket:
            by_docket.setdefault(docket, lr)
        if party:
            by_party.setdefault(party, lr)
    return by_docket, by_party


def find_lag(rec, by_docket, by_party):
    docket, party = _identity(rec)
    if docket and docket in by_docket:
        return by_docket[docket]
    if party and party in by_party:
        return by_party[party]
    return None


def enrich(records, lag_recs):
    by_docket, by_party = build_lag_index(lag_recs)
    stats = {'judge_filled': 0, 'summary_updated': 0, 'matched': 0}
    for rec in records:
        lr = find_lag(rec, by_docket, by_party)
        if not lr:
            continue
        stats['matched'] += 1
        if not rec.get('judge') and lr.get('judge'):
            rec['judge'] = lr['judge']
            stats['judge_filled'] += 1
        if rec.get('source') == 'rails' and lr.get('summary') and lr['summary'] != rec.get('summary'):
            rec['summary'] = lr['summary']
            stats['summary_updated'] += 1
    return stats


def main():
    write = '--write' in sys.argv
    records = json.load(open(EXPLORER_PATH, encoding='utf-8'))
    lag_recs = lag_convert.convert_all(lag_cases.items(lag_cases.load_cached()))

    before = len(records)
    stats = enrich(records, lag_recs)
    normalize.normalize(records)
    normalize.mark_unverified(records)

    assert len(records) == before, 'record count changed — aborting'
    problems = schema.validate_dataset(records)
    if problems:
        print(f'ABORT: {len(problems)} validation problems')
        for p in problems[:10]:
            print('  ', p)
        raise SystemExit(1)

    print(f'records: {before}  matched LAG: {stats["matched"]}')
    print(f'judge filled: {stats["judge_filled"]}  summary updated: {stats["summary_updated"]}')

    if not write:
        print('\nDRY RUN — nothing written. Re-run with --write to apply.')
        return
    payload = json.dumps(records, ensure_ascii=False, indent=2)
    for p in (EXPLORER_PATH, CHARTS_PATH):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(payload)
    print(f'\nWrote {before} records to:\n  {EXPLORER_PATH}\n  {CHARTS_PATH}')


if __name__ == '__main__':
    main()

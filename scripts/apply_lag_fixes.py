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
import re
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


def _name_key(rec):
    return re.sub(r'[^a-z0-9]', '', (rec.get('name', '') or '').lower())


def _identity(rec):
    blob = (rec.get('name', '') or '') + ' ' + (rec.get('summary', '') or '')
    docket = lag_merge.extract_docket(blob)
    party = lag_merge.extract_parties(rec.get('name', '')) or lag_merge.extract_parties(blob)
    return docket, party


def _unambiguous(lists):
    """Keep only keys that map to a single case (one distinct slug)."""
    out = {}
    for key, lrs in lists.items():
        ids = {lr.get('slug') or id(lr) for lr in lrs}
        if len(ids) == 1:
            out[key] = lrs[0]
    return out


def build_lag_index(lag_recs):
    by_docket, party_lists, name_lists = {}, {}, {}
    for lr in lag_recs:
        docket, party = _identity(lr)
        if docket:
            by_docket.setdefault(docket, lr)
        if party:
            party_lists.setdefault(party, []).append(lr)
        nk = _name_key(lr)
        if nk:
            name_lists.setdefault(nk, []).append(lr)
    # Generic party pairs ("X LLC v. City of Y" -> ('llc','city')) and repeated
    # case names collide across unrelated matters; matching on an ambiguous key
    # would graft one case's data onto another. Drop those — docket still matches.
    return by_docket, _unambiguous(party_lists), _unambiguous(name_lists)


def _party_compatible(rec, lr):
    """False only when both sides name parties and they disagree."""
    rp, lp = _identity(rec)[1], _identity(lr)[1]
    return not (rp and lp and rp != lp)


def find_lag(rec, by_docket, by_party, by_name):
    docket, party = _identity(rec)
    if docket and docket in by_docket:
        lr = by_docket[docket]
        # a docket pulled from prose can be a cross-reference to another case;
        # trust it only when the parties don't contradict it.
        if _party_compatible(rec, lr):
            return lr
    if party and party in by_party:
        lr = by_party[party]
        if lag_merge._date_within(rec.get('date'), lr.get('date'),
                                  lag_merge._PARTY_DATE_WINDOW_DAYS):
            return lr  # generic party pair — require the dates to be close
    nk = _name_key(rec)
    if nk and nk in by_name:
        return by_name[nk]
    return None


def enrich(records, lag_recs):
    by_docket, by_party, by_name = build_lag_index(lag_recs)
    stats = {'judge_filled': 0, 'summary_updated': 0, 'pending_set': 0,
             'fields_filled': 0, 'cleared': 0, 'matched': 0}
    for rec in records:
        lr = find_lag(rec, by_docket, by_party, by_name)
        if not lr:
            # No safe LAG match: scrub any LAG-exclusive data a prior (looser)
            # run may have mis-attributed, so re-runs are self-correcting.
            for f in ('slug', 'ai_tool', 'last_verified'):
                if rec.get(f):
                    rec[f] = ''
                    stats['cleared'] += 1
            if rec.get('pending'):
                rec['pending'] = False
                stats['cleared'] += 1
            continue
        stats['matched'] += 1
        # judge: an R&G judge is authoritative (fill only if empty); a rails
        # judge is LAG-derived, so re-derive it from the (current) converter.
        is_rails = rec.get('source') == 'rails'
        if lr.get('judge') and ((is_rails and rec.get('judge') != lr['judge'])
                                or (not is_rails and not rec.get('judge'))):
            rec['judge'] = lr['judge']
            stats['judge_filled'] += 1
        if is_rails and lr.get('summary') and lr['summary'] != rec.get('summary'):
            rec['summary'] = lr['summary']
            stats['summary_updated'] += 1
        if bool(rec.get('pending')) != bool(lr.get('pending')):
            rec['pending'] = bool(lr.get('pending'))
            stats['pending_set'] += 1
        # slug/ai_tool/last_verified come only from LAG — set from source of truth
        for f in ('slug', 'ai_tool', 'last_verified'):
            if (rec.get(f) or '') != (lr.get(f) or ''):
                rec[f] = lr.get(f) or ''
                stats['fields_filled'] += 1
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
    print(f'judge filled: {stats["judge_filled"]}  summary updated: {stats["summary_updated"]}  '
          f'pending set: {stats["pending_set"]}  fields filled: {stats["fields_filled"]}  '
          f'stale cleared: {stats["cleared"]}')

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

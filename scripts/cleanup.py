#!/usr/bin/env python3
"""One-time cleanup of explorer_data.json.

Recovers original source links, normalizes the schema, validates and prunes
broken CourtListener links, then writes the canonical dataset and mirrors it to
charts/data/. Idempotent; refuses to write if the result fails validation.

Usage:
    python3 scripts/cleanup.py            # full run (live HTTP CL check)
    python3 scripts/cleanup.py --no-http  # skip CL link validation (offline)
    python3 scripts/cleanup.py --dry-run  # report only, write nothing
"""

import argparse
import json
import os

import dedup
import linkcheck
import linkrecover
import normalize
import schema

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, 'data', 'processed')
CHARTS_DATA_DIR = os.path.join(PROJECT_DIR, 'charts', 'data')
EXPLORER_PATH = os.path.join(DATA_DIR, 'explorer_data.json')
RG_SOURCE_PATH = os.path.join(PROJECT_DIR, 'data', 'sources', 'ropes_gray_court_orders.json')
CACHE_PATH = os.path.join(DATA_DIR, 'cl_link_cache.json')

OUTPUT_PATHS = [EXPLORER_PATH, os.path.join(CHARTS_DATA_DIR, 'explorer_data.json')]


def clean(records, results, do_http=True, fetch=linkcheck.default_fetch,
          cache=None, rate_limit=0.0):
    """Run the full cleanup over records. Returns (records, problems, stats)."""
    stats = {}
    records, stats['dedup'] = dedup.merge_duplicates(records)
    stats['recover'] = linkrecover.recover(records, results)
    normalize.normalize(records)
    if do_http:
        stats['linkcheck'] = linkcheck.validate_links(
            records, fetch=fetch, cache=cache, rate_limit=rate_limit)
    stats['verify'] = normalize.mark_unverified(records)
    problems = schema.validate_dataset(records)
    return records, problems, stats


def write_outputs(records, paths=OUTPUT_PATHS):
    payload = json.dumps(records, ensure_ascii=False, indent=2)
    for p in paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(payload)


def _load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding='utf-8') as f:
            return json.load(f)
    return {}


def _save_cache(cache):
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-http', action='store_true', help='skip CL link validation')
    ap.add_argument('--dry-run', action='store_true', help='report only, write nothing')
    args = ap.parse_args()

    with open(EXPLORER_PATH, encoding='utf-8') as f:
        records = json.load(f)
    with open(RG_SOURCE_PATH, encoding='utf-8') as f:
        results = json.load(f)['results']

    cache = {} if args.no_http else _load_cache()
    records, problems, stats = clean(
        records, results, do_http=not args.no_http, cache=cache, rate_limit=0.25)

    print('dedup:', stats['dedup'])
    print('recover:', stats['recover'])
    print('verify:', stats.get('verify'))
    if 'linkcheck' in stats:
        print('linkcheck:', stats['linkcheck'])

    if problems:
        print(f'ABORT: {len(problems)} validation problems; not writing.')
        for p in problems[:10]:
            print('  ', p)
        raise SystemExit(1)

    if not args.no_http:
        _save_cache(cache)

    if args.dry_run:
        print(f'DRY RUN: {len(records)} records valid; nothing written.')
        return

    write_outputs(records)
    print(f'Wrote {len(records)} records to:')
    for p in OUTPUT_PATHS:
        print('  ', p)


if __name__ == '__main__':
    main()

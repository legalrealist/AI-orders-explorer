#!/usr/bin/env python3
"""Audit archived PDFs for correctness.

Tier 2/3 PDFs carry the matched CourtListener `case_name` in the manifest. This
re-applies the same strict party-name check (offline, no API) and reports any
entry whose matched case doesn't agree with the record — there should be none,
since resolution enforces it, but this is the standing belt-and-suspenders check.

Usage: python3 scripts/audit_pdfs.py [--show N]
"""

import argparse
import json
import os

import cl_resolve

_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(os.path.dirname(_DIR), 'data', 'processed')


def audit(records, manifest):
    """Return (searched_entries, mismatches). A mismatch is a correctness bug."""
    by_pdf = {r.get('pdf'): r for r in records if r.get('pdf')}
    searched, mismatches = [], []
    for m in manifest:
        case = m.get('matched_case')
        if not case:
            continue  # tier-1 direct download (the record's own curated link)
        rec = by_pdf.get(m.get('pdf'))
        if rec is None:
            continue  # superseded by a later data refresh
        searched.append((rec.get('name', ''), case, m.get('pdf')))
        if not cl_resolve.case_matches(rec, case):
            mismatches.append((rec.get('name', ''), case, m.get('pdf')))
    return searched, mismatches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--show', type=int, default=10, help='sample N verified pairs')
    args = ap.parse_args()
    records = json.load(open(os.path.join(_DATA, 'explorer_data.json'), encoding='utf-8'))
    mpath = os.path.join(_DATA, 'pdf_manifest.json')
    manifest = json.load(open(mpath, encoding='utf-8')) if os.path.exists(mpath) else []

    with_pdf = sum(1 for r in records if r.get('pdf'))
    searched, mismatches = audit(records, manifest)
    print(f'records with pdf: {with_pdf}/{len(records)}')
    print(f'tier-1 (direct link): {with_pdf - len(searched)}')
    print(f'tier-2/3 (CL-resolved, verified): {len(searched)}')
    print(f'mismatches (correctness bugs): {len(mismatches)}')
    for name, case, pdf in mismatches:
        print(f'  MISMATCH: record={name!r}  matched={case!r}  {pdf}')
    print(f'\nsample verified record -> matched case (first {args.show}):')
    for name, case, _ in searched[:args.show]:
        print(f'  {name[:45]:45}  ->  {case[:45]}')


if __name__ == '__main__':
    main()

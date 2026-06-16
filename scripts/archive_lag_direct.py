#!/usr/bin/env python3
"""Tier-LAG: download primary-source PDFs directly from LegalAIGovernance.

LAG's cases.json links the actual document (primary_source_urls / source_urls —
mostly S3, damiencharlotin.com, govinfo, court-site, and CourtListener *storage*
PDFs). Match each record without a PDF to its LAG case by case name, else by
party pair within a date window, then download the source document directly —
no CourtListener API, no rate limit. download_pdf validates %PDF magic, so HTML
landing/challenge pages are rejected. The matched LAG case name is logged for
the audit trail.

Usage: python3 scripts/archive_lag_direct.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cl_resolve
import lag_cases
import lag_merge
import normalize
import pdf_archive
import schema

OUT = '/Users/hao/legalhack/public_html/orders'
DATA = 'data/processed/explorer_data.json'
MIRROR = 'charts/data/explorer_data.json'
MANIFEST = 'data/processed/pdf_manifest.json'
DATE_WINDOW_DAYS = 180


def build_indexes(cases):
    by_name, by_party = {}, {}
    for c in cases:
        name = c.get('case_name', '')
        if name:
            by_name.setdefault(name, c)
        p = lag_merge.extract_parties(name)
        if p:
            by_party.setdefault(p, []).append(c)
    return by_name, by_party


def match_lag_case(record, by_name, by_party):
    """Find the LAG case for a record and VERIFY it.

    A candidate is accepted only when cl_resolve.case_matches confirms every
    distinctive party of the record's own case appears in the LAG case name —
    the same strict guard the CL resolver uses. This rejects party matches where
    the record's summary actually cites a different case than its holding.
    """
    c = by_name.get(record.get('name', ''))
    if c and cl_resolve.case_matches(record, c.get('case_name', '')):
        return c
    p = lag_merge.extract_parties(cl_resolve.search_query(record))
    if not p:
        return None
    for cand in by_party.get(p, []):
        if (lag_merge._date_within(record.get('date'), cand.get('date'), DATE_WINDOW_DAYS)
                and cl_resolve.case_matches(record, cand.get('case_name', ''))):
            return cand
    return None


def candidate_urls(case):
    return (case.get('primary_source_urls') or []) + (case.get('source_urls') or [])


def main():
    exp = json.load(open(DATA))
    normalize.normalize(exp)
    env = lag_cases.load_cached() or lag_cases.fetch_cases()
    by_name, by_party = build_indexes(lag_cases.items(env))
    manifest = {m['key']: m for m in (json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else [])}

    matched = downloaded = 0
    for rec in exp:
        if rec.get('pdf'):
            continue
        case = match_lag_case(rec, by_name, by_party)
        if not case:
            continue
        matched += 1
        for src in candidate_urls(case):
            key = pdf_archive.stable_key(rec, src)
            dest = os.path.join(OUT, key + '.pdf')
            if os.path.exists(dest):
                rec['pdf'] = pdf_archive.BASE_URL + key + '.pdf'
                downloaded += 1
                break
            ok, sha1, n, err = pdf_archive.download_pdf(src, dest)
            if ok:
                rec['pdf'] = pdf_archive.BASE_URL + key + '.pdf'
                manifest[key] = {'key': key, 'name': rec.get('name', '')[:60],
                                 'matched_case': case.get('case_name', ''),
                                 'source_url': src, 'pdf': rec['pdf'],
                                 'sha1': sha1, 'bytes': n}
                downloaded += 1
                break

    problems = schema.validate_dataset(exp)
    if problems:
        print('VALIDATION PROBLEMS, not writing:', problems[:3])
        sys.exit(1)
    payload = json.dumps(exp, ensure_ascii=False, indent=2)
    open(DATA, 'w', encoding='utf-8').write(payload)
    open(MIRROR, 'w', encoding='utf-8').write(payload)
    json.dump(list(manifest.values()), open(MANIFEST, 'w'), indent=2)
    cov = sum(1 for r in exp if r.get('pdf'))
    print(f'LAG-direct: matched {matched} records, downloaded {downloaded}; '
          f'pdf coverage now {cov}/{len(exp)}')


if __name__ == '__main__':
    main()

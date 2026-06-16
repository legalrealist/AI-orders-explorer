#!/usr/bin/env python3
"""Tail pass A: download the order PDF straight from the record's own link.

Tier-1 only recognized URLs ending in `.pdf` (or CourtListener storage), so it
missed court documents served behind a query string (S3 `?VersionId=`) or a
file endpoint (`/JpsApi/file/<uuid>`). This pass tries each record's own
link / original_link and keeps it when the bytes are actually a PDF (%PDF magic
in download_pdf). Paywalled hosts (Lexis/Westlaw/Bloomberg) and aggregator pages
(R&G tracker, LAG) are skipped — they never serve the order PDF.

Usage: python3 scripts/archive_tail.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import normalize
import pdf_archive
import schema

OUT = '/Users/hao/legalhack/public_html/orders'
DATA = 'data/processed/explorer_data.json'
MIRROR = 'charts/data/explorer_data.json'
MANIFEST = 'data/processed/pdf_manifest.json'

# Hosts that never serve the order document itself.
_SKIP = ('lexis.com', 'westlaw.com', 'bloomberglaw.com', 'ropesgray.com',
         'legalaigovernance.com')


def candidate_urls(record):
    urls = []
    for u in (record.get('original_link', ''), record.get('link', '')):
        if u and u not in urls and not any(s in u.lower() for s in _SKIP):
            urls.append(u)
    return urls


def main():
    exp = json.load(open(DATA))
    normalize.normalize(exp)
    manifest = {m['key']: m for m in (json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else [])}

    tried = downloaded = 0
    for rec in exp:
        if rec.get('pdf'):
            continue
        urls = candidate_urls(rec)
        if not urls:
            continue
        tried += 1
        for src in urls:
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
    print(f'tail-A: tried {tried} records, downloaded {downloaded} real PDFs; '
          f'pdf coverage now {cov}/{len(exp)}')


if __name__ == '__main__':
    main()

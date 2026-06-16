#!/usr/bin/env python3
"""Tail pass B: render court pages to dated PDF captures (headless Chrome).

For hard-tail records (no resolvable case name, no CL link) whose link is a
genuine court / Justia / govinfo page — not a paywalled or aggregator page —
render the live page to a PDF with headless Chrome and self-host it. These are
labeled `kind: capture` in the manifest with the source URL and capture date:
faithful captures of the court's published page, explicitly NOT official
document PDFs. A size floor rejects blank / error / challenge renders.

Usage: python3 scripts/archive_capture.py
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cl_resolve
import normalize
import pdf_archive
import schema

OUT = '/Users/hao/legalhack/public_html/orders'
DATA = 'data/processed/explorer_data.json'
MIRROR = 'charts/data/explorer_data.json'
MANIFEST = 'data/processed/pdf_manifest.json'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

# Pages that are not the order itself, or that can't be rendered.
_SKIP = ('ropesgray.com', 'legalaigovernance.com', 'lexis.com', 'westlaw.com',
         'bloomberglaw.com', 'drive.google.com')
MIN_BYTES = 8000  # reject blank / error / challenge renders


def _is_cl(record):
    l = (record.get('link', '') + record.get('original_link', '')).lower()
    return 'courtlistener.com/docket' in l or 'courtlistener.com/opinion' in l


def renderable_url(record):
    """The court-page URL to capture, or '' when this record isn't a capture target."""
    if record.get('pdf'):
        return ''
    if cl_resolve.search_query(record):
        return ''  # has a case name -> the CL crawl owns it
    if _is_cl(record):
        return ''
    u = record.get('link', '') or record.get('original_link', '')
    if not u or any(s in u.lower() for s in _SKIP):
        return ''
    return u


def render(url, dest, profile):
    """Render url to a PDF at dest with headless Chrome. Returns True on a real PDF."""
    try:
        subprocess.run(
            [CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
             f'--user-data-dir={profile}', '--virtual-time-budget=15000',
             '--run-all-compositor-stages-before-draw',
             f'--print-to-pdf={dest}', url],
            timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    if os.path.exists(dest):
        with open(dest, 'rb') as f:
            head = f.read(4)
        if head == b'%PDF' and os.path.getsize(dest) >= MIN_BYTES \
                and not pdf_archive.is_challenge_pdf(dest):
            return True
        os.remove(dest)
    return False


def main():
    exp = json.load(open(DATA))
    normalize.normalize(exp)
    manifest = {m['key']: m for m in (json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else [])}
    today = datetime.date.today().isoformat()
    profile = tempfile.mkdtemp(prefix='pp-chrome-')

    captured = attempted = 0
    try:
        for rec in exp:
            u = renderable_url(rec)
            if not u:
                continue
            attempted += 1
            key = pdf_archive.stable_key(rec, u)
            dest = os.path.join(OUT, key + '.pdf')
            if os.path.exists(dest):
                rec['pdf'] = pdf_archive.BASE_URL + key + '.pdf'
                captured += 1
                continue
            if render(u, dest, profile):
                rec['pdf'] = pdf_archive.BASE_URL + key + '.pdf'
                manifest[key] = {'key': key, 'name': rec.get('name', '')[:60],
                                 'kind': 'capture', 'source_url': u, 'captured': today,
                                 'pdf': rec['pdf'], 'bytes': os.path.getsize(dest)}
                captured += 1
                print(f'  captured: {rec.get("name", "")[:50]}', flush=True)
    finally:
        shutil.rmtree(profile, ignore_errors=True)

    problems = schema.validate_dataset(exp)
    if problems:
        print('VALIDATION PROBLEMS, not writing:', problems[:3])
        sys.exit(1)
    payload = json.dumps(exp, ensure_ascii=False, indent=2)
    open(DATA, 'w', encoding='utf-8').write(payload)
    open(MIRROR, 'w', encoding='utf-8').write(payload)
    json.dump(list(manifest.values()), open(MANIFEST, 'w'), indent=2)
    cov = sum(1 for r in exp if r.get('pdf'))
    print(f'capture: attempted {attempted}, rendered {captured} dated captures; '
          f'pdf coverage now {cov}/{len(exp)}')


if __name__ == '__main__':
    main()

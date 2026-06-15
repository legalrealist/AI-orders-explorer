#!/usr/bin/env python3
"""Tier 2/3 PDF archiving via the CourtListener API (throttled + resumable).

For every record without a `pdf`, resolve a CL-hosted PDF (own docket/opinion
link, or re-find by case name) and download it under a stable key. Respects the
rate-limited key: spaces calls, backs off on 429, caches every resolution so a
re-run resumes instead of re-calling.

Run:  CL_API_KEY=... python3 scripts/archive_tier23.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cl_resolve
import lag_merge  # noqa: F401  (pulled in by cl_resolve)
import linkcheck
import normalize
import pdf_archive
import schema

KEY = os.environ.get('CL_API_KEY', '')
OUT = '/Users/hao/legalhack/public_html/orders'
DATA = 'data/processed/explorer_data.json'
MIRROR = 'charts/data/explorer_data.json'
MANIFEST = 'data/processed/pdf_manifest.json'
CACHE = 'data/processed/cl_resolve_cache.json'

# Seconds between API calls. Default is conservative for the free tier; lower it
# (e.g. CL_RATE_DELAY=0.3) once on a paid CourtListener tier with a higher limit.
BASE_DELAY = float(os.environ.get('CL_RATE_DELAY', '1.3'))
_last = [0.0]


def throttle():
    dt = time.time() - _last[0]
    if dt < BASE_DELAY:
        time.sleep(BASE_DELAY - dt)
    _last[0] = time.time()


def fetch(path):
    """GET a CL API path as JSON, throttled, with 429 backoff."""
    for attempt in range(5):
        throttle()
        req = urllib.request.Request('https://www.courtlistener.com' + path,
                                     headers={'Authorization': f'Token {KEY}',
                                              'User-Agent': linkcheck._USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30, context=linkcheck.SSL_CTX) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get('Retry-After', 0) or 0) or (5 * (attempt + 1))
                print(f'  429 — sleeping {wait}s', flush=True)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError('rate-limited after retries')


def load(p, default):
    return json.load(open(p)) if os.path.exists(p) else default


def main():
    if not KEY:
        print('CL_API_KEY not set'); sys.exit(1)
    exp = json.load(open(DATA))
    normalize.normalize(exp)
    cache = load(CACHE, {})
    manifest = {m['key']: m for m in load(MANIFEST, [])}

    import re as _re

    def resolvable(r):
        src = (r.get('link', '') + r.get('original_link', '')).lower()
        if 'courtlistener.com/docket' in src or 'courtlistener.com/opinion' in src:
            return True
        return bool(cl_resolve.search_query(r))  # case name in name or summary

    todo = [r for r in exp if not r.get('pdf') and resolvable(r)]
    print(f'tier2/3: {len(todo)} records to resolve (of {len(exp)})', flush=True)

    done = 0
    for i, rec in enumerate(todo):
        if rec.get('pdf'):
            continue
        ckey = pdf_archive.stable_key(rec, rec.get('link', ''))
        if ckey in cache:
            url = cache[ckey]
        else:
            try:
                url, method = cl_resolve.resolve_pdf_url(rec, fetch)
            except Exception as e:
                print(f'  [{i}] resolve error: {e}', flush=True)
                url = ''
            cache[ckey] = url
            if len(cache) % 10 == 0:
                json.dump(cache, open(CACHE, 'w'))

        if not url:
            continue
        key = pdf_archive.stable_key(rec, url)
        dest = os.path.join(OUT, key + '.pdf')
        if os.path.exists(dest):
            rec['pdf'] = pdf_archive.BASE_URL + key + '.pdf'
            done += 1
            continue
        throttle()
        ok, sha1, n, err = pdf_archive.download_pdf(url, dest)
        if ok:
            rec['pdf'] = pdf_archive.BASE_URL + key + '.pdf'
            manifest[key] = {'key': key, 'name': rec.get('name', '')[:60],
                             'source_url': url, 'pdf': rec['pdf'], 'sha1': sha1, 'bytes': n}
            done += 1
            if done % 20 == 0:
                _write(exp, manifest, cache)
                print(f'  progress: +{done} resolved/downloaded', flush=True)
        else:
            print(f'  [{i}] download fail: {err}', flush=True)

    _write(exp, manifest, cache)
    withpdf = sum(1 for r in exp if r.get('pdf'))
    print(f'DONE: +{done} this run | total pdf coverage {withpdf}/{len(exp)}', flush=True)


def _write(exp, manifest, cache):
    problems = schema.validate_dataset(exp)
    if problems:
        print('VALIDATION PROBLEMS, not writing:', problems[:3], flush=True)
        return
    payload = json.dumps(exp, ensure_ascii=False, indent=2)
    open(DATA, 'w', encoding='utf-8').write(payload)
    open(MIRROR, 'w', encoding='utf-8').write(payload)
    json.dump(list(manifest.values()), open(MANIFEST, 'w'), indent=2)
    json.dump(cache, open(CACHE, 'w'))


if __name__ == '__main__':
    main()

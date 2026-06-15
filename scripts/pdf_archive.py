"""Archive primary-document PDFs locally so the explorer can self-host them.

Tier 1: records whose `link` / `original_link` / LAG `source_urls` is already a
directly-downloadable PDF (a `.pdf` URL or a CourtListener storage doc). Each is
downloaded under a STABLE filename (not the explorer's `id`, which re-indexes on
every merge), the record's `pdf` field is set to the public URL, and a manifest
row is recorded. Idempotent: an already-downloaded file is reused.

The fetcher is injectable so tests never touch the network.
"""

import hashlib
import os
import re
import urllib.request

import lag_cases
import linkcheck

BASE_URL = 'https://legalhack.io/orders/'


def stable_key(record, src=''):
    """A filename stem that survives id re-indexing and data merges.

    R&G records key off their unique `_rg_id`; others hash court+date+name plus
    the source document URL, so two distinct documents never collide.
    """
    rgid = record.get('_rg_id')
    if rgid:
        return 'rg-' + re.sub(r'[^a-z0-9]', '', rgid.lower())[:12]
    basis = '|'.join([
        (record.get('court', '') or ''),
        (record.get('date', '') or ''),
        (record.get('name', '') or ''),
        (src or ''),
    ]).lower()
    return 'c-' + hashlib.sha1(basis.encode('utf-8')).hexdigest()[:12]


def is_direct_pdf(url):
    u = (url or '').lower()
    return u.endswith('.pdf') or 'storage.courtlistener.com' in u


def direct_pdf_url(record, lag_index=None):
    """Return a directly-downloadable PDF URL for this record, or ''."""
    for u in (record.get('original_link', ''), record.get('link', '')):
        if is_direct_pdf(u):
            return u
    if lag_index is not None:
        case = lag_index.get(record.get('name', ''))
        if case:
            for u in (case.get('primary_source_urls') or []) + (case.get('source_urls') or []):
                if is_direct_pdf(u):
                    return u
    return ''


def default_fetch(url, timeout=30):
    """Return raw response bytes (follows redirects). Raises on failure."""
    req = urllib.request.Request(url, headers={'User-Agent': linkcheck._USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=linkcheck.SSL_CTX) as resp:
        return resp.read()


def download_pdf(url, dest, fetch=default_fetch):
    """Download url to dest if it is a real PDF. Returns (ok, sha1, nbytes, err)."""
    try:
        data = fetch(url)
    except Exception as e:
        return False, '', 0, f'{type(e).__name__}: {e}'
    if not data[:5].startswith(b'%PDF'):
        return False, '', 0, 'not a PDF (bad magic)'
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'wb') as f:
        f.write(data)
    return True, hashlib.sha1(data).hexdigest(), len(data), ''


def lag_index_from(env):
    return {c.get('case_name', ''): c for c in lag_cases.items(env)}


def archive(records, out_dir, lag_index=None, fetch=default_fetch,
            base_url=BASE_URL, limit=None):
    """Download tier-1 PDFs, set record['pdf'], build manifest. Returns (stats, manifest)."""
    stats = {'candidates': 0, 'downloaded': 0, 'reused': 0, 'failed': 0, 'skipped_no_pdf': 0}
    manifest = []
    n = 0
    for rec in records:
        src = direct_pdf_url(rec, lag_index)
        if not src:
            stats['skipped_no_pdf'] += 1
            continue
        stats['candidates'] += 1
        if limit is not None and n >= limit:
            continue
        key = stable_key(rec, src)
        fname = key + '.pdf'
        dest = os.path.join(out_dir, fname)

        if os.path.exists(dest):
            stats['reused'] += 1
            sha1, nbytes = '', os.path.getsize(dest)
        else:
            ok, sha1, nbytes, err = download_pdf(src, dest, fetch)
            n += 1
            if not ok:
                stats['failed'] += 1
                manifest.append({'key': key, 'name': rec.get('name', ''),
                                 'source_url': src, 'pdf': '', 'error': err})
                continue
            stats['downloaded'] += 1

        rec['pdf'] = base_url + fname
        manifest.append({'key': key, 'name': rec.get('name', ''),
                         'source_url': src, 'pdf': rec['pdf'],
                         'sha1': sha1, 'bytes': nbytes})
    return stats, manifest

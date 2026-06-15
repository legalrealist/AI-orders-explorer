"""Resolve a record to a CourtListener-hosted PDF (tiers 2 & 3).

Tier 2: a record's own CL docket/opinion link -> the opinion's stored PDF.
Tier 3: re-find a Justia/Lexis/Westlaw case on CL by name -> its stored PDF.

Resolution chain (CL has no single "docket PDF"):
    opinion id            -> opinion.local_path
    docket id  -> cluster -> sub_opinion -> opinion.local_path
    search(name) (verified by case_name) -> cluster -> opinion.local_path

All network goes through an injected `fetch(path) -> dict` (raises HTTPError),
so the resolver itself is unit-testable offline. case_name verification reuses
distinctive-token overlap to reject wrong-case search hits (hallucination guard).
"""

import re
import urllib.parse

import lag_merge

STORAGE = 'https://storage.courtlistener.com/'


def _toks(text):
    return {t for t in re.findall(r'[a-z]{4,}', (text or '').lower())} - lag_merge._NOT_SURNAME


def storage_url(local_path):
    return STORAGE + local_path.lstrip('/') if local_path else ''


def _id_from(url):
    return (url or '').rstrip('/').split('/')[-1]


def name_matches(record, case_name):
    return bool(_toks(case_name) & _toks(record.get('name', '') + ' ' + record.get('summary', '')))


def _opinion_pdf(opinion_id, fetch):
    o = fetch(f'/api/rest/v4/opinions/{opinion_id}/')
    return storage_url(o.get('local_path'))


def _cluster_pdf(cluster_url, fetch):
    cid = _id_from(cluster_url)
    c = fetch(f'/api/rest/v4/clusters/{cid}/')
    for sub in c.get('sub_opinions', []) or []:
        url = _opinion_pdf(_id_from(sub), fetch)
        if url:
            return url
    return ''


def _docket_pdf(docket_id, fetch):
    d = fetch(f'/api/rest/v4/dockets/{docket_id}/')
    for cl in d.get('clusters', []) or []:
        url = _cluster_pdf(cl, fetch)
        if url:
            return url
    return ''


def _search_pdf(record, fetch):
    q = record.get('name', '')
    if not q:
        return ''
    d = fetch('/api/rest/v4/search/?type=o&q=' + urllib.parse.quote(q))
    for res in (d.get('results') or [])[:3]:
        if not name_matches(record, res.get('caseName', '')):
            continue
        cid = res.get('cluster_id')
        if cid:
            url = _cluster_pdf(f'/api/rest/v4/clusters/{cid}/', fetch)
            if url:
                return url
    return ''


def resolve_pdf_url(record, fetch, allow_search=True):
    """Return (storage_pdf_url, method) or ('', '')."""
    link = record.get('link', '') or ''
    orig = record.get('original_link', '') or ''

    for src in (link, orig):
        m = re.search(r'/opinion/(\d+)/', src)
        if m:
            try:
                url = _opinion_pdf(m.group(1), fetch)
                if url:
                    return url, 'opinion'
            except Exception:
                pass
        m = re.search(r'/docket/(\d+)/', src)
        if m:
            try:
                url = _docket_pdf(m.group(1), fetch)
                if url:
                    return url, 'docket'
            except Exception:
                pass

    if allow_search:
        try:
            url = _search_pdf(record, fetch)
            if url:
                return url, 'search'
        except Exception:
            pass
    return '', ''

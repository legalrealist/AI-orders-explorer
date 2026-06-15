"""Resolve a record to the CORRECT CourtListener-hosted PDF (tiers 2 & 3).

Tier 2: a record's own CL docket/opinion link -> the opinion's stored PDF.
Tier 3: re-find a Justia/Lexis/Westlaw case on CL by name -> its stored PDF.

Correctness is the priority. Every candidate PDF is verified against the
record's own case identity before it is accepted: `case_matches` requires every
distinctive party name of our case to appear in the CL case_name. This rejects:
  - hallucinated / wrong-case docket or opinion links the record may carry, and
  - wrong-case hits from the name search.
A rejected docket/opinion link falls through to a verified search. The matched
CL case_name is returned so the runner can log an audit trail.

All network goes through an injected `fetch(path) -> dict` (raises HTTPError),
so the resolver is unit-testable offline.
"""

import re
import urllib.parse

import lag_merge

STORAGE = 'https://storage.courtlistener.com/'

_CASE_RE = re.compile(r"\b([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){0,3}\s+v\.?\s+[A-Z][\w.'-]+)")


def _toks(text):
    return {t for t in re.findall(r'[a-z]{4,}', (text or '').lower())} - lag_merge._NOT_SURNAME


def storage_url(local_path):
    return STORAGE + local_path.lstrip('/') if local_path else ''


def _id_from(url):
    return (url or '').rstrip('/').split('/')[-1]


def search_query(record):
    """Best case-name query: the record name if it's a case, else from summary."""
    name = record.get('name', '') or ''
    if ' v' in name.lower() and _CASE_RE.search(name):
        return name
    m = _CASE_RE.search(record.get('summary', '') or '')
    if not m:
        return ''
    return re.sub(r'^(In|Matter of)\s+', '', m.group(1))


def case_matches(record, case_name):
    """Strict: every distinctive party token of our case appears in CL's case_name.

    "Shore v. Dorel" matches "Shore v. Dorel Juvenile Group" (both parties
    present) but NOT "Shore v. Smith" (only one party) — so a wrong-case hit that
    merely shares a surname is rejected.
    """
    qt = _toks(search_query(record))
    return bool(qt) and qt <= _toks(case_name)


def _opinion_local_path(opinion_id, fetch):
    o = fetch(f'/api/rest/v4/opinions/{opinion_id}/')
    return storage_url(o.get('local_path')), o.get('cluster', '')


def _cluster(cluster_url, fetch):
    return fetch(f'/api/rest/v4/clusters/{_id_from(cluster_url)}/')


def _cluster_pdf(cluster_url, fetch):
    c = _cluster(cluster_url, fetch)
    cname = c.get('case_name', '')
    for sub in c.get('sub_opinions', []) or []:
        url, _ = _opinion_local_path(_id_from(sub), fetch)
        if url:
            return url, cname
    return '', cname


def _docket_pdf(docket_id, fetch):
    d = fetch(f'/api/rest/v4/dockets/{docket_id}/')
    cname = d.get('case_name', '')
    for cl in d.get('clusters', []) or []:
        url, _ = _cluster_pdf(cl, fetch)
        if url:
            return url, cname
    return '', cname


def _opinion_pdf_via_link(opinion_id, fetch):
    url, cluster_url = _opinion_local_path(opinion_id, fetch)
    if not url:
        return '', ''
    cname = _cluster(cluster_url, fetch).get('case_name', '') if cluster_url else ''
    return url, cname


def _search_pdf(record, fetch):
    q = search_query(record)
    if not q:
        return '', ''
    d = fetch('/api/rest/v4/search/?type=o&q=' + urllib.parse.quote(q))
    for res in (d.get('results') or [])[:5]:
        cn = res.get('caseName', '')
        if not case_matches(record, cn):
            continue
        cid = res.get('cluster_id')
        if cid:
            url, _ = _cluster_pdf(f'/api/rest/v4/clusters/{cid}/', fetch)
            if url:
                return url, cn
    return '', ''


def resolve_pdf_url(record, fetch, allow_search=True):
    """Return (storage_pdf_url, method, matched_case_name) or ('', '', '').

    Docket/opinion links are accepted only when the resolved case_name passes
    case_matches against the record; otherwise resolution falls through to a
    verified name search.
    """
    link = record.get('link', '') or ''
    orig = record.get('original_link', '') or ''

    for src in (link, orig):
        m = re.search(r'/opinion/(\d+)/', src)
        if m:
            try:
                url, cname = _opinion_pdf_via_link(m.group(1), fetch)
                if url and case_matches(record, cname):
                    return url, 'opinion', cname
            except Exception:
                pass
        m = re.search(r'/docket/(\d+)/', src)
        if m:
            try:
                url, cname = _docket_pdf(m.group(1), fetch)
                if url and case_matches(record, cname):
                    return url, 'docket', cname
            except Exception:
                pass

    if allow_search:
        try:
            url, cname = _search_pdf(record, fetch)
            if url:
                return url, 'search', cname
        except Exception:
            pass
    return '', '', ''

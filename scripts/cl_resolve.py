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


def _date_close(record_date, cl_date, days=31):
    """True if the CL decision date matches the record's date (same document).

    Allows a window for tracker-vs-court date drift; month-precision record
    dates match on year-month. Missing dates can't disprove a match -> allow,
    so case-name verification still governs.
    """
    rd, cd = (record_date or '')[:10], (cl_date or '')[:10]
    if not rd or not cd:
        return True
    if len(rd) == 7:  # YYYY-MM precision
        return cd[:7] == rd
    try:
        from datetime import date
        a = date(*map(int, rd.split('-')))
        b = date(*map(int, cd.split('-')))
    except (ValueError, TypeError):
        return True
    return abs((a - b).days) <= days


def _opinion_local_path(opinion_id, fetch):
    o = fetch(f'/api/rest/v4/opinions/{opinion_id}/')
    return storage_url(o.get('local_path')), o.get('cluster', '')


def _cluster(cluster_url, fetch):
    return fetch(f'/api/rest/v4/clusters/{_id_from(cluster_url)}/')


def _cluster_pdf(cluster_url, fetch, record):
    """Return (pdf_url, case_name) only if the cluster matches the record's
    case name AND decision date — i.e. it is the same document."""
    c = _cluster(cluster_url, fetch)
    cname = c.get('case_name', '')
    if not case_matches(record, cname):
        return '', cname
    if not _date_close(record.get('date'), c.get('date_filed')):
        return '', cname  # right case, wrong ruling in it
    for sub in c.get('sub_opinions', []) or []:
        url, _ = _opinion_local_path(_id_from(sub), fetch)
        if url:
            return url, cname
    return '', cname


def _docket_pdf(docket_id, fetch, record):
    d = fetch(f'/api/rest/v4/dockets/{docket_id}/')
    for cl in d.get('clusters', []) or []:
        url, cname = _cluster_pdf(cl, fetch, record)
        if url:
            return url, cname
    return '', d.get('case_name', '')


def _opinion_pdf_via_link(opinion_id, fetch, record):
    url, cluster_url = _opinion_local_path(opinion_id, fetch)
    if not url or not cluster_url:
        return '', ''
    c = _cluster(cluster_url, fetch)
    cname = c.get('case_name', '')
    if not case_matches(record, cname):
        return '', cname
    if not _date_close(record.get('date'), c.get('date_filed')):
        return '', cname
    return url, cname


def _search_pdf(record, fetch):
    q = search_query(record)
    if not q:
        return '', ''
    d = fetch('/api/rest/v4/search/?type=o&q=' + urllib.parse.quote(q))
    for res in (d.get('results') or [])[:5]:
        cid = res.get('cluster_id')
        if cid:
            url, cname = _cluster_pdf(f'/api/rest/v4/clusters/{cid}/', fetch, record)
            if url:
                return url, cname
    return '', ''


def resolve_pdf_url(record, fetch, allow_search=True):
    """Return (storage_pdf_url, method, matched_case_name) or ('', '', '').

    A candidate is accepted only when the CL cluster matches the record's case
    name AND decision date (same document) — verified inside _cluster_pdf /
    _opinion_pdf_via_link. A record's own docket/opinion link that fails either
    check falls through to a verified name search.
    """
    link = record.get('link', '') or ''
    orig = record.get('original_link', '') or ''

    for src in (link, orig):
        m = re.search(r'/opinion/(\d+)/', src)
        if m:
            try:
                url, cname = _opinion_pdf_via_link(m.group(1), fetch, record)
                if url:
                    return url, 'opinion', cname
            except Exception:
                pass
        m = re.search(r'/docket/(\d+)/', src)
        if m:
            try:
                url, cname = _docket_pdf(m.group(1), fetch, record)
                if url:
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

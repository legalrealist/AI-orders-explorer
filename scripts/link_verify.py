"""Verify CourtListener links and repair hallucinated / dead ones.

CourtListener and Justia block scraping (202 challenge / 403), so HTML checks
are useless. Instead this verifies CL links offline first — the case slug in the
URL (or storage-PDF filename) is matched against the record's own citation text —
and only the handful that don't match are confirmed via the rate-limited CL REST
API (case_name comparison catches wrong-case "hallucinations", not just dead
links). A bad link falls back to the record's lexis/westlaw original_link, or is
blanked and reported when no authoritative fallback exists.

Pure/offline except the optional injected `api_fetch`.
"""

import re
import json
import urllib.error
import urllib.request

import lag_merge
import linkcheck
import linkrecover

_STOP = lag_merge._NOT_SURNAME | {
    'inc', 'llc', 'corp', 'co', 'na', 'the', 'of', 'and', 'et', 'al', 'ica',
    'opinion', 'filed', 'jr', 'sr', 'iii', 'minors', 'order', 'parties',
}


def _toks(text, minlen=3):
    return {t for t in re.findall(r'[a-z]{%d,}' % minlen, (text or '').lower())} - _STOP


def cl_case_slug(url):
    """Case slug from a CL docket/opinion URL or a storage-PDF filename."""
    m = re.search(r'/(?:docket|opinion)/\d+/([a-z0-9-]+)', url or '')
    if m:
        return m.group(1).replace('-', ' ')
    m = re.search(r'storage\.courtlistener\.com/pdf/[\d/]+/(.+?)\.pdf', url or '')
    if m:
        return m.group(1).replace('_', ' ')
    return None


def cl_kind(url):
    url = url or ''
    if 'storage.courtlistener.com/recap/' in url:
        return 'recap'      # direct court filing PDF — trustworthy
    if 'storage.courtlistener.com/pdf/' in url:
        return 'pdf'        # opinion PDF — filename is slug-checkable
    if re.search(r'/(?:docket|opinion)/\d+/[a-z0-9-]+', url):
        return 'slugged'
    if '?q=' in url:
        return 'search'     # bare search page — no direct hit
    return 'other'


def extract_id(url):
    """Return (type, id) for a CL docket/opinion URL, else (None, None)."""
    m = re.search(r'/(docket|opinion)/(\d+)/', url or '')
    return (m.group(1), m.group(2)) if m else (None, None)


def _record_text(record):
    return record.get('name', '') + ' ' + record.get('summary', '')


def slug_matches_record(url, record):
    slug = cl_case_slug(url)
    if slug is None:
        return None
    return bool(_toks(slug) & _toks(_record_text(record)))


def offline_classify(record):
    """trust | suspicious | search | review (questionable) for a CL link."""
    url = record.get('link', '')
    kind = cl_kind(url)
    if kind == 'recap':
        return 'trust'
    if kind in ('slugged', 'pdf'):
        return 'trust' if slug_matches_record(url, record) else 'suspicious'
    if kind == 'search':
        return 'search'
    return 'review'


def default_api_fetch(api_key):
    """Build an api_fetch(type, id) -> dict using the CL REST API + key."""
    def fetch(type_, id_):
        url = f'https://www.courtlistener.com/api/rest/v4/{type_}s/{id_}/'
        req = urllib.request.Request(url, headers={
            'Authorization': f'Token {api_key}',
            'User-Agent': linkcheck._USER_AGENT,
        })
        with urllib.request.urlopen(req, timeout=20, context=linkcheck.SSL_CTX) as r:
            return json.loads(r.read().decode())
    return fetch


def api_confirms(record, data):
    name = (data or {}).get('case_name') or (data or {}).get('caseName') or ''
    return bool(_toks(name) & _toks(_record_text(record)))


def _apply_fallback(record):
    """Fall back to lexis/westlaw original_link, else blank. Returns action."""
    orig = record.get('original_link', '') or ''
    osrc = linkrecover.classify_link_source(orig)
    if osrc in ('lexis', 'westlaw'):
        record['link'] = orig
        record['link_source'] = osrc
        return 'fallback_' + osrc
    record['link'] = ''
    record['link_source'] = 'none'
    return 'blanked'


def resolve(records, api_fetch=None):
    """Verify CL links; repair bad ones. Returns (stats, report).

    report: list of {id, name, old_link, action, status}.
    """
    stats = {'trust': 0, 'suspicious': 0, 'search': 0, 'review': 0,
             'api_confirmed': 0, 'api_rejected': 0, 'api_error': 0,
             'fallback_lexis': 0, 'fallback_westlaw': 0, 'blanked': 0}
    report = []

    for rec in records:
        if rec.get('link_source') != 'courtlistener':
            continue
        status = offline_classify(rec)
        stats[status] += 1
        if status == 'trust':
            continue

        old = rec.get('link', '')

        # Suspicious slug: the API can definitively confirm/deny via case_name.
        if status == 'suspicious' and api_fetch:
            type_, id_ = extract_id(old)
            if id_:
                try:
                    data = api_fetch(type_, id_)
                    if api_confirms(rec, data):
                        stats['api_confirmed'] += 1
                        continue  # false alarm — keep the link
                    stats['api_rejected'] += 1
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        stats['api_rejected'] += 1   # docket gone -> repair
                    else:
                        stats['api_error'] += 1
                        report.append({'id': rec.get('id'), 'name': rec.get('name', ''),
                                       'old_link': old, 'action': 'unverified_kept',
                                       'status': status})
                        continue
                except Exception:
                    stats['api_error'] += 1
                    report.append({'id': rec.get('id'), 'name': rec.get('name', ''),
                                   'old_link': old, 'action': 'unverified_kept',
                                   'status': status})
                    continue

        action = _apply_fallback(rec)
        stats[action] = stats.get(action, 0) + 1
        report.append({'id': rec.get('id'), 'name': rec.get('name', ''),
                       'old_link': old, 'action': action, 'status': status})

    return stats, report

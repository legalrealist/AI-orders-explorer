"""Recover original source links and classify link provenance.

The pipeline historically overwrote each record's single `link` field with a
CourtListener URL, destroying the original Ropes & Gray (Lexis) permalink. This
module recovers that original from the raw R&G source and records where the
current `link` points, without ever touching `link` itself.

Pure functions over inputs — no network.
"""

import re
from urllib.parse import urlparse

import schema


def classify_link_source(url):
    """Map a URL to a schema.LINK_SOURCES value."""
    if not url:
        return 'none'
    host = (urlparse(url).netloc or '').lower()
    if 'courtlistener.com' in host:
        return 'courtlistener'
    if 'lexis.com' in host:
        return 'lexis'
    if 'westlaw.com' in host:
        return 'westlaw'
    if 'justia.com' in host:
        return 'justia'
    if 'govinfo.gov' in host:
        return 'govinfo'
    if 'ropesgray.com' in host:
        return 'ropesgray'
    return 'other'


_TITLE_RE = re.compile(
    r'^(chief|acting|senior|presiding|district|magistrate|hon\.?|honorable|'
    r'justice|judge|court|d\.)\s+',
    re.IGNORECASE,
)


def _norm_judge(judge):
    s = (judge or '').lower()
    prev = None
    while s != prev:
        prev = s
        s = _TITLE_RE.sub('', s).strip()
    return re.sub(r'[^a-z0-9]+', '', s)


def _norm_state(state):
    return (state or '').strip().lower()


def _date10(value):
    return (value or '')[:10]


def _norm_name(name):
    return re.sub(r'[^a-z0-9]+', '', (name or '').lower())


def build_source_index(results):
    """Index raw R&G `results` items for recovery lookups.

    Returns (by_id, by_key, by_name) where by_key is
    (date, state, judge_norm) -> url and by_name is name_norm -> (id, url),
    limited to *unambiguous* titles (a title mapping to more than one distinct
    source URL is dropped, since many judges have multiple orders under one
    title and a guess would attach the wrong document).
    """
    by_id = {}
    by_key = {}
    name_first = {}
    name_urls = {}
    for item in results:
        url = (item.get('linkToCourtOrder') or {}).get('url', '') or ''
        if not url:
            continue
        rid = item.get('id')
        if rid:
            by_id[rid] = url
        date = _date10(item.get('effectiveDate', ''))
        state = _norm_state(item.get('state', ''))
        judges = item.get('judge', []) or []
        judge_norm = _norm_judge(' '.join(judges))
        if date and judge_norm:
            by_key.setdefault((date, state, judge_norm), url)
        nname = _norm_name((item.get('linkToCourtOrder') or {}).get('text', ''))
        if nname:
            name_first.setdefault(nname, (rid, url))
            name_urls.setdefault(nname, set()).add(url)
    by_name = {n: name_first[n] for n in name_first if len(name_urls[n]) == 1}
    return by_id, by_key, by_name


def recover(records, results):
    """Set `original_link` and `link_source` on each record (mutates in place).

    Returns a small stats dict for reporting.
    """
    by_id, by_key, by_name = build_source_index(results)
    stats = {'by_id': 0, 'by_key': 0, 'by_name': 0, 'from_self': 0, 'none': 0}

    for rec in records:
        link = rec.get('link', '') or ''
        rec['link_source'] = classify_link_source(link)

        original = ''
        rid = rec.get('_rg_id')
        if rid and rid in by_id:
            original = by_id[rid]
            stats['by_id'] += 1
        else:
            key = (
                _date10(rec.get('date', '')),
                _norm_state(rec.get('state', '')),
                _norm_judge(rec.get('judge', '')),
            )
            if key[0] and key[2] and key in by_key:
                original = by_key[key]
                stats['by_key'] += 1
            else:
                # Exact, unambiguous title match — restores provenance when the
                # _rg_id linkage was lost and the date was stored coarsely.
                src = by_name.get(_norm_name(rec.get('name', '')))
                if src and src[1]:
                    original = src[1]
                    if not rec.get('_rg_id') and src[0]:
                        rec['_rg_id'] = src[0]   # backfill the lost linkage
                    stats['by_name'] += 1

        if not original:
            # No source match. Keep an already-set original_link (e.g. provenance
            # set by the LAG converter); else preserve the current link only when
            # it is itself a paywalled source link (Lexis/Westlaw).
            preset = rec.get('original_link')
            if preset:
                original = preset
                stats['preset'] = stats.get('preset', 0) + 1
            elif rec['link_source'] in ('lexis', 'westlaw'):
                original = link
                stats['from_self'] += 1
            else:
                stats['none'] += 1

        rec['original_link'] = original

    return stats

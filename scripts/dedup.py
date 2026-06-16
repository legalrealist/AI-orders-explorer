"""Merge same-order duplicates created by double-ingestion (R&G + LAG/rails).

The same standing order is often tracked by both the Ropes & Gray feed and the
LAG/rails feed, producing two records with complementary fields (one carries a
self-hosted `pdf`, the other an `original_link`, etc.). They are detected by an
*identical full summary* within the same (judge, court, type) group — a detailed
summary paragraph does not collide across genuinely different orders, so this is
conservative: distinct rulings in one case (different summaries) and civil-vs-
criminal order splits are never merged.

Pure functions over inputs — no network.
"""

import re

_TITLE_RE = re.compile(
    r'^(chief|acting|senior|presiding|district|magistrate|hon\.?|honorable|'
    r'justice|judge|court|d\.)\s+',
    re.IGNORECASE,
)


def _njudge(judge):
    s = (judge or '').lower()
    prev = None
    while s != prev:
        prev = s
        s = _TITLE_RE.sub('', s).strip()
    return re.sub(r'[^a-z0-9]+', '', s)


def _ncourt(court):
    return re.sub(r'[^a-z0-9]+', '', (court or '').lower())


def _source_rank(src):
    return {'both': 0, 'rg': 1, 'rails': 2}.get(src, 3)


def _doc_class(record):
    """Civil/criminal discriminator: judges issue parallel civil and criminal
    standing orders with identical AI language; their links name the difference.
    Keeps those two documents from being merged into one."""
    low = (record.get('link') or '').lower()
    return 'criminal' if 'criminal' in low else ''


def _richer(a, b):
    """Pick the record to keep: prefer source authority, then date precision."""
    ra, rb = _source_rank(a.get('source')), _source_rank(b.get('source'))
    if ra != rb:
        return a if ra < rb else b
    da, db = len(a.get('date') or ''), len(b.get('date') or '')
    if da != db:
        return a if da > db else b
    return a if a.get('id', 0) <= b.get('id', 0) else b


def _merge_into(keep, drop):
    """Fold complementary fields from `drop` into `keep` (mutates keep)."""
    keep['source'] = 'both'
    # Fill scalar fields only when keep's is empty.
    for f in ('pdf', 'original_link', 'link', '_rg_id', 'ai_type', 'applies_to'):
        if not (keep.get(f) or '') and (drop.get(f) or ''):
            keep[f] = drop[f]
    # Prefer a full date over a month-only one.
    if len(keep.get('date') or '') < len(drop.get('date') or ''):
        keep['date'] = drop['date']
    # Union requirement flags (OR booleans; keep any rule string).
    rk, rd = keep.get('reqs') or {}, drop.get('reqs') or {}
    merged = dict(rd)
    merged.update({k: v for k, v in rk.items() if v})
    for k, v in rd.items():
        if v and not merged.get(k):
            merged[k] = v
    if merged:
        keep['reqs'] = merged
    # Keep the richer multi-value lists.
    for f in ('applicableTo',):
        if len(drop.get(f) or []) > len(keep.get(f) or []):
            keep[f] = drop[f]


def find_duplicate_groups(records):
    """Return lists of record ids that are the same order (>=2 per group)."""
    groups = {}
    for r in records:
        summ = re.sub(r'\s+', ' ', (r.get('summary') or '')).strip()
        if not summ:
            continue
        key = (_njudge(r.get('judge', '')), _ncourt(r.get('court', '')),
               r.get('type', ''), _doc_class(r), summ)
        groups.setdefault(key, []).append(r)
    return [[r['id'] for r in recs] for recs in groups.values() if len(recs) > 1]


def merge_duplicates(records):
    """Merge same-order duplicates in place. Returns (new_records, stats)."""
    by_id = {r['id']: r for r in records}
    removed = set()
    groups = 0
    for ids in find_duplicate_groups(records):
        recs = [by_id[i] for i in ids if i not in removed]
        if len(recs) < 2:
            continue
        groups += 1
        keep = recs[0]
        for r in recs[1:]:
            keep = _richer(keep, r)
        for r in recs:
            if r is keep:
                continue
            _merge_into(keep, r)
            removed.add(r['id'])
    new = [r for r in records if r['id'] not in removed]
    return new, {'groups': groups, 'removed': len(removed)}

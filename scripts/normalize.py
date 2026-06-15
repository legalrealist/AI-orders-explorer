"""Normalize explorer records to the canonical schema.

Applies the cleanup rules:
- reqs flag values ('checked' / 'Yes' / any truthy) -> boolean True; the `rules`
  key keeps its citation string.
- consequence '' -> None.
- uniform field presence: every record carries the full schema.REQUIRED_KEYS set
  with sensible empty defaults.

Idempotent: normalize(normalize(x)) == normalize(x). Pure-ish — mutates and
returns the same list.
"""

import re

import schema

_STR_DEFAULT = {
    'name', 'judge', 'court', 'state', 'state_abbr', 'date', 'type', 'source',
    'jurisdiction', 'link', 'original_link', 'ai_type', 'applies_to', 'summary',
    'pdf',
}


def _empty_sanction_types():
    return {'amount_awarded': None, 'amount_sought': None, 'types': []}


def normalize_reqs(reqs):
    if not isinstance(reqs, dict):
        return {}
    out = {}
    for k, v in reqs.items():
        if k == schema.CITATION_KEY:
            if isinstance(v, str) and v.strip():
                out[k] = v
        elif k in schema.FLAG_KEYS:
            if v:  # 'checked', 'Yes', True -> True; drop falsy flags
                out[k] = True
        # unknown keys are dropped
    return out


def normalize_record(rec):
    rec['reqs'] = normalize_reqs(rec.get('reqs'))

    c = rec.get('consequence')
    rec['consequence'] = c if c in schema.CONSEQUENCES else None

    st = rec.get('sanction_types')
    if not isinstance(st, dict):
        st = _empty_sanction_types()
    else:
        st.setdefault('amount_awarded', None)
        st.setdefault('amount_sought', None)
        if not isinstance(st.get('types'), list):
            st['types'] = []
    rec['sanction_types'] = st

    if not isinstance(rec.get('applicableTo'), list):
        rec['applicableTo'] = []

    if '_rg_id' not in rec or not (rec['_rg_id'] is None or isinstance(rec['_rg_id'], str)):
        rec['_rg_id'] = rec.get('_rg_id') if isinstance(rec.get('_rg_id'), str) else None

    if rec.get('link_source') not in schema.LINK_SOURCES:
        rec['link_source'] = 'none'

    for k in _STR_DEFAULT:
        if not isinstance(rec.get(k), str):
            rec[k] = ''

    return rec


# --- court value normalization (dataset-level) ---
# The same federal district court is stored both abbreviated ("S.D.N.Y.") and
# long-form ("U.S. District Court, Southern District of New York[, X Division]").
# Collapse each (direction, state) group to its shortest spelling. Only federal
# district courts are touched — state, appeals, and bankruptcy courts are left
# alone (no key is computed for them).

_DIR = {'northern': 'N', 'southern': 'S', 'eastern': 'E',
        'western': 'W', 'middle': 'M', 'central': 'C'}
_LONG_FED = re.compile(r'(U\.S\.|United States)\s+District Court', re.I)


def _is_fed_district(court):
    if court.startswith('Bankr.'):
        return False
    return bool(_LONG_FED.search(court)
                or re.match(r'^[NSEWMC]\.D\.', court)
                or re.match(r'^D\.\s*[A-Z]', court)
                or re.match(r'^D\.D\.C\.', court))


def _court_direction(court):
    if _LONG_FED.search(court):
        m = re.search(r'(Northern|Southern|Eastern|Western|Middle|Central)\s+District',
                      court, re.I)
        return _DIR[m.group(1).lower()] if m else ''
    m = re.match(r'^([NSEWMC])\.D\.', court)
    return m.group(1) if m else ''


def normalize_courts(records):
    """Collapse multi-spelling federal-district courts to one canonical form."""
    groups = {}
    for r in records:
        c = r.get('court', '') or ''
        if c and _is_fed_district(c):
            groups.setdefault((_court_direction(c), r.get('state', '')), []).append(r)
    stats = {'collision_groups': 0, 'records_changed': 0}
    for recs in groups.values():
        spellings = {r['court'] for r in recs}
        if len(spellings) <= 1:
            continue
        canon = min(spellings, key=lambda s: (len(s), s))  # shortest = the abbreviation
        stats['collision_groups'] += 1
        for r in recs:
            if r['court'] != canon:
                r['court'] = canon
                stats['records_changed'] += 1

    # Collapse any courts that are identical after stripping punctuation/spacing
    # (e.g. "Ct. Int'l Trade" vs "Ct. Int'l. Trade") to the shortest spelling.
    byn = {}
    for r in records:
        c = r.get('court', '') or ''
        if c:
            byn.setdefault(re.sub(r'[^a-z0-9]+', '', c.lower()), []).append(r)
    for recs in byn.values():
        spellings = {r['court'] for r in recs}
        if len(spellings) <= 1:
            continue
        canon = min(spellings, key=lambda s: (len(s), s))
        for r in recs:
            if r['court'] != canon:
                r['court'] = canon
                stats['records_changed'] += 1
    return stats


def normalize(records):
    for rec in records:
        normalize_record(rec)
    normalize_courts(records)
    return records

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

import schema

_STR_DEFAULT = {
    'name', 'judge', 'court', 'state', 'state_abbr', 'date', 'type', 'source',
    'jurisdiction', 'link', 'original_link', 'ai_type', 'applies_to', 'summary',
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


def normalize(records):
    for rec in records:
        normalize_record(rec)
    return records

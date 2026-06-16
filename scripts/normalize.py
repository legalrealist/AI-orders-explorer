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


def _norm_amount(val):
    """Standardize a sanction amount to '$X,XXX[.cc]', or None if non-monetary.

    The field historically held prose ('None (warning only)', 'Dismissal with
    prejudice', '1 year suspension'); those carry no dollar figure and become
    None — the description lives in consequence / sanction_types.types / summary.
    """
    if not val:
        return None
    m = re.search(r'\$\s?([\d,]+(?:\.\d+)?)', str(val))
    if not m:
        return None
    try:
        f = float(m.group(1).replace(',', ''))
    except ValueError:
        return None
    return '${:,}'.format(int(f)) if f == int(f) else '${:,.2f}'.format(f)


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
    st['amount_awarded'] = _norm_amount(st.get('amount_awarded'))
    st['amount_sought'] = _norm_amount(st.get('amount_sought'))
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

    if not isinstance(rec.get('unverified'), bool):
        rec['unverified'] = False

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

# Bluebook (T1) state abbreviations for federal district/bankruptcy reporters.
_STATE_ABBR = {
    'alabama': 'Ala.', 'alaska': 'Alaska', 'arizona': 'Ariz.', 'arkansas': 'Ark.',
    'california': 'Cal.', 'colorado': 'Colo.', 'connecticut': 'Conn.',
    'delaware': 'Del.', 'florida': 'Fla.', 'georgia': 'Ga.', 'hawaii': 'Haw.',
    'idaho': 'Idaho', 'illinois': 'Ill.', 'indiana': 'Ind.', 'iowa': 'Iowa',
    'kansas': 'Kan.', 'kentucky': 'Ky.', 'louisiana': 'La.', 'maine': 'Me.',
    'maryland': 'Md.', 'massachusetts': 'Mass.', 'michigan': 'Mich.',
    'minnesota': 'Minn.', 'mississippi': 'Miss.', 'missouri': 'Mo.',
    'montana': 'Mont.', 'nebraska': 'Neb.', 'nevada': 'Nev.',
    'new hampshire': 'N.H.', 'new jersey': 'N.J.', 'new mexico': 'N.M.',
    'new york': 'N.Y.', 'north carolina': 'N.C.', 'north dakota': 'N.D.',
    'ohio': 'Ohio', 'oklahoma': 'Okla.', 'oregon': 'Or.', 'pennsylvania': 'Pa.',
    'rhode island': 'R.I.', 'south carolina': 'S.C.', 'south dakota': 'S.D.',
    'tennessee': 'Tenn.', 'texas': 'Tex.', 'utah': 'Utah', 'vermont': 'Vt.',
    'virginia': 'Va.', 'washington': 'Wash.', 'west virginia': 'W. Va.',
    'wisconsin': 'Wis.', 'wyoming': 'Wyo.', 'district of columbia': 'D.C.',
}
# Initialism abbreviations merge with the directional prefix (S.D.N.Y., D.S.C.);
# single-word contractions take a space (S.D. Cal., E.D. Mich.).
_MERGE_STATES = {'N.Y.', 'N.C.', 'S.C.', 'N.D.', 'S.D.', 'N.J.', 'N.H.',
                 'N.M.', 'R.I.', 'D.C.'}
_ORDINAL = {'first': '1st', 'second': '2d', 'third': '3d', 'fourth': '4th',
            'fifth': '5th', 'sixth': '6th', 'seventh': '7th', 'eighth': '8th',
            'ninth': '9th', 'tenth': '10th', 'eleventh': '11th'}
# Non-pattern straggler spellings of the same court.
_COURT_FIXES = {'2nd Cir.': '2d Cir.', 'Minn. Tax Court': 'Minn. Tax Ct.'}


def _abbrev_federal(court):
    """Long-form federal court name -> Bluebook abbreviation, else None."""
    c = court.strip()
    m = re.match(r'(?:U\.S\.|United States)\s+Court of Appeals for the '
                 r'(\w+) Circuit$', c, re.I)
    if m:
        o = _ORDINAL.get(m.group(1).lower())
        return f'{o} Cir.' if o else None
    if re.match(r'(?:U\.S\.|United States)\s+Tax Court$', c, re.I):
        return 'U.S. Tax Ct.'
    m = re.match(r'(?:U\.S\.|United States)\s+(Bankruptcy|District) Court,\s+(.*)$',
                 c, re.I)
    if not m:
        return None
    prefix = 'Bankr. ' if m.group(1).lower() == 'bankruptcy' else ''
    rest = m.group(2)
    dm = re.match(r'(Northern|Southern|Eastern|Western|Middle|Central) District '
                  r'of (.+?)(?:,.*)?$', rest, re.I)
    if dm:
        d = _DIR[dm.group(1).lower()]
        st = _STATE_ABBR.get(dm.group(2).strip().lower())
        if st:
            return f'{prefix}{d}.D.{st}' if st in _MERGE_STATES else f'{prefix}{d}.D. {st}'
    gm = re.match(r'District of (.+?)(?:,.*)?$', rest, re.I)
    if gm:
        st = _STATE_ABBR.get(gm.group(1).strip().lower())
        if st:
            return f'{prefix}D.{st}' if st in _MERGE_STATES else f'{prefix}D. {st}'
    return None


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
    stats = {'collision_groups': 0, 'records_changed': 0}
    # Canonicalize long-form federal court names (and stray spellings) up front.
    for r in records:
        c = r.get('court', '') or ''
        canon = _COURT_FIXES.get(c) or _abbrev_federal(c)
        if canon and canon != c:
            r['court'] = canon
            stats['records_changed'] += 1
    groups = {}
    for r in records:
        c = r.get('court', '') or ''
        if c and _is_fed_district(c):
            groups.setdefault((_court_direction(c), r.get('state', '')), []).append(r)
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


# --- primary-source verification flag ---
# A record is `unverified` when the explorer cannot point a user at an openly
# accessible primary source: it has no self-hosted PDF and its link is not a
# real document pointer (a tracker/aggregator/news page, or empty). Official
# court/.gov pages and specific legal-research permalinks count as pointers.
# Hosts we treat as independently confirmed. Justia/Lexis/Westlaw/news are NOT
# here: their links are real-looking but unfetchable (or paywalled), so we keep
# the link but flag the record `unverified` rather than vouch for it.
_PRIMARY_HOSTS = ('courtlistener', 'recap', 'govinfo', 'google.com', 'dropbox')
# Records whose publicly reachable document was checked and did NOT support the
# summary — keyed on stable content, not id. (Both confirmed by fetching.)
_CONFIRMED_UNVERIFIED = (
    ('reggiebwalton', 'Standing Order'),
    ('brantleystarr', 'Standing Order'),
)


def _link_is_primary(url):
    from urllib.parse import urlparse
    if not url:
        return False
    u = url.lower()
    host = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    if u.endswith('.pdf'):
        return True
    if any(h in host for h in _PRIMARY_HOSTS):
        return True
    if 'ropesgray.com' in host or 'legalaigovernance.com' in host:
        return path.endswith('.pdf')   # tracker landing pages are not pointers
    if host.endswith('.gov') or '.gov' in host or 'courts.' in host:
        return True                    # official court site
    return False


def _confirmed_unverified(rec):
    j = re.sub(r'[^a-z0-9]+', '', (rec.get('judge') or '').lower())
    return any(sig in j and rec.get('type') == typ
               for sig, typ in _CONFIRMED_UNVERIFIED)


def mark_unverified(records):
    """Set `unverified` from final link/pdf state. Run after link validation."""
    n = 0
    for rec in records:
        bad = _confirmed_unverified(rec) or (
            not (rec.get('pdf') or '').strip()
            and not _link_is_primary(rec.get('link', '')))
        rec['unverified'] = bool(bad)
        n += bad
    return {'unverified': n}

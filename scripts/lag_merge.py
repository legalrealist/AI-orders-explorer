"""Merge converted LAG/RAILS litigation cases into the dataset.

LAG's cases.json is the *litigation* feed (sanctions/warnings opinions); it does
NOT cover the standing-orders/local-rules records that the prior manual RAILS
import (All_Data.csv) contributed. So existing records — including rails-only
standing orders — are preserved; LAG cases are matched against the full dataset
and only genuinely-new ones are appended as 'rails'.

Matching a LAG case to an existing record uses case identity, since sources
format judges differently ("Judge Cota" vs "Judge Jesse M. Furman"):
  1. docket number (strongest), e.g. 2:25-cv-02955
  2. party pair from the case name ("Geddes v. LoanCare") within a date window
  3. date + state + judge (legacy key, rarely fires across sources)

A match against an R&G record marks it 'both' and fills only its empty fields;
a match against an existing rails record just fills gaps. This makes re-runs
idempotent (a previously-added LAG case matches itself). A same-date+state
collision with no identity match is flagged to review_needed.json rather than
silently merged.
"""

import re
from datetime import date

import linkrecover

_FILLABLE = ('summary', 'link', 'original_link', 'judge', 'state', 'state_abbr')
_PARTY_DATE_WINDOW_DAYS = 120

_PARTY_RE = re.compile(
    r"([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+)*)\s+v\.?\s+([A-Z][\w.'-]+)")
_DOCKET_RE = re.compile(r"\b(\d{1,2}:\d{2}-[a-z]{2,4}-\d{3,6})\b", re.I)


def extract_parties(text):
    m = _PARTY_RE.search(text or '')
    if not m:
        return None
    a = re.sub(r'[^a-z]', '', m.group(1).split()[-1].lower())
    b = re.sub(r'[^a-z]', '', m.group(2).lower())
    return (a, b) if a and b else None


def extract_docket(text):
    m = _DOCKET_RE.search(text or '')
    return m.group(1).lower() if m else None


def _parse_date(s):
    try:
        y, m, d = (s or '')[:10].split('-')
        return date(int(y), int(m), int(d))
    except (ValueError, AttributeError):
        return None


def _date_within(a, b, days):
    da, db = _parse_date(a), _parse_date(b)
    if not da or not db:
        return True  # can't disprove; allow party match
    return abs((da - db).days) <= days


def _legacy_key(rec):
    return (
        (rec.get('date') or '')[:10],
        linkrecover._norm_state(rec.get('state')),
        linkrecover._norm_judge(rec.get('judge')),
    )


def _rg_blob(rec):
    return (rec.get('summary', '') or '') + ' ' + (rec.get('name', '') or '')


def _lag_blob(rec):
    return (rec.get('name', '') or '') + ' ' + (rec.get('summary', '') or '')


def merge_lag(existing, lag_records):
    """Return (merged, review, stats). Mutates matched records in place."""
    by_docket, by_party, by_legacy, by_date_state = {}, {}, {}, {}
    for r in existing:
        blob = _rg_blob(r)
        d = extract_docket(blob)
        if d:
            by_docket.setdefault(d, r)
        p = extract_parties(r.get('name', '')) or extract_parties(blob)
        if p:
            by_party.setdefault(p, []).append(r)
        lk = _legacy_key(r)
        if lk[0] and lk[2]:
            by_legacy.setdefault(lk, r)
        by_date_state.setdefault((lk[0], lk[1]), []).append(r)

    review = []
    stats = {'matched_docket': 0, 'matched_party': 0, 'matched_legacy': 0,
             'rails_only': 0, 'review': 0,
             'existing_total': len(existing), 'lag_total': len(lag_records)}
    added = []

    for lag in lag_records:
        match = _find_match(lag, by_docket, by_party, by_legacy, stats)
        if match:
            if match.get('source') == 'rg':
                match['source'] = 'both'
            _fill_gaps(match, lag)
            continue

        lk = _legacy_key(lag)
        candidates = by_date_state.get((lk[0], lk[1]), []) if lk[0] and lk[1] else []
        if candidates:
            review.append({
                'lag_name': lag.get('name', ''), 'date': lag.get('date', ''),
                'state': lag.get('state', ''), 'lag_judge': lag.get('judge', ''),
                'candidates': [c.get('name', '') for c in candidates][:5],
            })
            stats['review'] += 1
        added.append(lag)
        stats['rails_only'] += 1

    merged = existing + added
    for i, rec in enumerate(merged):
        rec['id'] = i
    return merged, review, stats


def _find_match(lag, by_docket, by_party, by_legacy, stats):
    blob = _lag_blob(lag)
    docket = extract_docket(lag.get('summary', '')) or extract_docket(blob)
    if docket and docket in by_docket:
        stats['matched_docket'] += 1
        return by_docket[docket]

    party = extract_parties(lag.get('name', '')) or extract_parties(blob)
    if party and party in by_party:
        for cand in by_party[party]:
            if _date_within(lag.get('date'), cand.get('date'), _PARTY_DATE_WINDOW_DAYS):
                stats['matched_party'] += 1
                return cand

    lk = _legacy_key(lag)
    if lk[0] and lk[2] and lk in by_legacy:
        stats['matched_legacy'] += 1
        return by_legacy[lk]
    return None


def _fill_gaps(rg_rec, lag_rec):
    for f in _FILLABLE:
        if not rg_rec.get(f) and lag_rec.get(f):
            rg_rec[f] = lag_rec[f]
    if not rg_rec.get('link_source') or rg_rec.get('link_source') == 'none':
        rg_rec['link_source'] = linkrecover.classify_link_source(rg_rec.get('link', ''))
    st = rg_rec.get('sanction_types') or {}
    lst = lag_rec.get('sanction_types') or {}
    if not st.get('amount_awarded') and lst.get('amount_awarded'):
        st['amount_awarded'] = lst['amount_awarded']
        rg_rec['sanction_types'] = st

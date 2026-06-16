"""Convert LegalAIGovernance (LAG/RAILS) cases to the canonical explorer schema.

Deterministic mapping — no LLM. Produces records that satisfy schema.validate.
LAG cases are litigation rulings (sanctions / warnings), so they map to
Judicial Opinions from the 'rails' source.
"""

import re

import linkrecover
import normalize

STATE_ABBR = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
    'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
    'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN',
    'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE',
    'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC',
    'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR',
    'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
    'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
    'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
    'District of Columbia': 'DC', 'Puerto Rico': 'PR', 'Guam': 'GU',
}
# Longest-first so "West Virginia" matches before "Virginia".
_STATE_NAMES_SORTED = sorted(STATE_ABBR, key=len, reverse=True)

# Common federal-district jurisdiction abbreviations -> state.
_JURIS_STATE = {
    'N.Y.': 'New York', 'CAL.': 'California', 'FLA.': 'Florida',
    'TEX.': 'Texas', 'ILL.': 'Illinois', 'PA.': 'Pennsylvania',
    'MICH.': 'Michigan', 'WASH.': 'Washington', 'MASS.': 'Massachusetts',
    'N.J.': 'New Jersey', 'COLO.': 'Colorado', 'ARIZ.': 'Arizona',
    'OHIO': 'Ohio', 'GA.': 'Georgia', 'VA.': 'Virginia', 'MD.': 'Maryland',
    'CONN.': 'Connecticut', 'NEV.': 'Nevada', 'MINN.': 'Minnesota',
    'D.C.': 'District of Columbia',
}

_JUDGE_RE = re.compile(r'\(([A-Z][A-Za-z.\'-]+(?:\s+[A-Z][A-Za-z.\'-]+)?),\s*'
                       r'(?:Chief\s+)?(?:Mag\.?\s*|Magistrate\s+)?(?:J|C)')

# Fallback: a judge named in prose ("...Judge Timothy L. Brooks issued..."),
# used when the structured citation carries no judge. Anchors on the word
# Judge/Justice and captures the following name — first/last words, middle
# initials, accented letters, apostrophe surnames ("d'Auguste"), and lowercase
# nobiliary particles ("van Keulen") — stopping at the first ordinary word.
_NAME_WORD = r"(?:[a-z]['’])?[A-ZÀ-Þ][a-zß-ÿ]+(?:['’\-][A-Za-zÀ-ÿ]+)*"
_INITIAL = r"[A-Z]\."
_PARTICLE = r"(?:van|von|de|del|della|di|da|du|le|la|der|den|ten|ter)"
_PROSE_JUDGE_RE = re.compile(
    r'\b(?:Judge|Justice)\s+'
    rf'({_NAME_WORD}'
    rf'(?:\s+(?:{_INITIAL}|{_PARTICLE}\s+{_NAME_WORD}|{_NAME_WORD}))*)')
# Capitalized words that follow "Judge"/"Justice" but are not personal names.
_NOT_JUDGE_NAME = {'Department', 'Court', 'Advocate', 'System', 'Building',
                   'Center', 'Division', 'District'}


def extract_state(court, jurisdiction):
    text = court or ''
    for name in _STATE_NAMES_SORTED:
        if name.lower() in text.lower():
            return name, STATE_ABBR[name]
    j = (jurisdiction or '').upper()
    for token, name in _JURIS_STATE.items():
        if token in j:
            return name, STATE_ABBR[name]
    return '', ''


def extract_judge(citation):
    m = _JUDGE_RE.search(citation or '')
    if m:
        return 'Judge ' + m.group(1).strip()
    return ''


def extract_judge_prose(text):
    """Recover 'Judge <name>' from narrative prose when no citation judge."""
    for m in _PROSE_JUDGE_RE.finditer(text or ''):
        toks = m.group(1).split()
        while len(toks) > 1 and re.fullmatch(r"[A-Z]\.?", toks[-1]):
            toks.pop()  # never end a name on a dangling initial
        if toks[0] in _NOT_JUDGE_NAME:
            continue
        return 'Judge ' + ' '.join(toks)
    return ''


def build_summary(case):
    """Narrative description plus the outcome's final disposition."""
    desc = (case.get('description') or '').strip()
    outcome = (case.get('outcome') or '').strip()
    if not outcome or outcome in desc:
        return desc
    if not desc:
        return outcome
    return desc + ' ' + outcome


def _ai_type(ai_tool):
    low = (ai_tool or '').lower()
    if low.startswith('any ai') or 'any ai' in low:
        return 'Any AI'
    return 'Gen AI'


def _applies_to(text):
    low = (text or '').lower()
    if 'pro se' in low or 'self-represented' in low or 'self represented' in low:
        return 'Pro Se Litigants'
    return 'Attorneys'


def _consequence_and_sanctions(case, applies_to):
    stype = case.get('sanction_type', '')
    amount = case.get('sanction_amount') or None
    types = []
    consequence = None
    if stype == 'warning':
        consequence = 'warning'
    elif stype == 'court_sanction':
        consequence = 'sanctions_party' if applies_to == 'Pro Se Litigants' else 'sanctions_attorney'
        if amount:
            types.append('monetary')
    elif stype == 'bar_discipline':
        consequence = 'sanctions_attorney'
        types.append('bar_referral')
    # 'other' -> consequence stays None
    sanction_types = {'amount_awarded': amount, 'amount_sought': None, 'types': types}
    return consequence, sanction_types


def _applicable_to(consequence):
    tags = ['Generative AI Usage']
    if consequence == 'sanctions_attorney':
        tags.append('Court-Imposed Consequences - Attorneys/Law Firms')
    elif consequence == 'sanctions_party':
        tags.append('Court-Imposed Consequences - Parties')
    return tags


def _choose_link(case):
    for key in ('primary_source_urls', 'source_urls'):
        urls = case.get(key) or []
        if urls:
            return urls[0]
    return case.get('url', '') or ''


def convert_case(case, idx=0):
    """Convert one LAG case dict to a canonical explorer record."""
    court = case.get('court', '') or ''
    state, state_abbr = extract_state(court, case.get('jurisdiction', ''))
    applies_to = _applies_to((case.get('description', '') or '') + ' ' + (case.get('outcome', '') or ''))
    consequence, sanction_types = _consequence_and_sanctions(case, applies_to)
    link = _choose_link(case)

    judge = extract_judge(case.get('citation', ''))
    if not judge:
        judge = extract_judge_prose(
            (case.get('description', '') or '') + ' '
            + (case.get('outcome', '') or ''))

    rec = {
        'id': idx,
        'name': case.get('case_name', '') or '',
        'judge': judge,
        'court': court,
        'state': state,
        'state_abbr': state_abbr,
        'date': (case.get('date', '') or '')[:10],
        'type': 'Judicial Opinion',
        'source': 'rails',
        'jurisdiction': 'US',
        'link': link,
        'original_link': link,
        'link_source': linkrecover.classify_link_source(link),
        'ai_type': _ai_type(case.get('ai_tool', '')),
        'applies_to': applies_to,
        'summary': build_summary(case),
        'reqs': {},
        'consequence': consequence,
        'applicableTo': _applicable_to(consequence),
        'sanction_types': sanction_types,
        '_rg_id': None,
    }
    return normalize.normalize_record(rec)


def convert_all(cases, start_id=0):
    return [convert_case(c, start_id + i) for i, c in enumerate(cases)]

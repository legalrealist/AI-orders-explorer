"""Canonical record schema for explorer_data.json.

Single source of truth for the cleaned schema. The one-time cleanup driver
(cleanup.py) and the pipeline (update.py) both validate against this before
writing, and the test suite asserts against it.

The validators are pure: they report problems and never mutate input.
"""

# reqs keys that are boolean flags (normalized to True). Mirrors the flag keys
# in charts/src/constants.js REQ_ACTIONS / REQ_LABELS.
FLAG_KEYS = {
    'disclose', 'tool', 'how', 'sections', 'verify', 'certify_all',
    'certify_if_ai', 'prompts', 'proprietary', 'prohibited', 'warning',
    'evidence',
}
# The one reqs key whose value is a rule-citation string, not a flag.
CITATION_KEY = 'rules'

# Valid values for the link_source provenance field.
LINK_SOURCES = {
    'courtlistener', 'lexis', 'westlaw', 'justia', 'govinfo', 'ropesgray',
    'other', 'none',
}

# Valid consequence values (besides None).
CONSEQUENCES = {'warning', 'sanctions_attorney', 'sanctions_party'}

# Every cleaned record carries exactly this key set.
REQUIRED_KEYS = {
    'id', 'name', 'judge', 'court', 'state', 'state_abbr', 'date', 'type',
    'source', 'jurisdiction', 'link', 'original_link', 'link_source', 'pdf',
    'ai_type', 'applies_to', 'summary', 'reqs', 'consequence', 'applicableTo',
    'sanction_types', '_rg_id', 'unverified',
}

_STR_KEYS = {
    'name', 'judge', 'court', 'state', 'state_abbr', 'date', 'type', 'source',
    'jurisdiction', 'link', 'original_link', 'ai_type', 'applies_to', 'summary',
    'pdf',
}


def validate_record(rec, idx=None):
    """Return a list of human-readable problems for one record (empty == valid)."""
    where = f'record[{idx}]' if idx is not None else 'record'
    problems = []

    if not isinstance(rec, dict):
        return [f'{where}: not a dict']

    keys = set(rec.keys())
    for missing in sorted(REQUIRED_KEYS - keys):
        problems.append(f'{where}: missing key {missing!r}')
    for extra in sorted(keys - REQUIRED_KEYS):
        problems.append(f'{where}: unexpected key {extra!r}')

    if 'id' in rec and not isinstance(rec['id'], int):
        problems.append(f'{where}: id must be int, got {type(rec["id"]).__name__}')

    for k in _STR_KEYS:
        if k in rec and not isinstance(rec[k], str):
            problems.append(f'{where}: {k} must be str, got {type(rec[k]).__name__}')

    if 'link_source' in rec and rec['link_source'] not in LINK_SOURCES:
        problems.append(f'{where}: link_source {rec["link_source"]!r} not in enum')

    if 'consequence' in rec:
        c = rec['consequence']
        if c is not None and c not in CONSEQUENCES:
            problems.append(f'{where}: consequence {c!r} must be null or one of {sorted(CONSEQUENCES)}')

    if 'applicableTo' in rec and not isinstance(rec['applicableTo'], list):
        problems.append(f'{where}: applicableTo must be list')

    if '_rg_id' in rec and not (rec['_rg_id'] is None or isinstance(rec['_rg_id'], str)):
        problems.append(f'{where}: _rg_id must be str or null')

    if 'unverified' in rec and not isinstance(rec['unverified'], bool):
        problems.append(f'{where}: unverified must be bool')

    problems.extend(_validate_reqs(rec.get('reqs'), where))
    problems.extend(_validate_sanction_types(rec.get('sanction_types'), where))
    return problems


def _validate_reqs(reqs, where):
    if reqs is None:
        return [f'{where}: reqs missing']
    if not isinstance(reqs, dict):
        return [f'{where}: reqs must be dict']
    problems = []
    for k, v in reqs.items():
        if k == CITATION_KEY:
            if not isinstance(v, str):
                problems.append(f'{where}: reqs.{k} must be str')
        elif k in FLAG_KEYS:
            if v is not True:
                problems.append(f'{where}: reqs.{k} must be normalized to True, got {v!r}')
        else:
            problems.append(f'{where}: unknown reqs key {k!r}')
    return problems


def _validate_sanction_types(st, where):
    if st is None:
        return [f'{where}: sanction_types missing']
    if not isinstance(st, dict):
        return [f'{where}: sanction_types must be dict']
    problems = []
    for k in ('amount_awarded', 'amount_sought', 'types'):
        if k not in st:
            problems.append(f'{where}: sanction_types missing {k!r}')
    if 'types' in st and not isinstance(st['types'], list):
        problems.append(f'{where}: sanction_types.types must be list')
    return problems


def validate_dataset(records):
    """Return a flat list of problems across all records (empty == valid)."""
    if not isinstance(records, list):
        return ['dataset: not a list']
    problems = []
    for i, rec in enumerate(records):
        problems.extend(validate_record(rec, i))
    return problems

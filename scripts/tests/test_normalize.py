import copy

import normalize
import schema


def base():
    return {
        'id': 1,
        'name': 'n', 'judge': 'j', 'court': 'c', 'state': 's', 'state_abbr': 'SS',
        'date': '2026-01-01', 'type': 'Judicial Opinion', 'source': 'rg',
        'jurisdiction': 'US', 'link': '', 'original_link': '', 'link_source': 'none',
        'ai_type': 'Gen AI', 'applies_to': 'Attorneys', 'summary': 'x',
        'reqs': {}, 'consequence': None, 'applicableTo': [],
        'sanction_types': {'amount_awarded': None, 'amount_sought': None, 'types': []},
        '_rg_id': None,
    }


def test_reqs_flags_become_true_rules_kept():
    rec = base()
    rec['reqs'] = {'disclose': 'checked', 'certify_all': 'Yes', 'rules': 'FRCP 11'}
    normalize.normalize_record(rec)
    assert rec['reqs'] == {'disclose': True, 'certify_all': True, 'rules': 'FRCP 11'}


def test_empty_reqs_stays_empty():
    rec = base()
    rec['reqs'] = {}
    normalize.normalize_record(rec)
    assert rec['reqs'] == {}


def test_falsy_flag_dropped():
    rec = base()
    rec['reqs'] = {'warning': '', 'verify': 'checked'}
    normalize.normalize_record(rec)
    assert rec['reqs'] == {'verify': True}


def test_consequence_empty_to_none():
    rec = base()
    rec['consequence'] = ''
    normalize.normalize_record(rec)
    assert rec['consequence'] is None


def test_consequence_valid_preserved():
    rec = base()
    rec['consequence'] = 'warning'
    normalize.normalize_record(rec)
    assert rec['consequence'] == 'warning'


def test_missing_sanction_types_filled():
    rec = base()
    del rec['sanction_types']
    normalize.normalize_record(rec)
    assert rec['sanction_types'] == {'amount_awarded': None, 'amount_sought': None, 'types': []}


def test_existing_sanction_types_untouched():
    rec = base()
    rec['sanction_types'] = {'amount_awarded': '$1,000', 'amount_sought': None, 'types': ['monetary']}
    normalize.normalize_record(rec)
    assert rec['sanction_types']['amount_awarded'] == '$1,000'
    assert rec['sanction_types']['types'] == ['monetary']


def test_idempotent():
    rec = base()
    rec['reqs'] = {'disclose': 'checked', 'rules': 'FRCP 11'}
    rec['consequence'] = ''
    once = normalize.normalize_record(copy.deepcopy(rec))
    twice = normalize.normalize_record(copy.deepcopy(once))
    assert once == twice


def test_normalized_record_passes_validator():
    rec = base()
    rec['reqs'] = {'disclose': 'checked', 'certify_all': 'Yes', 'rules': 'FRCP 11'}
    rec['consequence'] = ''
    normalize.normalize_record(rec)
    assert schema.validate_record(rec) == []


def test_bad_string_field_coerced():
    rec = base()
    rec['judge'] = None
    normalize.normalize_record(rec)
    assert rec['judge'] == ''


def _court(court, state):
    r = base()
    r['court'] = court
    r['state'] = state
    return r


def test_normalize_courts_collapses_dual_spelling():
    recs = [_court('S.D.N.Y.', 'New York'),
            _court('U.S. District Court, Southern District of New York', 'New York')]
    normalize.normalize_courts(recs)
    assert {r['court'] for r in recs} == {'S.D.N.Y.'}


def test_normalize_courts_drops_division_suffix():
    recs = [_court('N.D. Ill.', 'Illinois'),
            _court('U.S. District Court, Northern District of Illinois, Eastern Division', 'Illinois')]
    normalize.normalize_courts(recs)
    assert {r['court'] for r in recs} == {'N.D. Ill.'}


def test_normalize_courts_leaves_state_and_bankruptcy_courts():
    recs = [_court('Supreme Court of Montana', 'Montana'),
            _court('Bankr. W.D. La.', 'Louisiana'),
            _court('Court of Appeal of Florida', 'Florida')]
    before = [r['court'] for r in recs]
    normalize.normalize_courts(recs)
    assert [r['court'] for r in recs] == before


def test_normalize_courts_keeps_distinct_districts_separate():
    recs = [_court('N.D. Cal.', 'California'), _court('S.D. Cal.', 'California')]
    normalize.normalize_courts(recs)
    assert {r['court'] for r in recs} == {'N.D. Cal.', 'S.D. Cal.'}

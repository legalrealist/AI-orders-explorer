import copy

import schema


def clean_record():
    return {
        'id': 0,
        'name': 'Test Court – Judge X',
        'judge': 'Judge X',
        'court': 'Test Court',
        'state': 'Montana',
        'state_abbr': 'MT',
        'date': '2026-05-08',
        'type': 'Judicial Opinion',
        'source': 'rg',
        'jurisdiction': 'US',
        'link': 'https://www.courtlistener.com/opinion/1/x/',
        'original_link': 'https://advance.lexis.com/permalink/abc/',
        'link_source': 'courtlistener',
        'pdf': '',
        'ai_type': 'Gen AI',
        'applies_to': 'Attorneys',
        'summary': 'A summary.',
        'reqs': {'disclose': True, 'rules': 'FRCP 11'},
        'consequence': 'sanctions_attorney',
        'applicableTo': ['Generative AI Usage'],
        'sanction_types': {'amount_awarded': None, 'amount_sought': None, 'types': []},
        '_rg_id': 'abc-123',
        'unverified': False,
    }


def test_clean_record_has_no_problems():
    assert schema.validate_record(clean_record()) == []


def test_missing_original_link_reported():
    rec = clean_record()
    del rec['original_link']
    problems = schema.validate_record(rec)
    assert any('original_link' in p for p in problems)


def test_missing_link_source_reported():
    rec = clean_record()
    del rec['link_source']
    assert any('link_source' in p for p in schema.validate_record(rec))


def test_bad_link_source_reported():
    rec = clean_record()
    rec['link_source'] = 'bloomberg'
    assert any('link_source' in p and 'enum' in p for p in schema.validate_record(rec))


def test_unnormalized_reqs_flag_reported():
    rec = clean_record()
    rec['reqs'] = {'disclose': 'checked'}
    assert any('disclose' in p for p in schema.validate_record(rec))


def test_yes_reqs_flag_reported():
    rec = clean_record()
    rec['reqs'] = {'certify_all': 'Yes'}
    assert any('certify_all' in p for p in schema.validate_record(rec))


def test_rules_citation_string_is_valid():
    rec = clean_record()
    rec['reqs'] = {'rules': 'FRCP 11, 28 U.S.C. § 1927'}
    assert schema.validate_record(rec) == []


def test_empty_consequence_string_reported():
    rec = clean_record()
    rec['consequence'] = ''
    assert any('consequence' in p for p in schema.validate_record(rec))


def test_null_consequence_is_valid():
    rec = clean_record()
    rec['consequence'] = None
    assert schema.validate_record(rec) == []


def test_missing_sanction_types_reported():
    rec = clean_record()
    del rec['sanction_types']
    assert any('sanction_types' in p for p in schema.validate_record(rec))


def test_unexpected_key_reported():
    rec = clean_record()
    rec['bogus'] = 1
    assert any('bogus' in p for p in schema.validate_record(rec))


def test_validate_dataset_flags_each_record():
    bad = clean_record()
    bad['consequence'] = ''
    problems = schema.validate_dataset([clean_record(), bad])
    assert any('record[1]' in p for p in problems)
    assert all('record[0]' not in p for p in problems)


def test_validate_dataset_rejects_non_list():
    assert schema.validate_dataset({}) == ['dataset: not a list']

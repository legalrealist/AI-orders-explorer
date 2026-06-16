import json
import os

import lag_convert
import schema


GEDDES = {
    'slug': 'krista-geddes-v-loancare',
    'url': 'https://legalaigovernance.com/tracker/cases/krista-geddes-v-loancare/',
    'case_name': 'Krista C. Geddes v. LoanCare, LLC',
    'citation': 'Geddes v. LoanCare, No. 2:25-cv-02955 (E.D. Cal. Apr. 22, 2026) (Cota, Mag. J.)',
    'court': 'U.S. District Court, Eastern District of California',
    'jurisdiction': 'E.D. Cal.',
    'date': '2026-04-22',
    'ai_tool': 'Unspecified generative AI',
    'sanction_type': 'court_sanction',
    'sanction_amount': '$1,000',
    'pending': False,
    'outcome': '$1,000 monetary sanction imposed.',
    'description': 'A California attorney submitted briefing that misquoted authority.',
    'source_urls': ['https://websitedc.s3.amazonaws.com/documents/Geddes.pdf'],
    'primary_source_urls': [],
    'last_verified': '2026-05-14',
}


def test_court_sanction_with_amount():
    rec = lag_convert.convert_case(GEDDES, 0)
    assert rec['consequence'] == 'sanctions_attorney'
    assert rec['sanction_types']['amount_awarded'] == '$1,000'
    assert rec['sanction_types']['types'] == ['monetary']
    assert rec['source'] == 'rails'
    assert rec['type'] == 'Judicial Opinion'


def test_state_extracted_from_court():
    rec = lag_convert.convert_case(GEDDES, 0)
    assert rec['state'] == 'California'
    assert rec['state_abbr'] == 'CA'


def test_judge_parsed_from_citation():
    rec = lag_convert.convert_case(GEDDES, 0)
    assert rec['judge'] == 'Judge Cota'


def test_link_provenance_from_source_urls():
    rec = lag_convert.convert_case(GEDDES, 0)
    assert rec['link'] == 'https://websitedc.s3.amazonaws.com/documents/Geddes.pdf'
    assert rec['original_link'] == rec['link']
    assert rec['link_source'] in schema.LINK_SOURCES


def test_warning_maps_to_warning():
    case = dict(GEDDES, sanction_type='warning', sanction_amount=None)
    rec = lag_convert.convert_case(case, 0)
    assert rec['consequence'] == 'warning'
    assert rec['sanction_types']['types'] == []


def test_bar_discipline_adds_bar_referral():
    case = dict(GEDDES, sanction_type='bar_discipline', sanction_amount=None)
    rec = lag_convert.convert_case(case, 0)
    assert rec['consequence'] == 'sanctions_attorney'
    assert 'bar_referral' in rec['sanction_types']['types']


def test_other_sanction_type_is_null_consequence():
    case = dict(GEDDES, sanction_type='other', sanction_amount=None)
    rec = lag_convert.convert_case(case, 0)
    assert rec['consequence'] is None


def test_pro_se_maps_to_party():
    case = dict(GEDDES, description='A pro se litigant filed fabricated cases.')
    rec = lag_convert.convert_case(case, 0)
    assert rec['applies_to'] == 'Pro Se Litigants'
    assert rec['consequence'] == 'sanctions_party'


def test_empty_source_urls_falls_back_to_tracker_url():
    case = dict(GEDDES, source_urls=[], primary_source_urls=[])
    rec = lag_convert.convert_case(case, 0)
    assert rec['link'] == case['url']


def test_no_links_at_all_gives_none_source():
    case = dict(GEDDES, source_urls=[], primary_source_urls=[], url='')
    rec = lag_convert.convert_case(case, 0)
    assert rec['link'] == ''
    assert rec['link_source'] == 'none'


def test_converted_record_passes_validator():
    rec = lag_convert.convert_case(GEDDES, 0)
    assert schema.validate_record(rec) == []


def test_state_court_name_extraction():
    case = dict(GEDDES, court='Supreme Court of Texas', jurisdiction='Tex.')
    rec = lag_convert.convert_case(case, 0)
    assert rec['state'] == 'Texas'


def test_convert_all_real_sample_validates():
    path = os.path.join(os.path.dirname(__file__), '..', '..',
                        'data', 'sources', 'lag_cases.json')
    if not os.path.exists(path):
        return  # live cache not present; skip
    cases = json.load(open(path, encoding='utf-8'))['items']
    recs = lag_convert.convert_all(cases)
    assert schema.validate_dataset(recs) == []

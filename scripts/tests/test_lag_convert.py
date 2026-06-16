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


def test_pending_flag_carried_from_source():
    rec = lag_convert.convert_case(dict(GEDDES, pending=True), 0)
    assert rec['pending'] is True


def test_slug_carried_from_source():
    rec = lag_convert.convert_case(GEDDES, 0)
    assert rec['slug'] == 'krista-geddes-v-loancare'


def test_last_verified_carried_from_source():
    rec = lag_convert.convert_case(GEDDES, 0)
    assert rec['last_verified'] == '2026-05-14'


def test_ai_tool_normalized_to_canonical_name():
    assert lag_convert.normalize_tool('ChatGPT') == 'ChatGPT'
    assert lag_convert.normalize_tool('Microsoft Copilot') == 'Microsoft Copilot'
    assert lag_convert.normalize_tool('Google Gemini') == 'Google Gemini'
    assert lag_convert.normalize_tool('Claude') == 'Claude'
    assert lag_convert.normalize_tool('Westlaw CoCounsel') == 'Westlaw CoCounsel'


def test_ai_tool_unspecified_becomes_empty():
    assert lag_convert.normalize_tool('Unspecified generative AI') == ''
    assert lag_convert.normalize_tool('Generative AI inferred from the citation pattern') == ''
    rec = lag_convert.convert_case(GEDDES, 0)  # GEDDES ai_tool is unspecified
    assert rec['ai_tool'] == ''
    assert rec['ai_type'] == 'Gen AI'  # coarse enum still set


def test_not_pending_by_default():
    rec = lag_convert.convert_case(GEDDES, 0)
    assert rec['pending'] is False


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


# --- judge prose fallback (citation has no judge) ---

PIRANI = {
    'case_name': 'Jason M. Hatfield, P.A. v. Pirani',
    'citation': 'Jason M. Hatfield, P.A. v. Pirani, No. 5:22-CV-5110 (W.D. Ark.)',
    'court': 'U.S. District Court, Western District of Arkansas',
    'jurisdiction': 'W.D. Ark.', 'date': '2025-12-04', 'ai_tool': 'ChatGPT',
    'sanction_type': 'court_sanction',
    'sanction_amount': '$1,578,172 attorney fees + $93,388 costs',
    'outcome': "$1,578,172 in additional attorney fees and $93,388 in costs "
               "awarded to opposing party. Judge Brooks stated the sanctions "
               "were intended to deter similar misconduct.",
    'description': 'Attorney Tony Pirani used ChatGPT to draft post-trial '
                   'motions. He admitted the AI use; Judge Timothy L. Brooks '
                   'issued an order to show cause on 2025-07-31.',
    'source_urls': ['https://www.courtlistener.com/docket/63367909/x/'],
    'primary_source_urls': [],
}


def test_judge_recovered_from_prose_when_citation_lacks_it():
    rec = lag_convert.convert_case(PIRANI, 0)
    assert rec['judge'] == 'Judge Timothy L. Brooks'


def test_citation_judge_takes_precedence_over_prose():
    case = dict(PIRANI,
                citation='Foo v. Bar, No. 1:24-cv-1 (D. Or.) (Clarke, Mag. J.)')
    rec = lag_convert.convert_case(case, 0)
    assert rec['judge'] == 'Judge Clarke'


def test_prose_full_surname_not_truncated_at_initial():
    case = dict(PIRANI, citation='No citation judge here',
                description='Magistrate Judge Sarala V. Nagala imposed sanctions.',
                outcome='')
    rec = lag_convert.convert_case(case, 0)
    assert rec['judge'] == 'Judge Sarala V. Nagala'


def test_prose_keeps_lowercase_nobiliary_particle():
    assert lag_convert.extract_judge_prose(
        'Judge Susan van Keulen, and the parties agreed.'
    ) == 'Judge Susan van Keulen'


def test_prose_keeps_accented_name():
    assert lag_convert.extract_judge_prose(
        'Judge José R. Almonte found the citations fabricated.'
    ) == 'Judge José R. Almonte'


def test_prose_keeps_apostrophe_surname():
    assert lag_convert.extract_judge_prose(
        "Justice James d'Auguste granted summary judgment."
    ) == "Judge James d'Auguste"


def test_prose_keeps_mc_mac_internal_capital():
    assert lag_convert.extract_judge_prose('Judge McConnell ruled.') == 'Judge McConnell'
    assert lag_convert.extract_judge_prose('Judge MacDonald held.') == 'Judge MacDonald'
    assert lag_convert.extract_judge_prose(
        'Magistrate Judge Kimberly McEvers issued.') == 'Judge Kimberly McEvers'


def test_prose_keeps_uppercase_apostrophe_surname():
    assert lag_convert.extract_judge_prose("Judge O'Hearn denied.") == "Judge O'Hearn"
    assert lag_convert.extract_judge_prose("Justice D'Angelo ruled.") == "Judge D'Angelo"


def test_prose_drops_trailing_non_name_word():
    assert lag_convert.extract_judge_prose(
        'Judge Smith District ruled.') == 'Judge Smith'


def test_tool_unspecified_when_multiple_named():
    # court listed several tools as examples -> no single attribution
    assert lag_convert.normalize_tool(
        'ChatGPT, Claude, Copilot, DeepSeek, Google Gemini, and Grok') == ''
    assert lag_convert.normalize_tool(
        'named ChatGPT, Microsoft Copilot, and Claude as examples') == ''


def test_tool_single_still_resolves():
    assert lag_convert.normalize_tool('Microsoft Office Copilot') == 'Microsoft Copilot'
    assert lag_convert.normalize_tool('Microsoft Copilot') == 'Microsoft Copilot'


def test_no_false_positive_judge_from_prose():
    case = dict(PIRANI, citation='No citation judge',
                description='The matter was referred to the assigned superior '
                            'court judge for further proceedings.',
                outcome='Counsel was referred to the Justice Department.')
    rec = lag_convert.convert_case(case, 0)
    assert rec['judge'] == ''


# --- summary carries the outcome (final disposition), not just the narrative ---

def test_summary_includes_outcome_disposition():
    rec = lag_convert.convert_case(PIRANI, 0)
    assert 'show cause' in rec['summary']           # the description narrative
    assert '$93,388' in rec['summary']              # the outcome detail
    assert 'awarded to opposing party' in rec['summary']


def test_summary_no_outcome_equals_description():
    case = dict(PIRANI, outcome='')
    rec = lag_convert.convert_case(case, 0)
    assert rec['summary'] == case['description']


def test_summary_does_not_duplicate_outcome_already_in_description():
    case = dict(PIRANI,
                description='Counsel was fined $1,000 for fabricated citations.',
                outcome='$1,000 for fabricated citations.')
    rec = lag_convert.convert_case(case, 0)
    assert rec['summary'].count('$1,000') == 1

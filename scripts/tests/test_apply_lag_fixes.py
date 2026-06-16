import apply_lag_fixes as A
import lag_convert


def _lag(**kw):
    base = {
        'case_name': 'Hatfield v. Pirani',
        'citation': 'Hatfield v. Pirani, No. 5:22-cv-5110 (W.D. Ark.)',
        'court': 'U.S. District Court, Western District of Arkansas',
        'jurisdiction': 'W.D. Ark.', 'date': '2025-12-04', 'ai_tool': 'ChatGPT',
        'sanction_type': 'court_sanction', 'sanction_amount': '$1,000',
        'description': 'Counsel used ChatGPT. Judge Timothy L. Brooks issued an order.',
        'outcome': '$1,000 sanction awarded to opposing party.',
        'source_urls': [], 'primary_source_urls': [],
    }
    base.update(kw)
    return lag_convert.convert_all([base])


def _rec(**kw):
    r = {'source': 'rails', 'name': 'Hatfield v. Pirani', 'judge': '',
         'summary': 'Counsel used ChatGPT.', 'sanction_types': {},
         'date': '2025-12-04', 'state': 'Arkansas'}
    r.update(kw)
    return r


def test_matches_by_docket_in_summary_and_fills_judge():
    lag = _lag(description='Sanctions in No. 5:22-cv-5110. Judge Timothy L. '
                           'Brooks issued an order.')
    rec = _rec(name='', summary='Dispute, No. 5:22-cv-5110, sanctions.')
    A.enrich([rec], lag)
    assert rec['judge'] == 'Judge Timothy L. Brooks'


def test_matches_by_party_name_and_fills_judge():
    rec = _rec()  # name 'Hatfield v. Pirani' matches the LAG party pair
    A.enrich([rec], _lag())
    assert rec['judge'] == 'Judge Timothy L. Brooks'


def test_rails_summary_replaced_with_enriched():
    rec = _rec()
    A.enrich([rec], _lag())
    assert '$1,000 sanction awarded' in rec['summary']


def test_both_source_keeps_rg_summary_but_fills_judge():
    rec = _rec(source='both', summary='Authoritative R&G summary.')
    A.enrich([rec], _lag())
    assert rec['summary'] == 'Authoritative R&G summary.'
    assert rec['judge'] == 'Judge Timothy L. Brooks'


def test_existing_judge_not_overwritten():
    rec = _rec(judge='Judge Existing')
    A.enrich([rec], _lag())
    assert rec['judge'] == 'Judge Existing'


def test_unmatched_record_untouched():
    rec = _rec(name='Unrelated v. Case', summary='Nothing in common.')
    stats = A.enrich([rec], _lag())
    assert stats['matched'] == 0
    assert rec['judge'] == ''
    assert rec['summary'] == 'Nothing in common.'

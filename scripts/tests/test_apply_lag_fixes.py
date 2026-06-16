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


def test_rg_judge_not_overwritten():
    # an R&G-authored judge is authoritative — never replaced by LAG
    rec = _rec(source='both', judge='Judge Existing')
    A.enrich([rec], _lag())
    assert rec['judge'] == 'Judge Existing'


def test_rails_judge_refreshed_from_lag():
    # rails judge is LAG-derived, so a stale/truncated one is re-derived
    rec = _rec(source='rails', judge='Judge Mc')
    A.enrich([rec], _lag())
    assert rec['judge'] == 'Judge Timothy L. Brooks'


def test_ai_tool_corrected_not_just_filled():
    # a stale ai_tool is overwritten from the (re-normalized) LAG value
    rec = _rec(ai_tool='ChatGPT')
    A.enrich([rec], _lag(ai_tool='ChatGPT, Claude, and Gemini'))  # multi -> ''
    assert rec['ai_tool'] == ''


def test_matches_by_name_when_no_docket_or_party():
    lag = _lag(case_name='In re Valencia Sanctions Matter',
               citation='In re Valencia (1st Cir.)',
               description='Sanctions pending.', outcome='', pending=True)
    rec = _rec(name='In re Valencia Sanctions Matter', summary='AI sanctions pending')
    A.enrich([rec], lag)
    assert rec['pending'] is True


def test_pending_carried_from_lag():
    rec = _rec()
    A.enrich([rec], _lag(pending=True))
    assert rec['pending'] is True


def test_slug_tool_last_verified_filled_from_lag():
    rec = _rec()
    A.enrich([rec], _lag(slug='hatfield-v-pirani', ai_tool='ChatGPT',
                         last_verified='2026-05-05'))
    assert rec['slug'] == 'hatfield-v-pirani'
    assert rec['ai_tool'] == 'ChatGPT'
    assert rec['last_verified'] == '2026-05-05'


def test_pending_cleared_when_lag_final():
    rec = _rec(pending=True)
    A.enrich([rec], _lag(pending=False))
    assert rec['pending'] is False


def _two_lag(**common):
    base = dict(court='U.S. District Court, District of Utah', jurisdiction='D. Utah',
                date='2026-04-22', ai_tool='ChatGPT', sanction_type='court_sanction',
                sanction_amount='$1,000', description='Counsel sanctioned.',
                outcome='', source_urls=[], primary_source_urls=[])
    base.update(common)
    return lag_convert.convert_all([
        dict(base, case_name='Alpha LLC v. City of Aville', slug='alpha',
             citation='Alpha LLC v. City of Aville (D. Utah)'),
        dict(base, case_name='Beta LLC v. City of Bville', slug='beta',
             citation='Beta LLC v. City of Bville (D. Utah)'),
    ])


def test_ambiguous_party_key_not_mislinked():
    # two different cases share the generic party key ('llc','city')
    lag = _two_lag()
    rec = _rec(name='Gamma LLC v. City of Cville', summary='no docket here',
               judge='', slug='')
    stats = A.enrich([rec], lag)
    assert stats['matched'] == 0
    assert rec['judge'] == '' and not rec.get('slug')


def test_docket_cross_reference_does_not_mislink():
    # case A's prose cites case B's docket; a record that IS case B must match B,
    # not A, even though docket is tried first.
    common = dict(court='D. Utah', jurisdiction='D. Utah', date='2026-04-22',
                  ai_tool='ChatGPT', sanction_type='court_sanction',
                  sanction_amount='$1,000', source_urls=[], primary_source_urls=[])
    lag = lag_convert.convert_all([
        dict(common, case_name='Wilkes v. Canyons', slug='wilkes',
             citation='Wilkes v. Canyons', description='Related to No. 1:25-cv-00052.',
             outcome=''),
        dict(common, case_name='Moulder v. Davis', slug='moulder',
             citation='Moulder v. Davis', description='Sanctions in No. 1:25-cv-00052.',
             outcome=''),
    ])
    rec = _rec(name='D. Utah – Judge X', summary='In Moulder v. Davis, No. 1:25-cv-00052, counsel sanctioned.',
               slug='', source='both', date='2026-04-22')
    A.enrich([rec], lag)
    assert rec['slug'] == 'moulder'


def test_party_match_respects_date_window():
    lag = lag_convert.convert_all([dict(
        case_name='Smith v. Jones', slug='smith-jones', date='2026-04-22',
        citation='Smith v. Jones (D. Utah)', court='D. Utah', jurisdiction='D. Utah',
        ai_tool='ChatGPT', sanction_type='court_sanction', sanction_amount='$1,000',
        description='Sanctioned. Judge Roe.', outcome='',
        source_urls=[], primary_source_urls=[])])
    # same party pair, different case name, years apart -> not the same case
    rec = _rec(name='Smith v. Jones Holdings', summary='no docket',
               judge='', slug='', date='2020-01-01')
    A.enrich([rec], lag)
    assert rec['judge'] == '' and not rec.get('slug')


def test_unmatched_record_untouched():
    rec = _rec(name='Unrelated v. Case', summary='Nothing in common.')
    stats = A.enrich([rec], _lag())
    assert stats['matched'] == 0
    assert rec['judge'] == ''
    assert rec['summary'] == 'Nothing in common.'


def test_unmatched_record_has_stale_lag_fields_cleared():
    # a record carrying LAG-exclusive data but matching nothing was mis-linked
    # by a prior run; re-running must scrub it.
    rec = _rec(name='Unrelated v. Case', summary='Nothing in common.',
               slug='some-other-case', ai_tool='ChatGPT',
               last_verified='2026-01-01', pending=True)
    A.enrich([rec], _lag())
    assert rec['slug'] == '' and rec['ai_tool'] == ''
    assert rec['last_verified'] == '' and rec['pending'] is False

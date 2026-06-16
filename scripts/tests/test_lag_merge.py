import copy

import lag_merge


def rg(id, date, state, judge, name='RG case', source='rg', **kw):
    base = {
        'id': id, 'name': name, 'judge': judge, 'court': 'Some Court',
        'state': state, 'state_abbr': 'XX', 'date': date, 'type': 'Judicial Opinion',
        'source': source, 'jurisdiction': 'US', 'link': '', 'original_link': '',
        'link_source': 'none', 'ai_type': 'Gen AI', 'applies_to': 'Attorneys',
        'summary': '', 'reqs': {}, 'consequence': None, 'applicableTo': [],
        'sanction_types': {'amount_awarded': None, 'amount_sought': None, 'types': []},
        '_rg_id': 'x',
    }
    base.update(kw)
    return base


def lag(id, date, state, judge, name='LAG case', **kw):
    r = rg(id, date, state, judge, name=name, source='rails', _rg_id=None)
    r.update(kw)
    return r


def test_legacy_key_match_marks_both_and_drops_lag():
    existing = [rg(0, '2026-04-22', 'California', 'Judge Cota')]
    lagrecs = [lag(0, '2026-04-22', 'California', 'Judge Cota')]
    merged, review, stats = lag_merge.merge_lag(existing, lagrecs)
    assert len(merged) == 1
    assert merged[0]['source'] == 'both'
    assert stats['matched_legacy'] == 1 and stats['rails_only'] == 0


def test_pending_propagates_to_matched_record():
    existing = [rg(0, '2026-04-22', 'California', 'Judge Cota')]
    lagrecs = [lag(0, '2026-04-22', 'California', 'Judge Cota', pending=True)]
    merged, _, _ = lag_merge.merge_lag(existing, lagrecs)
    assert merged[0]['source'] == 'both'
    assert merged[0]['pending'] is True


def test_slug_and_tool_fill_matched_record():
    existing = [rg(0, '2026-04-22', 'California', 'Judge Cota')]
    lagrecs = [lag(0, '2026-04-22', 'California', 'Judge Cota',
                   slug='a-v-b', ai_tool='ChatGPT', last_verified='2026-05-01')]
    merged, _, _ = lag_merge.merge_lag(existing, lagrecs)
    assert merged[0]['slug'] == 'a-v-b'
    assert merged[0]['ai_tool'] == 'ChatGPT'
    assert merged[0]['last_verified'] == '2026-05-01'


def test_party_name_match_across_judge_formats():
    existing = [rg(0, '2026-04-22', 'California', 'Judge Jesse M. Furman',
                   name='Geddes v. LoanCare, LLC')]
    lagrecs = [lag(0, '2026-04-20', 'California', 'Judge Cota',
                   name='Krista C. Geddes v. LoanCare')]
    merged, review, stats = lag_merge.merge_lag(existing, lagrecs)
    assert len(merged) == 1
    assert merged[0]['source'] == 'both'
    assert stats['matched_party'] == 1


def test_party_match_rejected_outside_date_window():
    existing = [rg(0, '2024-01-01', 'California', 'Judge X', name='Geddes v. LoanCare')]
    lagrecs = [lag(0, '2026-04-20', 'California', 'Judge Cota', name='Geddes v. LoanCare')]
    merged, review, stats = lag_merge.merge_lag(existing, lagrecs)
    assert len(merged) == 2  # too far apart in time -> not the same case
    assert stats['matched_party'] == 0


def test_docket_match():
    existing = [rg(0, '2026-04-22', 'California', 'Judge X',
                   summary='Order in 2:25-cv-02955 regarding AI use.')]
    lagrecs = [lag(0, '2026-04-22', 'Texas', 'Judge Y', name='A v. B',
                   summary='No. 2:25-cv-02955 sanctions.')]
    merged, review, stats = lag_merge.merge_lag(existing, lagrecs)
    assert len(merged) == 1
    assert stats['matched_docket'] == 1


def test_lag_only_added_as_rails():
    existing = [rg(0, '2026-01-01', 'Texas', 'Judge A')]
    lagrecs = [lag(0, '2026-02-02', 'Nevada', 'Judge B')]
    merged, review, stats = lag_merge.merge_lag(existing, lagrecs)
    assert len(merged) == 2
    assert any(r['source'] == 'rails' for r in merged)
    assert stats['rails_only'] == 1


def test_near_match_flagged_for_review():
    existing = [rg(0, '2026-04-22', 'California', 'Judge Smith')]
    lagrecs = [lag(0, '2026-04-22', 'California', 'Judge Cota')]
    merged, review, stats = lag_merge.merge_lag(existing, lagrecs)
    assert stats['review'] == 1
    assert review[0]['lag_judge'] == 'Judge Cota'
    # still added as rails (not silently merged)
    assert stats['rails_only'] == 1


def test_existing_rails_preserved():
    # LAG cases.json (litigation) must not clobber pre-existing rails standing
    # orders that came from a different source.
    existing = [rg(0, '2026-01-01', 'Texas', 'Judge A'),
                rg(1, '2025-01-01', 'Ohio', 'Judge Old', source='rails',
                   name="Judge's Procedures: AI", type='Standing Order')]
    lagrecs = [lag(0, '2026-02-02', 'Nevada', 'Judge B', name='X v. Y')]
    merged, review, stats = lag_merge.merge_lag(existing, lagrecs)
    assert len(merged) == 3  # rg + preserved rails standing order + new lag
    states = {r['state'] for r in merged}
    assert 'Ohio' in states


def test_gap_fill_only_empty_fields():
    existing = [rg(0, '2026-04-22', 'California', 'Judge Cota', summary='', link='')]
    lagrecs = [lag(0, '2026-04-22', 'California', 'Judge Cota',
                   summary='LAG summary', link='https://x/doc.pdf',
                   original_link='https://x/doc.pdf', link_source='other')]
    merged, _, _ = lag_merge.merge_lag(existing, lagrecs)
    assert merged[0]['summary'] == 'LAG summary'
    assert merged[0]['link'] == 'https://x/doc.pdf'


def test_gap_fill_does_not_overwrite_existing():
    existing = [rg(0, '2026-04-22', 'California', 'Judge Cota', summary='RG truth')]
    lagrecs = [lag(0, '2026-04-22', 'California', 'Judge Cota', summary='LAG summary')]
    merged, _, _ = lag_merge.merge_lag(existing, lagrecs)
    assert merged[0]['summary'] == 'RG truth'


def test_idempotent():
    existing = [rg(0, '2026-04-22', 'California', 'Judge Cota')]
    lagrecs = [lag(0, '2026-04-22', 'California', 'Judge Cota')]
    once, _, _ = lag_merge.merge_lag(copy.deepcopy(existing), copy.deepcopy(lagrecs))
    twice, _, _ = lag_merge.merge_lag(copy.deepcopy(once), copy.deepcopy(lagrecs))
    assert len(once) == len(twice) == 1
    assert twice[0]['source'] == 'both'


def test_summary_surname_match_resolves_dup():
    # R&G name is "Court – Judge" (no parties), but its summary names the case.
    existing = [rg(0, '2026-04-09', 'Louisiana', 'Judge John Kolwe',
                   name='Bankr. W.D. La. – Judge John Kolwe',
                   summary='In re Troylond Malon Wise, the court sanctioned counsel.')]
    lagrecs = [lag(0, '2026-04-09', 'Louisiana', '', name='In re Troylond Malon Wise')]
    merged, review, stats = lag_merge.merge_lag(existing, lagrecs)
    assert len(merged) == 1
    assert merged[0]['source'] == 'both'
    assert stats['matched_summary'] == 1
    assert stats['review'] == 0


def test_summary_match_requires_distinctive_surname():
    # Only generic words shared -> not a match, stays a review near-match.
    existing = [rg(0, '2026-04-09', 'Texas', 'Judge X',
                   name='Court', summary='The State of Texas district court ruled.')]
    lagrecs = [lag(0, '2026-04-09', 'Texas', 'Judge Y', name='State v. County')]
    merged, review, stats = lag_merge.merge_lag(existing, lagrecs)
    assert stats['matched_summary'] == 0
    assert len(merged) == 2


def test_idempotent_rails_add():
    # A LAG case added as rails on run 1 must match itself on run 2 (no dup).
    existing = [rg(0, '2026-01-01', 'Texas', 'Judge A', name='RG thing')]
    lagrecs = [lag(0, '2026-04-22', 'California', 'Judge Cota', name='Geddes v. LoanCare')]
    once, _, _ = lag_merge.merge_lag(copy.deepcopy(existing), copy.deepcopy(lagrecs))
    twice, _, _ = lag_merge.merge_lag(copy.deepcopy(once), copy.deepcopy(lagrecs))
    assert len(once) == len(twice) == 2


def test_counts_reconcile():
    existing = [rg(0, '2026-01-01', 'Texas', 'Judge A')]
    lagrecs = [lag(0, '2026-01-01', 'Texas', 'Judge A'),
               lag(1, '2026-03-03', 'Utah', 'Judge C')]
    merged, _, stats = lag_merge.merge_lag(existing, lagrecs)
    matched = (stats['matched_docket'] + stats['matched_party']
               + stats['matched_legacy'] + stats['matched_summary'])
    assert matched + stats['rails_only'] == stats['lag_total']
    assert len(merged) == stats['existing_total'] + stats['rails_only']

import io
import json
from contextlib import redirect_stdout

import orders_cli as oc


RECS = [
    {'id': 0, 'name': 'D. Mass. – Judge Leo T. Sorokin', 'judge': 'Judge Leo T. Sorokin',
     'court': 'D. Mass.', 'state': 'Massachusetts', 'date': '2026-05-12',
     'type': 'Judicial Opinion', 'consequence': 'sanctions_attorney', 'source': 'rg',
     'ai_type': 'Gen AI', 'applies_to': 'Attorneys', 'jurisdiction': 'US',
     'summary': 'In Shore v. Dorel, the attorney used ChatGPT and Claude with hallucinated citations.',
     'applicableTo': ['Generative AI Usage'], 'pdf': 'https://legalhack.io/orders/rg-1.pdf',
     'link': 'https://www.courtlistener.com/x/'},
    {'id': 1, 'name': 'Standing Order – N.D. Cal.', 'judge': '', 'court': 'N.D. Cal.',
     'state': 'California', 'date': '2025-01-15', 'type': 'Standing Order',
     'consequence': None, 'source': 'rg', 'ai_type': 'Any AI', 'applies_to': 'Attorneys',
     'jurisdiction': 'US', 'summary': 'Disclosure required for AI-assisted filings.',
     'applicableTo': ['Requires Disclosure and/or Verification'], 'pdf': '', 'link': ''},
    {'id': 2, 'name': 'Doe v. Roe', 'judge': 'Judge X', 'court': 'Tex.',
     'state': 'Texas', 'date': '2026-02-01', 'type': 'Judicial Opinion',
     'consequence': 'warning', 'source': 'rails', 'ai_type': 'Gen AI',
     'applies_to': 'Pro Se Litigants', 'jurisdiction': 'US',
     'summary': 'Pro se litigant warned about fabricated cases.',
     'applicableTo': ['Generative AI Usage'], 'pdf': '', 'link': 'https://law.justia.com/y'},
]


def test_search_and_tokens():
    assert {r['id'] for r in oc.search(RECS, 'chatgpt hallucinated')} == {0}
    assert {r['id'] for r in oc.search(RECS, 'disclosure')} == {1}
    assert len(oc.search(RECS, '')) == 3


def test_filter_exact_and_date():
    f = {'state': 'California'}
    assert {r['id'] for r in oc.apply_filters(RECS, f)} == {1}
    f = {'date_from': '2026-01-01'}
    assert {r['id'] for r in oc.apply_filters(RECS, f)} == {0, 2}
    f = {'consequence': 'sanctions_attorney'}
    assert {r['id'] for r in oc.apply_filters(RECS, f)} == {0}


def test_filter_has_pdf_and_tag():
    assert {r['id'] for r in oc.apply_filters(RECS, {'has_pdf': True})} == {0}
    assert {r['id'] for r in oc.apply_filters(RECS, {'tag': 'Disclosure'})} == {1}


def test_facet_counts():
    f = oc.facet(RECS, 'type')
    assert {x['value']: x['count'] for x in f} == {'Judicial Opinion': 2, 'Standing Order': 1}


def test_facet_list_field():
    f = oc.facet(RECS, 'applicableTo')
    assert {x['value']: x['count'] for x in f}['Generative AI Usage'] == 2


def test_stats():
    s = oc.stats(RECS)
    assert s['total'] == 3
    assert s['with_pdf'] == 1
    assert s['date_range'] == ['2025-01-15', '2026-05-12']


def test_get_command(monkeypatch):
    monkeypatch.setattr(oc, 'load_orders', lambda: RECS)
    buf = io.StringIO()
    with redirect_stdout(buf):
        oc.main(['get', '2'])
    assert json.loads(buf.getvalue())['name'] == 'Doe v. Roe'


def test_search_command_json_projection(monkeypatch):
    monkeypatch.setattr(oc, 'load_orders', lambda: RECS)
    buf = io.StringIO()
    with redirect_stdout(buf):
        oc.main(['search', 'chatgpt'])
    out = json.loads(buf.getvalue())
    assert len(out) == 1 and out[0]['id'] == 0
    assert set(out[0].keys()) == set(oc._LIST_FIELDS)


def test_pdf_command(monkeypatch):
    monkeypatch.setattr(oc, 'load_orders', lambda: RECS)
    buf = io.StringIO()
    with redirect_stdout(buf):
        oc.main(['pdf', '0'])
    assert json.loads(buf.getvalue())['pdf'] == 'https://legalhack.io/orders/rg-1.pdf'


def test_get_missing_exits(monkeypatch):
    import pytest
    monkeypatch.setattr(oc, 'load_orders', lambda: RECS)
    with pytest.raises(SystemExit) as e:
        oc.main(['get', '999'])
    assert e.value.code == 3


def test_court_match_alias_and_substring():
    long = 'U.S. District Court, Southern District of New York'
    assert oc.court_match(long, 'S.D.N.Y.')        # alias unifies the two spellings
    assert oc.court_match('S.D.N.Y.', 'sdny')      # abbreviation alias
    assert oc.court_match('Supreme Court of Montana', 'Montana')  # substring
    assert not oc.court_match('N.D. Cal.', 'S.D.N.Y.')
    # bankruptcy court for the same district must NOT match the district filter
    assert not oc.court_match('U.S. Bankruptcy Court, Southern District of New York', 'S.D.N.Y.')
    assert not oc.court_match('Bankr. S.D.N.Y.', 'sdny')   # abbreviated form must not leak either
    assert not oc.court_match('2d Cir.', 'sdny')
    assert oc.court_match('Bankr. S.D.N.Y.', 'bankr')      # but a bankruptcy query still matches


def test_filter_court_unifies_spellings():
    recs = [
        {'id': 1, 'court': 'S.D.N.Y.', 'name': 'A'},
        {'id': 2, 'court': 'U.S. District Court, Southern District of New York', 'name': 'B'},
        {'id': 3, 'court': 'N.D. Cal.', 'name': 'C'},
    ]
    got = {r['id'] for r in oc.apply_filters(recs, {'court': 'S.D.N.Y.'})}
    assert got == {1, 2}   # both SDNY spellings, not the N.D. Cal. record


def test_judge_match_title_insensitive():
    assert oc.judge_match('Chief Judge Pamela Pepper', 'Judge Pamela Pepper')
    assert oc.judge_match('Magistrate Judge Anthony P. Patti', 'Anthony P. Patti')
    assert oc.judge_match('Judge Nina Y. Wang', 'Wang')
    assert not oc.judge_match('Judge Nina Y. Wang', 'Castel')
    assert not oc.judge_match('', 'Wang')          # empty judge must not match anything
    assert not oc.judge_match('All Judges', 'Wang')


def test_applies_to_matches_multivalue():
    assert oc.applies_match('Attorneys,Pro Se Litigants', 'Attorneys')
    assert oc.applies_match('Attorneys,Pro Se Litigants', 'Pro Se Litigants')
    assert not oc.applies_match('Any Parties', 'Attorneys')


def test_filter_judge_and_applies_to():
    recs = [
        {'id': 1, 'judge': 'Chief Judge Pamela Pepper', 'applies_to': 'Attorneys,Pro Se Litigants'},
        {'id': 2, 'judge': 'Judge Other Person', 'applies_to': 'Any Parties'},
    ]
    assert {r['id'] for r in oc.apply_filters(recs, {'judge': 'Pamela Pepper'})} == {1}
    assert {r['id'] for r in oc.apply_filters(recs, {'applies_to': 'Attorneys'})} == {1}


def test_facet_excludes_placeholders_by_default():
    recs = [{'judge': 'All Judges'}, {'judge': 'Judge X'}, {'judge': 'Judge X'}, {'judge': ''}]
    default = {f['value']: f['count'] for f in oc.facet(recs, 'judge')}
    assert default == {'Judge X': 2}                 # "All Judges" + empty dropped
    allv = {f['value']: f['count'] for f in oc.facet(recs, 'judge', include_all=True)}
    assert allv.get('All Judges') == 1


def test_count_flag(monkeypatch, capsys):
    import json as _json
    monkeypatch.setattr(oc, 'load_orders', lambda: RECS)
    oc.main(['search', '', '--state', 'California', '--count'])
    out = _json.loads(capsys.readouterr().out)
    assert out == {'count': 1}


def test_bar_filter(monkeypatch):
    monkeypatch.setattr(oc, 'load_bar', lambda: {'items': [
        {'name': 'California', 'abbreviation': 'CA', 'status': 'formal'},
        {'name': 'Texas', 'abbreviation': 'TX', 'status': 'none'}]})
    buf = io.StringIO()
    with redirect_stdout(buf):
        oc.main(['bar', 'California'])
    out = json.loads(buf.getvalue())
    assert len(out) == 1 and out[0]['abbreviation'] == 'CA'

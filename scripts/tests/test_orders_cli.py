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


def test_filter_pending_and_final():
    recs = [dict(RECS[0], id=0, pending=False),
            dict(RECS[0], id=1, pending=True)]
    assert {r['id'] for r in oc.apply_filters(recs, {'pending': True})} == {1}
    assert {r['id'] for r in oc.apply_filters(recs, {'final': True})} == {0}


def test_final_filter_treats_missing_pending_as_final():
    # records without a pending key (legacy) count as final, not proposed
    assert {r['id'] for r in oc.apply_filters(RECS, {'final': True})} == {0, 1, 2}
    assert oc.apply_filters(RECS, {'pending': True}) == []


def test_projection_includes_pending():
    assert 'pending' in oc._project(dict(RECS[0], pending=True))


def test_filter_by_ai_tool():
    recs = [dict(RECS[0], id=0, ai_tool='ChatGPT'),
            dict(RECS[0], id=1, ai_tool='Claude'),
            dict(RECS[0], id=2, ai_tool='')]
    assert {r['id'] for r in oc.apply_filters(recs, {'ai_tool': 'chatgpt'})} == {0}
    assert {r['id'] for r in oc.apply_filters(recs, {'ai_tool': 'Claude'})} == {1}


def test_projection_includes_slug_and_ai_tool():
    p = oc._project(dict(RECS[0], slug='doe-v-roe', ai_tool='ChatGPT'))
    assert p['slug'] == 'doe-v-roe' and p['ai_tool'] == 'ChatGPT'


def test_get_by_slug(monkeypatch):
    recs = [dict(RECS[0], id=7, slug='shore-v-dorel')]
    monkeypatch.setattr(oc, 'load_orders', lambda: recs)
    buf = io.StringIO()
    with redirect_stdout(buf):
        oc.main(['get', 'shore-v-dorel'])
    assert json.loads(buf.getvalue())['slug'] == 'shore-v-dorel'


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


def test_data_unavailable_exits_cleanly(monkeypatch, capsys):
    import pytest

    def boom(name):
        raise oc.DataUnavailable(f"no data for {name}")

    monkeypatch.setattr(oc, '_fetch_json', boom)
    with pytest.raises(SystemExit) as e:
        oc.main(['stats'])
    assert e.value.code == 4
    assert 'error:' in capsys.readouterr().err


def test_fetch_json_raises_dataunavailable_when_offline(monkeypatch, tmp_path):
    import pytest

    def fail_open(*a, **k):
        raise OSError('offline')

    monkeypatch.setattr(oc.urllib.request, 'urlopen', fail_open)
    monkeypatch.setattr(oc, '_LOCAL_DIR', str(tmp_path))
    with pytest.raises(oc.DataUnavailable):
        oc._fetch_json('explorer_data.json')


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


REQ_RECS = [
    {'id': 0, 'court': 'N.D. Cal.', 'type': 'Standing Order',
     'reqs': {'disclose': True}, 'name': 'A'},
    {'id': 1, 'court': 'N.D. Cal.', 'type': 'Standing Order',
     'reqs': {'disclose': False}, 'name': 'B'},
    {'id': 2, 'court': 'S.D.N.Y.', 'type': 'Judicial Opinion',
     'reqs': {'rules': 'FRCP 11'}, 'name': 'C'},
    {'id': 3, 'court': 'D. Mass.', 'type': 'Standing Order',
     'reqs': {}, 'name': 'D'},
    {'id': 4, 'court': 'D. Mass.', 'type': 'Standing Order', 'name': 'E'},  # no reqs key
]


def test_requires_truthy_only():
    assert {r['id'] for r in oc.apply_filters(REQ_RECS, {'requires': 'disclose'})} == {0}


def test_requires_string_value_is_truthy():
    assert {r['id'] for r in oc.apply_filters(REQ_RECS, {'requires': 'rules'})} == {2}


def test_requires_unknown_key_and_missing_reqs():
    assert oc.apply_filters(REQ_RECS, {'requires': 'nonexistent'}) == []
    # record 4 has no reqs key at all — must not raise
    assert {r['id'] for r in oc.apply_filters(REQ_RECS, {'requires': 'disclose'})} == {0}


def test_requires_composes_with_other_filters():
    f = {'type': 'Standing Order', 'requires': 'disclose'}
    assert {r['id'] for r in oc.apply_filters(REQ_RECS, f)} == {0}


def test_facets_filter_aware_helper():
    recs = oc.apply_filters(REQ_RECS, {'requires': 'disclose'})
    counts = {x['value']: x['count'] for x in oc.facet(recs, 'court')}
    assert counts == {'N.D. Cal.': 1}


def test_facets_command_respects_filters(monkeypatch):
    monkeypatch.setattr(oc, 'load_orders', lambda: RECS)
    buf = io.StringIO()
    with redirect_stdout(buf):
        oc.main(['facets', 'court', '--consequence', 'sanctions_attorney'])
    out = {x['value']: x['count'] for x in json.loads(buf.getvalue())}
    assert out == {'D. Mass.': 1}


def test_facets_command_unfiltered_regression(monkeypatch):
    monkeypatch.setattr(oc, 'load_orders', lambda: RECS)
    buf = io.StringIO()
    with redirect_stdout(buf):
        oc.main(['facets', 'type'])
    out = {x['value']: x['count'] for x in json.loads(buf.getvalue())}
    assert out == {'Judicial Opinion': 2, 'Standing Order': 1}


def test_parser_builds_without_arg_collision():
    # facets gains filter flags but keeps its own --limit/--all — must not raise
    oc.build_parser()


def test_summary_in_projection_and_table(monkeypatch):
    assert 'summary' in oc._LIST_FIELDS
    monkeypatch.setattr(oc, 'load_orders', lambda: RECS)
    # JSON keeps full summary
    buf = io.StringIO()
    with redirect_stdout(buf):
        oc.main(['search', 'chatgpt'])
    assert json.loads(buf.getvalue())[0]['summary'].startswith('In Shore v. Dorel')
    # table shows a truncated summary line
    buf = io.StringIO()
    with redirect_stdout(buf):
        oc.main(['search', 'chatgpt', '--format', 'table'])
    table = buf.getvalue()
    assert 'In Shore v. Dorel' in table


def test_table_no_summary_line_when_empty():
    buf = io.StringIO()
    with redirect_stdout(buf):
        oc._print_table([{'id': 9, 'date': '2026-01-01', 'state': 'X', 'type': 'Standing Order',
                          'consequence': None, 'name': 'No summary here', 'summary': ''}])
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    assert any('No summary here' in ln for ln in lines)
    assert len(lines) == 2  # header line + name line, no summary line


def test_facets_table_branch_unaffected():
    buf = io.StringIO()
    with redirect_stdout(buf):
        oc._print_table([{'value': 'N.D. Cal.', 'count': 9}])
    assert buf.getvalue().strip() == '9  N.D. Cal.'


def test_bar_filter(monkeypatch):
    monkeypatch.setattr(oc, 'load_bar', lambda: {'items': [
        {'name': 'California', 'abbreviation': 'CA', 'status': 'formal'},
        {'name': 'Texas', 'abbreviation': 'TX', 'status': 'none'}]})
    buf = io.StringIO()
    with redirect_stdout(buf):
        oc.main(['bar', 'California'])
    out = json.loads(buf.getvalue())
    assert len(out) == 1 and out[0]['abbreviation'] == 'CA'

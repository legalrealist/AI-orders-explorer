import copy
import json
import os

import cleanup
import schema


def raw_record():
    return {
        'id': 0,
        'name': 'Test', 'judge': 'Chief Justice Cory James Swanson',
        'court': 'Supreme Court of Montana', 'state': 'Montana', 'state_abbr': 'MT',
        'date': '2026-05-08', 'type': 'Judicial Opinion', 'source': 'rg',
        'link': 'https://www.courtlistener.com/opinion/1/x/',
        'ai_type': 'Gen AI', 'applies_to': 'Attorneys', 'summary': 's',
        'reqs': {'disclose': 'checked'}, 'consequence': '', 'applicableTo': [],
        'jurisdiction': 'US', '_rg_id': 'rg-1',
    }


SRC = [{
    'id': 'rg-1', 'state': 'Montana', 'judge': ['Chief Justice Cory James Swanson'],
    'effectiveDate': '2026-05-08T00:00:00Z',
    'linkToCourtOrder': {'url': 'https://advance.lexis.com/permalink/AAA/'},
}]


def test_offline_clean_validates():
    recs, problems, stats = cleanup.clean([raw_record()], SRC, do_http=False)
    assert problems == []
    assert recs[0]['original_link'] == 'https://advance.lexis.com/permalink/AAA/'
    assert recs[0]['reqs'] == {'disclose': True}
    assert recs[0]['consequence'] is None


def test_clean_idempotent():
    once, _, _ = cleanup.clean([raw_record()], SRC, do_http=False)
    twice, _, _ = cleanup.clean(copy.deepcopy(once), SRC, do_http=False)
    assert once == twice


def test_invalid_record_reports_problem():
    bad = raw_record()
    bad['id'] = 'not-an-int'
    _, problems, _ = cleanup.clean([bad], SRC, do_http=False)
    assert any('id must be int' in p for p in problems)


def test_http_prune_falls_back(monkeypatch):
    import urllib.error

    def fetch(u):
        raise urllib.error.HTTPError(u, 404, 'gone', {}, None)

    recs, problems, stats = cleanup.clean([raw_record()], SRC, do_http=True, fetch=fetch, cache={})
    assert problems == []
    assert recs[0]['link'] == 'https://advance.lexis.com/permalink/AAA/'
    assert recs[0]['link_source'] == 'lexis'
    assert stats['linkcheck']['pruned'] == 1


def test_write_outputs_mirror_byte_identical(tmp_path):
    recs, _, _ = cleanup.clean([raw_record()], SRC, do_http=False)
    a = tmp_path / 'a.json'
    b = tmp_path / 'sub' / 'b.json'
    cleanup.write_outputs(recs, [str(a), str(b)])
    assert a.read_bytes() == b.read_bytes()
    assert schema.validate_dataset(json.loads(a.read_text())) == []

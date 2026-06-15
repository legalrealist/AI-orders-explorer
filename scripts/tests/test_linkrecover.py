import linkrecover


SRC = [
    {
        'id': 'rg-1',
        'state': 'Montana',
        'judge': ['Chief Justice Cory James Swanson'],
        'effectiveDate': '2026-05-08T00:00:00Z',
        'linkToCourtOrder': {'url': 'https://advance.lexis.com/permalink/AAA/'},
    },
    {
        'id': 'rg-2',
        'state': 'New York',
        'judge': ['Judge Jesse M. Furman'],
        'effectiveDate': '2025-06-01T00:00:00Z',
        'linkToCourtOrder': {'url': 'https://advance.lexis.com/permalink/BBB/'},
    },
]


def test_classify_link_source():
    cases = {
        'https://www.courtlistener.com/opinion/1/x/': 'courtlistener',
        'https://advance.lexis.com/permalink/AAA/': 'lexis',
        'https://1.next.westlaw.com/Document/x': 'westlaw',
        'https://law.justia.com/cases/x': 'justia',
        'https://www.govinfo.gov/app/x': 'govinfo',
        'https://www.ropesgray.com/en/sites/x': 'ropesgray',
        'https://example.com/x': 'other',
        '': 'none',
    }
    for url, expected in cases.items():
        assert linkrecover.classify_link_source(url) == expected


def test_recover_by_rg_id():
    rec = {'_rg_id': 'rg-1', 'date': '2026-05-08', 'state': 'Montana',
           'judge': 'Chief Justice Cory James Swanson',
           'link': 'https://www.courtlistener.com/opinion/1/x/'}
    linkrecover.recover([rec], SRC)
    assert rec['original_link'] == 'https://advance.lexis.com/permalink/AAA/'
    assert rec['link_source'] == 'courtlistener'


def test_recover_by_date_state_judge_when_no_rg_id():
    # No _rg_id; judge differs by title prefix only.
    rec = {'_rg_id': None, 'date': '2025-06-01', 'state': 'New York',
           'judge': 'Jesse M. Furman',
           'link': 'https://www.courtlistener.com/opinion/2/y/'}
    linkrecover.recover([rec], SRC)
    assert rec['original_link'] == 'https://advance.lexis.com/permalink/BBB/'


def test_lexis_link_preserved_when_no_source_match():
    rec = {'_rg_id': None, 'date': '2024-01-01', 'state': 'Texas',
           'judge': 'Unknown Person',
           'link': 'https://advance.lexis.com/permalink/ZZZ/'}
    linkrecover.recover([rec], SRC)
    assert rec['original_link'] == 'https://advance.lexis.com/permalink/ZZZ/'
    assert rec['link_source'] == 'lexis'


def test_rails_record_no_match_gets_empty_original():
    rec = {'_rg_id': None, 'date': '2024-01-01', 'state': 'Texas',
           'judge': 'Unknown Person',
           'link': 'https://legalaigovernance.com/tracker/cases/x/'}
    linkrecover.recover([rec], SRC)
    assert rec['original_link'] == ''
    assert rec['link_source'] == 'other'


def test_norm_judge_strips_titles():
    assert linkrecover._norm_judge('Chief Magistrate Judge William Matthewman') == \
        linkrecover._norm_judge('William Matthewman')


def test_link_source_values_are_in_schema_enum():
    for url in ('https://www.courtlistener.com/x', '', 'https://x.gov'):
        assert linkrecover.classify_link_source(url) in schema_link_sources()


def schema_link_sources():
    import schema
    return schema.LINK_SOURCES

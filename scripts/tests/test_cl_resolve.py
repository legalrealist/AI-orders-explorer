import urllib.error

import cl_resolve


def make_fetch(routes):
    """routes: dict path-substring -> response dict (or callable raising)."""
    def fetch(path):
        for key, val in routes.items():
            if key in path:
                if callable(val):
                    return val(path)
                return val
        raise urllib.error.HTTPError(path, 404, 'nf', {}, None)
    return fetch


def test_storage_url():
    assert cl_resolve.storage_url('recap/x/1.pdf') == 'https://storage.courtlistener.com/recap/x/1.pdf'
    assert cl_resolve.storage_url('') == ''


def test_case_matches_strict():
    rec = {'name': 'Geddes v. LoanCare', 'summary': ''}
    assert cl_resolve.case_matches(rec, 'Geddes v. LoanCare, LLC')   # both parties
    assert not cl_resolve.case_matches(rec, 'Geddes v. Smith')       # only one party
    assert not cl_resolve.case_matches(rec, 'Jones v. Anderson')     # neither


def test_opinion_link_verified():
    rec = {'link': 'https://www.courtlistener.com/opinion/555/x/',
           'name': 'Geddes v. LoanCare', 'summary': ''}
    fetch = make_fetch({
        '/opinions/555/': {'local_path': 'recap/y/2.pdf',
                           'cluster': 'https://x/api/rest/v4/clusters/9/'},
        '/clusters/9/': {'case_name': 'Geddes v. LoanCare, LLC'},
    })
    url, method, cname = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url.endswith('recap/y/2.pdf') and method == 'opinion'
    assert cname == 'Geddes v. LoanCare, LLC'


def test_docket_chain_verified():
    rec = {'link': 'https://www.courtlistener.com/docket/63/coomer-v-lindell/',
           'name': 'Coomer v. Lindell', 'summary': ''}
    fetch = make_fetch({
        '/dockets/63/': {'case_name': 'Coomer v. Lindell',
                         'clusters': ['https://x/api/rest/v4/clusters/10/']},
        '/clusters/10/': {'case_name': 'Coomer v. Lindell',
                          'sub_opinions': ['https://x/api/rest/v4/opinions/77/']},
        '/opinions/77/': {'local_path': 'recap/z/3.pdf'},
    })
    url, method, cname = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url.endswith('recap/z/3.pdf') and method == 'docket'


def test_wrong_case_docket_rejected_then_search():
    # The record's docket link resolves to the WRONG case; verification rejects
    # it and a verified search finds the right one.
    rec = {'link': 'https://www.courtlistener.com/docket/1/wrong/',
           'name': 'Geddes v. LoanCare', 'summary': ''}
    fetch = make_fetch({
        '/dockets/1/': {'case_name': 'Unrelated v. Party',
                        'clusters': ['https://x/api/rest/v4/clusters/2/']},
        '/clusters/2/': {'case_name': 'Unrelated v. Party',
                         'sub_opinions': ['https://x/api/rest/v4/opinions/3/']},
        '/opinions/3/': {'local_path': 'recap/wrong.pdf'},
        '/search/': {'results': [{'caseName': 'Geddes v. LoanCare, LLC', 'cluster_id': 99}]},
        '/clusters/99/': {'case_name': 'Geddes v. LoanCare, LLC',
                          'sub_opinions': ['https://x/api/rest/v4/opinions/88/']},
        '/opinions/88/': {'local_path': 'recap/right.pdf'},
    })
    url, method, cname = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url.endswith('recap/right.pdf') and method == 'search'
    assert cname == 'Geddes v. LoanCare, LLC'


def test_search_verified_match():
    rec = {'link': 'https://law.justia.com/x', 'name': 'Shore v. Dorel Juvenile', 'summary': ''}
    fetch = make_fetch({
        '/search/': {'results': [{'caseName': 'Shore v. Dorel Juvenile Group', 'cluster_id': 5}]},
        '/clusters/5/': {'case_name': 'Shore v. Dorel Juvenile Group',
                         'sub_opinions': ['https://x/opinions/6/']},
        '/opinions/6/': {'local_path': 'recap/s/4.pdf'},
    })
    url, method, cname = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url.endswith('recap/s/4.pdf') and method == 'search'


def test_date_mismatch_rejects_then_finds_right_ruling():
    # Same case has two rulings; the record's date picks the right document.
    rec = {'link': 'https://www.courtlistener.com/docket/1/x/',
           'name': 'Geddes v. LoanCare', 'summary': '', 'date': '2026-04-22'}
    fetch = make_fetch({
        '/dockets/1/': {'clusters': ['https://x/api/rest/v4/clusters/2/']},
        '/clusters/2/': {'case_name': 'Geddes v. LoanCare, LLC', 'date_filed': '2024-01-01',
                         'sub_opinions': ['https://x/opinions/3/']},   # right case, WRONG date
        '/opinions/3/': {'local_path': 'recap/wrongdate.pdf'},
        '/search/': {'results': [{'caseName': 'Geddes v. LoanCare, LLC', 'cluster_id': 9}]},
        '/clusters/9/': {'case_name': 'Geddes v. LoanCare, LLC', 'date_filed': '2026-04-20',
                         'sub_opinions': ['https://x/opinions/8/']},   # right case + date
        '/opinions/8/': {'local_path': 'recap/rightdate.pdf'},
    })
    url, method, cname = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url.endswith('recap/rightdate.pdf') and method == 'search'


def test_ai_content_disambiguates_same_day_rulings():
    # Same case, same date, two rulings; pick the one whose text is about AI.
    rec = {'link': 'https://www.courtlistener.com/docket/1/x/',
           'name': 'Smith v. Jones', 'summary': '', 'date': '2026-03-01'}
    fetch = make_fetch({
        '/dockets/1/': {'clusters': ['https://x/api/rest/v4/clusters/A/',
                                     'https://x/api/rest/v4/clusters/B/']},
        '/clusters/A/': {'case_name': 'Smith v. Jones', 'date_filed': '2026-03-01',
                         'sub_opinions': ['https://x/opinions/10/']},
        '/opinions/10/': {'local_path': 'recap/scheduling.pdf',
                          'plain_text': 'Order setting a status conference next month.'},
        '/clusters/B/': {'case_name': 'Smith v. Jones', 'date_filed': '2026-03-01',
                         'sub_opinions': ['https://x/opinions/11/']},
        '/opinions/11/': {'local_path': 'recap/ai_sanctions.pdf',
                          'plain_text': 'Counsel cited nonexistent cases produced by '
                                        'ChatGPT, a generative artificial intelligence tool.'},
    })
    url, method, cname = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url.endswith('recap/ai_sanctions.pdf') and method == 'docket'


def test_ai_score():
    assert cl_resolve._ai_score('used ChatGPT and generative AI to hallucinate citations') >= 3
    assert cl_resolve._ai_score('a routine scheduling order') == 0


def test_date_close():
    assert cl_resolve._date_close('2026-04-22', '2026-04-20')      # within window
    assert not cl_resolve._date_close('2026-04-22', '2024-01-01')  # different ruling
    assert cl_resolve._date_close('2026-04', '2026-04-30')         # month precision
    assert not cl_resolve._date_close('2026-04', '2026-06-01')
    assert cl_resolve._date_close('2026-04-22', '')                # missing -> allow


def test_search_rejects_wrong_case():
    rec = {'link': 'https://law.justia.com/x', 'name': 'Shore v. Dorel', 'summary': ''}
    fetch = make_fetch({
        '/search/': {'results': [{'caseName': 'Maddox v. Wexford Health', 'cluster_id': 1}]},
        '/clusters/1/': {'sub_opinions': ['https://x/opinions/2/']},
        '/opinions/2/': {'local_path': 'recap/wrong.pdf'},
    })
    url, method, cname = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url == '' and method == ''


def test_summary_search_for_rg_record():
    # R&G record: name is "Court – Judge"; case lives in the summary.
    rec = {'link': 'https://advance.lexis.com/x',
           'name': 'D. Mass. – Judge Leo T. Sorokin',
           'summary': 'In Shore v. Dorel, the attorney used hallucinated citations.'}
    fetch = make_fetch({
        '/search/': {'results': [{'caseName': 'Shore v. Dorel Juvenile Group', 'cluster_id': 7}]},
        '/clusters/7/': {'case_name': 'Shore v. Dorel Juvenile Group',
                         'sub_opinions': ['https://x/opinions/8/']},
        '/opinions/8/': {'local_path': 'recap/rg.pdf'},
    })
    url, method, cname = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url.endswith('recap/rg.pdf') and method == 'search'


def test_no_local_path_returns_empty():
    rec = {'link': 'https://www.courtlistener.com/opinion/7/x/',
           'name': 'Geddes v. LoanCare', 'summary': ''}
    fetch = make_fetch({'/opinions/7/': {'local_path': None, 'cluster': ''},
                        '/search/': {'results': []}})
    url, method, cname = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url == '' and method == ''


def test_search_query_from_name_or_summary():
    assert cl_resolve.search_query({'name': 'Geddes v. LoanCare', 'summary': ''}) == 'Geddes v. LoanCare'
    rec = {'name': 'D. Mass. – Judge Leo T. Sorokin',
           'summary': 'In Shore v. Dorel Juvenile Grp., the attorney ...'}
    assert cl_resolve.search_query(rec) == 'Shore v. Dorel'
    assert cl_resolve.search_query({'name': 'Standing Order', 'summary': 'no case here'}) == ''

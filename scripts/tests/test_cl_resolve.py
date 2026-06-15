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


def test_opinion_link_direct():
    rec = {'link': 'https://www.courtlistener.com/opinion/555/x/', 'name': 'A v. B', 'summary': ''}
    fetch = make_fetch({'/opinions/555/': {'local_path': 'recap/y/2.pdf'}})
    url, method = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url.endswith('recap/y/2.pdf') and method == 'opinion'


def test_docket_chain():
    rec = {'link': 'https://www.courtlistener.com/docket/63/coomer-v-lindell/',
           'name': 'Coomer v. Lindell', 'summary': ''}
    fetch = make_fetch({
        '/dockets/63/': {'clusters': ['https://x/api/rest/v4/clusters/10/']},
        '/clusters/10/': {'sub_opinions': ['https://x/api/rest/v4/opinions/77/']},
        '/opinions/77/': {'local_path': 'recap/z/3.pdf'},
    })
    url, method = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url.endswith('recap/z/3.pdf') and method == 'docket'


def test_search_verified_match():
    rec = {'link': 'https://law.justia.com/x', 'name': 'Shore v. Dorel Juvenile', 'summary': ''}
    fetch = make_fetch({
        '/search/': {'results': [{'caseName': 'Shore v. Dorel Juvenile Group', 'cluster_id': 99}]},
        '/clusters/99/': {'sub_opinions': ['https://x/opinions/88/']},
        '/opinions/88/': {'local_path': 'recap/s/4.pdf'},
    })
    url, method = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url.endswith('recap/s/4.pdf') and method == 'search'


def test_search_rejects_wrong_case():
    rec = {'link': 'https://law.justia.com/x', 'name': 'Shore v. Dorel', 'summary': ''}
    fetch = make_fetch({
        '/search/': {'results': [{'caseName': 'Maddox v. Wexford Health', 'cluster_id': 1}]},
        '/clusters/1/': {'sub_opinions': ['https://x/opinions/2/']},
        '/opinions/2/': {'local_path': 'recap/wrong.pdf'},
    })
    url, method = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url == ''  # name mismatch -> not used


def test_opinion_404_falls_through_to_search():
    rec = {'link': 'https://www.courtlistener.com/opinion/999/x/',
           'name': 'Real Case Here', 'summary': ''}
    fetch = make_fetch({
        '/opinions/999/': lambda p: (_ for _ in ()).throw(urllib.error.HTTPError(p, 404, 'nf', {}, None)),
        '/search/': {'results': [{'caseName': 'Real Case Here', 'cluster_id': 5}]},
        '/clusters/5/': {'sub_opinions': ['https://x/opinions/6/']},
        '/opinions/6/': {'local_path': 'recap/found.pdf'},
    })
    url, method = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url.endswith('recap/found.pdf') and method == 'search'


def test_no_local_path_returns_empty():
    rec = {'link': 'https://www.courtlistener.com/opinion/7/x/', 'name': 'X', 'summary': ''}
    fetch = make_fetch({'/opinions/7/': {'local_path': None}, '/search/': {'results': []}})
    url, method = cl_resolve.resolve_pdf_url(rec, fetch)
    assert url == '' and method == ''


def test_name_matches():
    rec = {'name': 'Geddes v. LoanCare', 'summary': ''}
    assert cl_resolve.name_matches(rec, 'Krista Geddes v. LoanCare LLC')
    assert not cl_resolve.name_matches(rec, 'Smith v. Jones')

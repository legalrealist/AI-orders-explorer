import urllib.error

import linkcheck


def cl_record(link, original='https://advance.lexis.com/permalink/X/'):
    return {'link': link, 'original_link': original, 'link_source': 'courtlistener'}


def test_ok_link_unchanged():
    rec = cl_record('https://www.courtlistener.com/opinion/1/x/')
    fetch = lambda u: (200, '<html>real opinion text</html>')
    stats = linkcheck.validate_links([rec], fetch=fetch)
    assert rec['link'] == 'https://www.courtlistener.com/opinion/1/x/'
    assert rec['link_source'] == 'courtlistener'
    assert stats['ok'] == 1 and stats['pruned'] == 0


def test_404_falls_back_to_lexis():
    rec = cl_record('https://www.courtlistener.com/opinion/bad/')

    def fetch(u):
        raise urllib.error.HTTPError(u, 404, 'Not Found', {}, None)

    linkcheck.validate_links([rec], fetch=fetch)
    assert rec['link'] == 'https://advance.lexis.com/permalink/X/'
    assert rec['link_source'] == 'lexis'


def test_empty_search_page_is_broken():
    rec = cl_record('https://www.courtlistener.com/?q=nothing')
    fetch = lambda u: (200, '<html>Your search had no results.</html>')
    linkcheck.validate_links([rec], fetch=fetch)
    assert rec['link'] == 'https://advance.lexis.com/permalink/X/'
    assert rec['link_source'] == 'lexis'


def test_broken_with_no_original_blanks_link():
    rec = cl_record('https://www.courtlistener.com/opinion/bad/', original='')

    def fetch(u):
        raise urllib.error.HTTPError(u, 404, 'Not Found', {}, None)

    linkcheck.validate_links([rec], fetch=fetch)
    assert rec['link'] == ''
    assert rec['link_source'] == 'none'


def test_cache_short_circuits_fetcher():
    calls = []

    def fetch(u):
        calls.append(u)
        return (200, 'real text')

    cache = {}
    rec1 = cl_record('https://www.courtlistener.com/opinion/1/x/')
    rec2 = cl_record('https://www.courtlistener.com/opinion/1/x/')
    linkcheck.validate_links([rec1], fetch=fetch, cache=cache)
    linkcheck.validate_links([rec2], fetch=fetch, cache=cache)
    assert len(calls) == 1  # second run served from cache


def test_non_cl_links_never_fetched():
    calls = []

    def fetch(u):
        calls.append(u)
        return (200, 'x')

    rec = {'link': 'https://law.justia.com/x', 'original_link': '', 'link_source': 'justia'}
    linkcheck.validate_links([rec], fetch=fetch)
    assert calls == []


def test_403_block_not_pruned():
    rec = cl_record('https://www.courtlistener.com/docket/1/x/')

    def fetch(u):
        raise urllib.error.HTTPError(u, 403, 'Forbidden', {}, None)

    stats = linkcheck.validate_links([rec], fetch=fetch)
    assert rec['link'] == 'https://www.courtlistener.com/docket/1/x/'
    assert stats['error'] == 1 and stats['pruned'] == 0


def test_410_gone_is_pruned():
    rec = cl_record('https://www.courtlistener.com/docket/1/x/')

    def fetch(u):
        raise urllib.error.HTTPError(u, 410, 'Gone', {}, None)

    linkcheck.validate_links([rec], fetch=fetch)
    assert rec['link'] == 'https://advance.lexis.com/permalink/X/'


def test_500_not_pruned():
    rec = cl_record('https://www.courtlistener.com/docket/1/x/')
    fetch = lambda u: (503, 'maintenance')
    stats = linkcheck.validate_links([rec], fetch=fetch)
    assert rec['link'] == 'https://www.courtlistener.com/docket/1/x/'
    assert stats['pruned'] == 0


def test_network_error_leaves_link_unchanged():
    rec = cl_record('https://www.courtlistener.com/opinion/1/x/')

    def fetch(u):
        raise ConnectionError('boom')

    stats = linkcheck.validate_links([rec], fetch=fetch)
    assert rec['link'] == 'https://www.courtlistener.com/opinion/1/x/'
    assert stats['error'] == 1 and stats['pruned'] == 0

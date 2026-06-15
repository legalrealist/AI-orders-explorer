import urllib.error

import link_verify


def cl(name, link, summary='', original='https://advance.lexis.com/permalink/X/'):
    return {'id': 1, 'name': name, 'summary': summary, 'link': link,
            'original_link': original, 'link_source': 'courtlistener'}


def test_slug_matches_record_is_trust():
    rec = cl('Coomer v. Lindell', 'https://www.courtlistener.com/docket/63296393/coomer-v-lindell/')
    assert link_verify.offline_classify(rec) == 'trust'


def test_wrong_case_slug_is_suspicious():
    rec = cl('Gouveia v. Meridian Fin.',
             'https://www.courtlistener.com/docket/1/gleason-v-marcus-canvassing-board/',
             summary='In Gouveia v. Meridian Fin., LLC ...')
    assert link_verify.offline_classify(rec) == 'suspicious'


def test_recap_pdf_is_trusted():
    rec = cl('Nora v. M & A Transport',
             'https://storage.courtlistener.com/recap/gov.uscourts.x/123.pdf')
    assert link_verify.offline_classify(rec) == 'trust'


def test_storage_pdf_filename_slug_checked():
    rec = cl('Williamson v. TransUnion',
             'https://storage.courtlistener.com/pdf/2026/05/04/eliott_williamson_v._transunion_llc.pdf')
    assert link_verify.offline_classify(rec) == 'trust'


def test_search_url_classified_search():
    rec = cl('Holmes v. UT Austin', 'https://www.courtlistener.com/docket/?q=Holmes+v.+UT')
    assert link_verify.offline_classify(rec) == 'search'


def test_resolve_suspicious_api_confirms_keeps_link():
    rec = cl('Shaporov v. PIPPD',
             'https://www.courtlistener.com/docket/63130422/shaparov-v-state/',
             summary='Shaporov v. PIPPD ...')
    # offline flags suspicious (shaparov vs shaporov); API confirms by case_name
    fetch = lambda t, i: {'case_name': 'Shaporov v. PIPPD'}
    stats, report = link_verify.resolve([rec], api_fetch=fetch)
    assert stats['api_confirmed'] == 1
    assert rec['link'].endswith('shaparov-v-state/')
    assert report == []


def test_resolve_suspicious_api_rejects_falls_back_to_lexis():
    rec = cl('Gouveia v. Meridian',
             'https://www.courtlistener.com/docket/1/gleason-v-marcus/',
             summary='Gouveia v. Meridian Fin.')
    fetch = lambda t, i: {'case_name': 'Gleason v. Marcus'}
    stats, report = link_verify.resolve([rec], api_fetch=fetch)
    assert rec['link'] == 'https://advance.lexis.com/permalink/X/'
    assert rec['link_source'] == 'lexis'
    assert report[0]['action'] == 'fallback_lexis'


def test_resolve_api_404_falls_back():
    rec = cl('Vanished Matter', 'https://www.courtlistener.com/docket/999/totally-other-thing/',
             summary='Vanished Matter v. Nobody')

    def fetch(t, i):
        raise urllib.error.HTTPError('u', 404, 'nf', {}, None)

    stats, report = link_verify.resolve([rec], api_fetch=fetch)
    assert rec['link_source'] == 'lexis'
    assert stats['api_rejected'] == 1


def test_no_fallback_blanks_and_flags():
    rec = cl('Mbow v. Mackert', 'https://www.courtlistener.com/docket/?q=Mbow',
             original='https://www.courtlistener.com/docket/?q=Mbow')  # CL original, no lexis
    stats, report = link_verify.resolve([rec])  # search -> no api needed
    assert rec['link'] == ''
    assert rec['link_source'] == 'none'
    assert report[0]['action'] == 'blanked'


def test_search_falls_back_to_lexis_when_available():
    rec = cl('Ringer v. BofA', 'https://www.courtlistener.com/docket/?q=Ringer')
    stats, report = link_verify.resolve([rec])
    assert rec['link_source'] == 'lexis'
    assert report[0]['action'] == 'fallback_lexis'


def test_non_cl_links_untouched():
    rec = {'link': 'https://law.justia.com/x', 'link_source': 'justia',
           'original_link': '', 'name': 'X', 'summary': ''}
    stats, report = link_verify.resolve([rec])
    assert rec['link'] == 'https://law.justia.com/x'
    assert report == []


def test_api_error_keeps_and_flags():
    rec = cl('Some Case', 'https://www.courtlistener.com/docket/5/other-slug/',
             summary='Some Case here')

    def fetch(t, i):
        raise ConnectionError('boom')

    stats, report = link_verify.resolve([rec], api_fetch=fetch)
    assert rec['link'].endswith('other-slug/')  # unchanged
    assert stats['api_error'] == 1
    assert report[0]['action'] == 'unverified_kept'

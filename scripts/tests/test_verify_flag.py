import normalize


def _rec(**kw):
    base = {'judge': '', 'type': 'Standing Order', 'link': '', 'pdf': ''}
    base.update(kw)
    return base


def test_self_hosted_pdf_is_verified():
    recs = [_rec(pdf='https://legalhack.io/orders/c-1.pdf', link='')]
    normalize.mark_unverified(recs)
    assert recs[0]['unverified'] is False


def test_tracker_page_is_unverified():
    recs = [_rec(link='https://www.ropesgray.com/en/sites/artificial-intelligence-court-order-tracker/states/new-york')]
    normalize.mark_unverified(recs)
    assert recs[0]['unverified'] is True


def test_confirmed_sources_are_not_flagged():
    for link in ['https://www.cand.uscourts.gov/judges/foo/',
                 'https://www.courtlistener.com/docket/123/x/',
                 'https://www.govinfo.gov/content/x.pdf',
                 'https://example.com/order.pdf']:
        recs = [_rec(link=link)]
        normalize.mark_unverified(recs)
        assert recs[0]['unverified'] is False, link


def test_unfetchable_external_sources_are_flagged():
    # real-looking but unconfirmable / paywalled -> kept, but flagged
    for link in ['https://law.justia.com/cases/kansas/court-of-appeals/2026/1.html',
                 'https://advance.lexis.com/api/permalink/abc/',
                 'https://caselaw.findlaw.com/x.html']:
        recs = [_rec(link=link)]
        normalize.mark_unverified(recs)
        assert recs[0]['unverified'] is True, link


def test_confirmed_mismatch_flagged_despite_court_link():
    # Walton: link is an official court page, but the document was checked and
    # does not support the summary, so it must be flagged regardless.
    recs = [_rec(judge='Judge Reggie B. Walton', type='Standing Order',
                 link='https://www.dcd.uscourts.gov/district-judge-reggie-b-waltons-court-webpage')]
    normalize.mark_unverified(recs)
    assert recs[0]['unverified'] is True


def test_normalize_injects_default_false():
    rec = {'reqs': {}, 'sanction_types': {}}
    normalize.normalize_record(rec)
    assert rec['unverified'] is False

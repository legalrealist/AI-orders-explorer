import os

import pdf_archive


PDF_BYTES = b'%PDF-1.7\n...content...\n%%EOF'


def rec(**kw):
    base = {'_rg_id': None, 'court': 'D. Mass.', 'date': '2026-05-12',
            'name': 'Shore v. Dorel', 'link': '', 'original_link': '', 'pdf': ''}
    base.update(kw)
    return base


def test_stable_key_uses_rg_id():
    r = rec(_rg_id='27cb2ca5-e806-4a8f-9491-176c6e50b891')
    assert pdf_archive.stable_key(r).startswith('rg-')
    # stable across calls
    assert pdf_archive.stable_key(r) == pdf_archive.stable_key(dict(r))


def test_stable_key_hash_when_no_rg_id():
    k = pdf_archive.stable_key(rec())
    assert k.startswith('c-') and len(k) == 14


def test_is_direct_pdf():
    assert pdf_archive.is_direct_pdf('https://x/doc.PDF')
    assert pdf_archive.is_direct_pdf('https://storage.courtlistener.com/recap/x/1.pdf')
    assert not pdf_archive.is_direct_pdf('https://www.courtlistener.com/docket/1/x/')
    assert not pdf_archive.is_direct_pdf('https://law.justia.com/x')


def test_direct_pdf_url_prefers_original():
    r = rec(original_link='https://x/orig.pdf', link='https://x/page')
    assert pdf_archive.direct_pdf_url(r) == 'https://x/orig.pdf'


def test_direct_pdf_url_from_lag_source():
    r = rec(name='Doe v. Roe')
    idx = {'Doe v. Roe': {'primary_source_urls': [], 'source_urls': ['https://s3/doe.pdf']}}
    assert pdf_archive.direct_pdf_url(r, idx) == 'https://s3/doe.pdf'


def test_download_pdf_writes_real_pdf(tmp_path):
    dest = str(tmp_path / 'x.pdf')
    ok, sha1, n, err = pdf_archive.download_pdf('http://x/a.pdf', dest, fetch=lambda u: PDF_BYTES)
    assert ok and n == len(PDF_BYTES) and os.path.exists(dest)


def test_download_pdf_rejects_non_pdf(tmp_path):
    dest = str(tmp_path / 'x.pdf')
    ok, _, _, err = pdf_archive.download_pdf('http://x/a.pdf', dest, fetch=lambda u: b'<html>403</html>')
    assert not ok and 'not a PDF' in err
    assert not os.path.exists(dest)


def test_archive_sets_pdf_and_manifest(tmp_path):
    recs = [rec(original_link='https://x/a.pdf'),
            rec(name='No PDF here', link='https://law.justia.com/x')]
    stats, manifest = pdf_archive.archive(recs, str(tmp_path), fetch=lambda u: PDF_BYTES)
    assert stats['downloaded'] == 1 and stats['skipped_no_pdf'] == 1
    assert recs[0]['pdf'].startswith('https://legalhack.io/orders/')
    assert recs[1]['pdf'] == ''
    assert manifest[0]['sha1']


def test_archive_idempotent_reuses_file(tmp_path):
    recs = [rec(original_link='https://x/a.pdf')]
    pdf_archive.archive(recs, str(tmp_path), fetch=lambda u: PDF_BYTES)
    calls = []
    pdf_archive.archive(recs, str(tmp_path), fetch=lambda u: calls.append(u) or PDF_BYTES)
    assert calls == []  # second run reused the existing file


def test_text_is_challenge():
    assert pdf_archive.text_is_challenge('Just a moment... Verifying you are human. Cloudflare Ray ID 8x')
    assert pdf_archive.text_is_challenge('Please enable JavaScript and cookies to continue')
    assert not pdf_archive.text_is_challenge('IT IS HEREBY ORDERED that counsel shall verify all citations.')


def test_download_pdf_rejects_challenge_page(tmp_path, monkeypatch):
    dest = str(tmp_path / 'x.pdf')
    monkeypatch.setattr(pdf_archive, 'is_challenge_pdf', lambda p: True)
    ok, _, _, err = pdf_archive.download_pdf('http://x/a.pdf', dest, fetch=lambda u: PDF_BYTES)
    assert not ok and 'challenge' in err
    assert not os.path.exists(dest)


def test_archive_failed_download_leaves_pdf_empty(tmp_path):
    recs = [rec(original_link='https://x/a.pdf')]

    def boom(u):
        raise ConnectionError('down')

    stats, manifest = pdf_archive.archive(recs, str(tmp_path), fetch=boom)
    assert stats['failed'] == 1
    assert recs[0]['pdf'] == ''
    assert manifest[0]['error']

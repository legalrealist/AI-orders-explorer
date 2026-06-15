import linkrecover
import normalize
import schema
import update


def rg_item(rid='rg-9', url='https://advance.lexis.com/permalink/NEW/'):
    return {
        'id': rid,
        'state': 'New York',
        'court': ['New York - Supreme Court, Kings County'],
        'judge': ['Judge Aaron D. Maslow'],
        'effectiveDate': '2026-03-01T00:00:00Z',
        'applicableTo': ['Requires Disclosure and/or Verification'],
        'summary': 'In re Something v. Other, the court ...',
        'linkToCourtOrder': {'url': url, 'text': 'NY|Kings County'},
    }


SRC = [rg_item()]


def test_new_entry_recovers_original_and_validates():
    item = rg_item()
    entry = update.fallback_convert_entry(item, 0)
    entry['_rg_id'] = item.get('id')
    # link starts as the lexis source url; simulate post-conversion state
    linkrecover.recover([entry], SRC)
    normalize.normalize([entry])
    assert schema.validate_record(entry) == []
    assert entry['original_link'] == 'https://advance.lexis.com/permalink/NEW/'
    assert entry['link_source'] in schema.LINK_SOURCES


def test_lexis_preserved_after_cl_replacement(monkeypatch):
    # Build an entry whose link is a Lexis url, then run replace_lexis_links
    # with a stubbed CL lookup; original_link must survive the replacement.
    item = rg_item()
    entry = update.fallback_convert_entry(item, 0)
    entry['_rg_id'] = item.get('id')
    linkrecover.recover([entry], SRC)  # sets original_link = lexis
    assert entry['original_link'] == 'https://advance.lexis.com/permalink/NEW/'

    monkeypatch.setattr(update, 'CL_API_KEY', 'fake')
    monkeypatch.setattr(update, 'CL_DELAY', 0)
    monkeypatch.setattr(update, 'cl_search_link',
                        lambda *a, **k: 'https://www.courtlistener.com/opinion/9/x/')
    update.replace_lexis_links([entry])

    assert entry['link'] == 'https://www.courtlistener.com/opinion/9/x/'
    assert entry['original_link'] == 'https://advance.lexis.com/permalink/NEW/'
    # reclassification happens on the durability recover pass
    linkrecover.recover([entry], SRC)
    assert entry['link_source'] == 'courtlistener'


def test_entry_with_no_source_link_gets_empty_original():
    item = rg_item(url='')
    entry = update.fallback_convert_entry(item, 0)
    entry['_rg_id'] = item.get('id')
    linkrecover.recover([entry], [])  # no source match
    normalize.normalize([entry])
    assert entry['original_link'] == ''
    assert entry['link_source'] == 'none'
    assert schema.validate_record(entry) == []


def test_replace_lexis_links_skips_without_key(monkeypatch):
    # Characterization: with no CL_API_KEY, links are left as-is.
    monkeypatch.setattr(update, 'CL_API_KEY', '')
    entry = {'link': 'https://advance.lexis.com/permalink/NEW/', 'name': 'x'}
    update.replace_lexis_links([entry])
    assert entry['link'] == 'https://advance.lexis.com/permalink/NEW/'

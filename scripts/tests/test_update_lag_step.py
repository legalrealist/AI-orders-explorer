"""Integration test for the LAG ingestion step wired into the pipeline.

Mirrors update.py main()'s Step 5b + save chain (fetch -> convert -> merge ->
recover -> normalize -> validate) without the live R&G/OpenRouter calls.
"""

import lag_cases
import lag_convert
import lag_merge
import linkrecover
import normalize
import schema


RG_SOURCE = []  # no R&G source needed; existing R&G already carry provenance


def existing_rg():
    return [{
        'id': 0, 'name': 'Geddes v. LoanCare, LLC', 'judge': 'Judge Jesse M. Furman',
        'court': 'E.D. Cal.', 'state': 'California', 'state_abbr': 'CA',
        'date': '2026-04-22', 'type': 'Judicial Opinion', 'source': 'rg',
        'jurisdiction': 'US', 'link': 'https://www.courtlistener.com/opinion/1/x/',
        'original_link': 'https://advance.lexis.com/permalink/AAA/', 'link_source': 'courtlistener',
        'ai_type': 'Gen AI', 'applies_to': 'Attorneys', 'summary': 'Geddes v. LoanCare ...',
        'reqs': {}, 'consequence': 'sanctions_attorney', 'applicableTo': [],
        'sanction_types': {'amount_awarded': None, 'amount_sought': None, 'types': []},
        '_rg_id': 'rg-1',
    }]


LAG_ENVELOPE = {
    'schema_version': 1, 'last_modified': '2026-05-15', 'count': 2,
    'items': [
        {  # should match the R&G record by party name
            'case_name': 'Krista C. Geddes v. LoanCare', 'court': 'U.S. District Court, Eastern District of California',
            'jurisdiction': 'E.D. Cal.', 'date': '2026-04-22', 'ai_tool': 'generative AI',
            'sanction_type': 'court_sanction', 'sanction_amount': '$1,000', 'pending': False,
            'citation': 'Geddes v. LoanCare (E.D. Cal. 2026) (Cota, Mag. J.)',
            'outcome': '$1,000', 'description': 'attorney misquoted authority',
            'source_urls': ['https://x.s3.amazonaws.com/geddes.pdf'], 'primary_source_urls': [],
            'url': 'https://legalaigovernance.com/tracker/cases/geddes/',
        },
        {  # genuinely new -> rails
            'case_name': 'Doe v. Roe', 'court': 'Supreme Court of Texas',
            'jurisdiction': 'Tex.', 'date': '2026-05-01', 'ai_tool': 'ChatGPT',
            'sanction_type': 'warning', 'sanction_amount': None, 'pending': False,
            'citation': 'Doe v. Roe (Tex. 2026)', 'outcome': 'warning', 'description': 'warned',
            'source_urls': ['https://law.justia.com/doe.html'], 'primary_source_urls': [],
            'url': 'https://legalaigovernance.com/tracker/cases/doe-v-roe/',
        },
    ],
}


def run_chain(existing, lag_env, rg_source):
    lag_recs = lag_convert.convert_all(lag_cases.items(lag_env))
    merged, review, stats = lag_merge.merge_lag(existing, lag_recs)
    linkrecover.recover(merged, rg_source)
    normalize.normalize(merged)
    return merged, review, stats


def test_lag_step_merges_and_validates():
    merged, review, stats = run_chain(existing_rg(), LAG_ENVELOPE, RG_SOURCE)
    assert schema.validate_dataset(merged) == []
    sources = {r['source'] for r in merged}
    assert 'both' in sources and 'rails' in sources
    # the Geddes LAG case folded into the R&G record (party match)
    assert stats['matched_party'] == 1
    assert stats['rails_only'] == 1


def test_rails_record_keeps_lag_provenance_after_recover():
    merged, _, _ = run_chain(existing_rg(), LAG_ENVELOPE, RG_SOURCE)
    doe = next(r for r in merged if r['name'] == 'Doe v. Roe')
    assert doe['source'] == 'rails'
    assert doe['original_link'] == 'https://law.justia.com/doe.html'
    assert doe['link_source'] == 'justia'


def test_rg_record_provenance_preserved():
    merged, _, _ = run_chain(existing_rg(), LAG_ENVELOPE, RG_SOURCE)
    geddes = next(r for r in merged if r['source'] == 'both')
    # original Lexis link still present; CL display link untouched
    assert geddes['original_link'] == 'https://advance.lexis.com/permalink/AAA/'
    assert geddes['link'] == 'https://www.courtlistener.com/opinion/1/x/'


def test_lag_fetch_failure_raises_for_caller_to_catch():
    import pytest

    def boom(url):
        raise ConnectionError('down')

    with pytest.raises(ConnectionError):
        lag_cases.fetch_cases(fetch_json=boom)

import archive_lag_direct as ald


CASES = [
    {'case_name': 'Geddes v. LoanCare, LLC', 'date': '2026-04-22',
     'primary_source_urls': [], 'source_urls': ['https://s3/geddes.pdf']},
    {'case_name': 'Shore v. Dorel Juvenile Group', 'date': '2026-05-12',
     'primary_source_urls': ['https://damiencharlotin.com/shore.pdf'], 'source_urls': []},
]


def test_match_by_exact_name():
    by_name, by_party = ald.build_indexes(CASES)
    rec = {'name': 'Geddes v. LoanCare, LLC', 'date': '2026-04-22', 'summary': ''}
    assert ald.match_lag_case(rec, by_name, by_party)['source_urls'] == ['https://s3/geddes.pdf']


def test_match_by_parties_and_date_window():
    by_name, by_party = ald.build_indexes(CASES)
    # R&G-style name; case identity is in the summary; date within window
    rec = {'name': 'D. Mass. – Judge Leo T. Sorokin', 'date': '2026-05-20',
           'summary': 'In Shore v. Dorel, the attorney ...'}
    c = ald.match_lag_case(rec, by_name, by_party)
    assert c and c['case_name'] == 'Shore v. Dorel Juvenile Group'


def test_no_match_outside_date_window():
    by_name, by_party = ald.build_indexes(CASES)
    rec = {'name': 'Shore v. Dorel', 'date': '2020-01-01', 'summary': ''}
    assert ald.match_lag_case(rec, by_name, by_party) is None


def test_no_match_no_parties():
    by_name, by_party = ald.build_indexes(CASES)
    rec = {'name': 'Standing Order', 'date': '2026-01-01', 'summary': 'no case'}
    assert ald.match_lag_case(rec, by_name, by_party) is None


def test_candidate_urls_primary_first():
    assert ald.candidate_urls(CASES[1]) == ['https://damiencharlotin.com/shore.pdf']
    assert ald.candidate_urls(CASES[0]) == ['https://s3/geddes.pdf']

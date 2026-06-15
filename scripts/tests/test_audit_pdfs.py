import audit_pdfs


def test_audit_flags_mismatch_passes_match():
    records = [
        {'pdf': 'https://x/a.pdf', 'name': 'Geddes v. LoanCare', 'summary': ''},
        {'pdf': 'https://x/b.pdf', 'name': 'Shore v. Dorel', 'summary': ''},
        {'pdf': 'https://x/c.pdf', 'name': 'Court – Judge', 'summary': ''},  # tier-1, no matched_case
    ]
    manifest = [
        {'pdf': 'https://x/a.pdf', 'matched_case': 'Geddes v. LoanCare, LLC'},   # correct
        {'pdf': 'https://x/b.pdf', 'matched_case': 'Smith v. Jones'},            # WRONG case
        {'pdf': 'https://x/c.pdf'},                                              # tier-1, skipped
    ]
    searched, mismatches = audit_pdfs.audit(records, manifest)
    assert len(searched) == 2
    assert len(mismatches) == 1
    assert mismatches[0][0] == 'Shore v. Dorel'


def test_audit_empty_manifest():
    searched, mismatches = audit_pdfs.audit([{'pdf': 'x', 'name': 'A v. B'}], [])
    assert searched == [] and mismatches == []

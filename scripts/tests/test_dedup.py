import dedup


def _rec(**kw):
    base = {'id': 0, 'judge': '', 'court': '', 'type': 'Standing Order',
            'summary': '', 'source': 'rg', 'date': '', 'link': '',
            'original_link': '', 'pdf': '', 'reqs': {}, 'applicableTo': []}
    base.update(kw)
    return base


def test_merges_same_order_from_two_feeds():
    recs = [
        _rec(id=1, judge='Judge A', court='D. Foo', summary='Order text.',
             source='rg', date='2025-06', original_link='https://lexis/x', pdf=''),
        _rec(id=2, judge='Chief Judge A', court='D. Foo', summary='Order text.',
             source='rails', date='2025-06-15', original_link='', pdf='https://h/a.pdf'),
    ]
    new, stats = dedup.merge_duplicates(recs)
    assert stats == {'groups': 1, 'removed': 1}
    assert len(new) == 1
    kept = new[0]
    assert kept['source'] == 'both'
    assert kept['pdf'] == 'https://h/a.pdf'          # absorbed from drop
    assert kept['original_link'] == 'https://lexis/x'  # kept from keep
    assert kept['date'] == '2025-06-15'                # prefers full-precision date


def test_does_not_merge_distinct_opinions_same_case():
    recs = [
        _rec(id=1, type='Judicial Opinion', judge='Judge B', court='S.D.N.Y.',
             summary='In X v. Y, the court sanctioned counsel on Nov 26.', date='2025-11-26'),
        _rec(id=2, type='Judicial Opinion', judge='Judge B', court='S.D.N.Y.',
             summary='In X v. Y, the court struck the filing on Sep 25.', date='2025-09-25'),
    ]
    new, stats = dedup.merge_duplicates(recs)
    assert stats['removed'] == 0
    assert len(new) == 2


def test_civil_and_criminal_orders_stay_separate():
    recs = [
        _rec(id=1, judge='Judge C', court='S.D. Ohio', summary='AI standing order.',
             link='https://c/Standing%20Civil%20Order.pdf'),
        _rec(id=2, judge='Judge C', court='S.D. Ohio', summary='AI standing order.',
             link='https://c/Standing%20Criminal%20Order.pdf'),
    ]
    new, stats = dedup.merge_duplicates(recs)
    assert stats['removed'] == 0
    assert len(new) == 2


def test_unions_requirement_flags():
    recs = [
        _rec(id=1, judge='Judge D', court='D. Bar', summary='same', reqs={'disclose': True}),
        _rec(id=2, judge='Judge D', court='D. Bar', summary='same', reqs={'certify': True}),
    ]
    new, _ = dedup.merge_duplicates(recs)
    assert new[0]['reqs'] == {'disclose': True, 'certify': True}

import json

import pytest

import lag_cases


ENVELOPE = {
    'schema_version': 1,
    'last_modified': '2026-05-14',
    'count': 2,
    'items': [{'slug': 'a'}, {'slug': 'b'}],
}


def test_fetch_validates_and_returns_items():
    data = lag_cases.fetch_cases(fetch_json=lambda u: ENVELOPE)
    assert lag_cases.items(data) == ENVELOPE['items']


def test_missing_schema_version_raises():
    bad = {'items': []}
    with pytest.raises(ValueError):
        lag_cases.fetch_cases(fetch_json=lambda u: bad)


def test_missing_items_raises():
    bad = {'schema_version': 1}
    with pytest.raises(ValueError):
        lag_cases.fetch_cases(fetch_json=lambda u: bad)


def test_is_newer_by_last_modified():
    older = {'last_modified': '2026-05-01', 'items': [], 'schema_version': 1}
    newer = {'last_modified': '2026-05-14', 'items': [], 'schema_version': 1}
    assert lag_cases.is_newer(newer, older) is True
    assert lag_cases.is_newer(older, newer) is False
    assert lag_cases.is_newer(newer, None) is True


def test_save_and_load_roundtrip(tmp_path):
    p = tmp_path / 'lag.json'
    lag_cases.save_cached(ENVELOPE, str(p))
    loaded = lag_cases.load_cached(str(p))
    assert loaded == ENVELOPE


def test_load_missing_returns_none(tmp_path):
    assert lag_cases.load_cached(str(tmp_path / 'nope.json')) is None

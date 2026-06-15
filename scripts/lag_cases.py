"""Fetch and cache the LegalAIGovernance (LAG/RAILS) court-order tracker.

LAG publishes its court-order cases as a versioned JSON envelope at
https://legalaigovernance.com/data/cases.json (schema_version / last_modified /
count / items), mirroring the already-automated opinions.json feed. This module
fetches it, validates the envelope, and caches the raw response.

The fetcher is injectable so tests never touch the network.
"""

import json
import os
import ssl
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CACHE_PATH = os.path.join(PROJECT_DIR, 'data', 'sources', 'lag_cases.json')

CASES_URL = 'https://legalaigovernance.com/data/cases.json'
_USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'
)


def _ssl_ctx():
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except ImportError:
        pass
    return ctx


SSL_CTX = _ssl_ctx()


def default_fetch_json(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _validate_envelope(data):
    if not isinstance(data, dict):
        raise ValueError('LAG cases: response is not a JSON object')
    if 'schema_version' not in data:
        raise ValueError('LAG cases: missing schema_version')
    if not isinstance(data.get('items'), list):
        raise ValueError('LAG cases: missing or invalid items array')
    return data


def fetch_cases(fetch_json=default_fetch_json):
    """Fetch the cases envelope from LAG and validate its shape."""
    return _validate_envelope(fetch_json(CASES_URL))


def items(data):
    return data.get('items', []) if isinstance(data, dict) else []


def last_modified(data):
    return (data or {}).get('last_modified') if isinstance(data, dict) else None


def is_newer(remote, cached):
    """True if remote should replace cached (by last_modified, else always)."""
    if not cached:
        return True
    rm, cm = last_modified(remote), last_modified(cached)
    if rm and cm:
        return rm > cm
    return True


def load_cached(path=CACHE_PATH):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return None


def save_cached(data, path=CACHE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

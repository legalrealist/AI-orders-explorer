"""Validate CourtListener links over HTTP and prune broken ones.

For every record whose `link` is a CourtListener URL, fetch it. A 4xx/5xx
response or a 200 that renders CourtListener's empty-result page is treated as
broken: the record's `link` falls back to its `original_link` (the recovered
Lexis/source URL), and `link_source` is reclassified.

The fetcher is injectable so tests never touch the network. Transient network
errors are reported as 'error' and leave the link unchanged (no destructive
pruning on a blip).
"""

import ssl
import time
import urllib.error
import urllib.request

import linkrecover

OK = 'ok'
BROKEN = 'broken'
ERROR = 'error'

# Browser User-Agent — CourtListener (Cloudflare) returns 403 to non-browser
# agents, which would otherwise be indistinguishable from a dead link.
_USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'
)
# Status codes that mean the resource is genuinely gone (prune-worthy).
_BROKEN_STATUS = {404, 410}
# Markers CourtListener renders on a zero-result search page.
_EMPTY_MARKERS = (
    'had no results',
    'no results found',
    'returned no results',
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


def default_fetch(url, timeout=15):
    """Return (status_code, body_text). Raises on network failure."""
    req = urllib.request.Request(url, method='GET', headers={'User-Agent': _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
        body = resp.read(20000).decode('utf-8', 'replace')
        return resp.status, body


def is_empty_result(body):
    low = (body or '').lower()
    return any(m in low for m in _EMPTY_MARKERS)


def check_url(url, fetch=default_fetch):
    """Return OK / BROKEN / ERROR for a single URL."""
    try:
        status, body = fetch(url)
    except urllib.error.HTTPError as e:
        # Only definitively-gone statuses prune. 403/429/5xx are access or
        # transient blocks (CourtListener Cloudflare), not dead links.
        return BROKEN if e.code in _BROKEN_STATUS else ERROR
    except Exception:
        return ERROR
    if status in _BROKEN_STATUS:
        return BROKEN
    if status >= 400:
        return ERROR
    if status == 200 and is_empty_result(body):
        return BROKEN
    return OK


def validate_links(records, fetch=default_fetch, cache=None, rate_limit=0.0):
    """Check CourtListener links; prune broken ones to original_link.

    `cache` maps url -> OK/BROKEN/ERROR and is updated in place. Returns a stats
    dict.
    """
    if cache is None:
        cache = {}
    stats = {'checked': 0, 'ok': 0, 'broken': 0, 'error': 0, 'cached': 0, 'pruned': 0}

    for rec in records:
        if rec.get('link_source') != 'courtlistener':
            continue
        url = rec.get('link', '')
        if not url:
            continue

        if url in cache:
            result = cache[url]
            stats['cached'] += 1
        else:
            result = check_url(url, fetch)
            # Errors are transient (network/block) — do not cache them, so a
            # later run re-checks instead of treating the blip as permanent.
            if result != ERROR:
                cache[url] = result
            stats['checked'] += 1
            if rate_limit:
                time.sleep(rate_limit)

        stats[result] = stats.get(result, 0) + 1

        if result == BROKEN:
            fallback = rec.get('original_link', '') or ''
            rec['link'] = fallback
            rec['link_source'] = linkrecover.classify_link_source(fallback)
            stats['pruned'] += 1

    return stats

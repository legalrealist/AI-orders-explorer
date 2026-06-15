#!/usr/bin/env python3
"""Agent-facing CLI for the AI Court Orders dataset.

Query 900+ U.S. court standing orders, local rules, and judicial decisions about
AI use in legal filings. JSON output by default so agents can parse results;
`--format table` for humans.

Data is fetched from legalhack.io (override with ORDERS_DATA_BASE) and falls back
to the local repo copy when offline.

Examples:
    orders search "hallucinated citations" --consequence sanctions_attorney
    orders list --state California --type "Standing Order" --limit 5
    orders get 42
    orders facets judge --limit 10
    orders stats
    orders bar California
    orders pdf 42
"""

import argparse
import json
import os
import sys
import urllib.request

DATA_BASE = os.environ.get('ORDERS_DATA_BASE', 'https://legalhack.io/data')
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCAL_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), 'data', 'processed')
_UA = 'ai-court-orders-cli/1.0'

# Filter flag -> record field (exact match, case-insensitive).
_EXACT = {
    'judge': 'judge', 'court': 'court', 'state': 'state', 'type': 'type',
    'consequence': 'consequence', 'ai_type': 'ai_type', 'applies_to': 'applies_to',
    'source': 'source', 'jurisdiction': 'jurisdiction',
}


def _fetch_json(name):
    """Load a dataset file: remote first, local fallback."""
    url = f'{DATA_BASE}/{name}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': _UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception:
        path = os.path.join(_LOCAL_DIR, name)
        with open(path, encoding='utf-8') as f:
            return json.load(f)


def load_orders():
    return _fetch_json('explorer_data.json')


def load_bar():
    return _fetch_json('bar_opinions.json')


# --- pure query helpers (unit-tested) ---

def _norm(s):
    return (s or '').lower()


def search(records, query):
    """AND-match query tokens across name, summary, judge, court."""
    if not query:
        return list(records)
    tokens = [t for t in _norm(query).replace('.', '').split() if t]
    out = []
    for r in records:
        blob = _norm(' '.join([
            r.get('name', ''), r.get('summary', ''),
            r.get('judge', ''), r.get('court', ''),
        ])).replace('.', '')
        if all(t in blob for t in tokens):
            out.append(r)
    return out


def apply_filters(records, filters):
    """filters: dict of flag->value. Handles exact, date range, has_* booleans, tag."""
    out = []
    for r in records:
        ok = True
        for flag, field in _EXACT.items():
            v = filters.get(flag)
            if v and _norm(r.get(field)) != _norm(v):
                ok = False
                break
        if not ok:
            continue
        df, dt = filters.get('date_from'), filters.get('date_to')
        d = r.get('date', '') or ''
        if df and d < df:
            continue
        if dt and d > dt:
            continue
        if filters.get('has_pdf') and not r.get('pdf'):
            continue
        if filters.get('has_link') and not r.get('link'):
            continue
        tag = filters.get('tag')
        if tag and not any(_norm(tag) in _norm(t) for t in (r.get('applicableTo') or [])):
            continue
        out.append(r)
    return out


def facet(records, field, limit=None):
    counts = {}
    for r in records:
        v = r.get(field)
        if isinstance(v, list):
            for x in v:
                counts[x] = counts.get(x, 0) + 1
        elif v:
            counts[v] = counts.get(v, 0) + 1
    items = sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0])))
    if limit:
        items = items[:limit]
    return [{'value': k, 'count': c} for k, c in items]


def stats(records):
    return {
        'total': len(records),
        'by_type': {f['value']: f['count'] for f in facet(records, 'type')},
        'by_consequence': {f['value']: f['count'] for f in facet(records, 'consequence')},
        'by_source': {f['value']: f['count'] for f in facet(records, 'source')},
        'with_pdf': sum(1 for r in records if r.get('pdf')),
        'with_link': sum(1 for r in records if r.get('link')),
        'date_range': [
            min((r['date'] for r in records if r.get('date')), default=''),
            max((r['date'] for r in records if r.get('date')), default=''),
        ],
    }


# --- output ---

_LIST_FIELDS = ['id', 'date', 'state', 'type', 'judge', 'consequence', 'name', 'pdf', 'link']


def _project(r):
    return {k: r.get(k) for k in _LIST_FIELDS}


def _emit(data, fmt):
    if fmt == 'table':
        _print_table(data)
    else:
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write('\n')


def _print_table(data):
    # Generic object (stats, pdf, single non-record dict): key: value lines.
    if isinstance(data, dict) and 'id' not in data:
        for k, v in data.items():
            print(f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v}")
        return
    rows = data if isinstance(data, list) else [data]
    if not rows:
        print('(no results)')
        return
    if isinstance(rows[0], dict) and 'value' in rows[0] and 'count' in rows[0]:
        for r in rows:
            print(f"{r['count']:>5}  {r['value']}")
        return
    for r in rows:
        if not isinstance(r, dict):
            print(r)
            continue
        print(f"[{r.get('id')}] {r.get('date','')}  {r.get('state','')}  "
              f"{(r.get('type') or '')[:18]:18}  {(r.get('consequence') or '-')}")
        print(f"      {(r.get('name') or '')[:90]}")


def _filters_from_args(a):
    return {
        'judge': a.judge, 'court': a.court, 'state': a.state, 'type': a.type,
        'consequence': a.consequence, 'ai_type': a.ai_type, 'applies_to': a.applies_to,
        'source': a.source, 'jurisdiction': a.jurisdiction,
        'date_from': a.date_from, 'date_to': a.date_to,
        'has_pdf': a.has_pdf, 'has_link': a.has_link, 'tag': a.tag,
    }


def _add_filter_args(p):
    for name in ('judge', 'court', 'state', 'type', 'consequence', 'ai-type',
                 'applies-to', 'source', 'jurisdiction', 'tag', 'date-from', 'date-to'):
        p.add_argument(f'--{name}')
    p.add_argument('--has-pdf', action='store_true', help='only records with a self-hosted PDF')
    p.add_argument('--has-link', action='store_true', help='only records with a source link')
    p.add_argument('--limit', type=int, default=50)
    p.add_argument('--full', action='store_true', help='emit full records, not the summary projection')


def cmd_search(a):
    recs = apply_filters(search(load_orders(), a.query), _filters_from_args(a))
    recs = recs[:a.limit]
    _emit(recs if a.full else [_project(r) for r in recs], a.format)


def cmd_list(a):
    a.query = ''
    cmd_search(a)


def cmd_get(a):
    rec = next((r for r in load_orders() if str(r.get('id')) == str(a.id)), None)
    if rec is None:
        print(f'No record with id {a.id}', file=sys.stderr)
        sys.exit(3)
    _emit(rec, a.format)


def cmd_facets(a):
    _emit(facet(load_orders(), a.field, a.limit), a.format)


def cmd_stats(a):
    _emit(stats(load_orders()), a.format)


def cmd_pdf(a):
    rec = next((r for r in load_orders() if str(r.get('id')) == str(a.id)), None)
    if rec is None:
        print(f'No record with id {a.id}', file=sys.stderr)
        sys.exit(3)
    _emit({'id': rec['id'], 'pdf': rec.get('pdf', ''), 'link': rec.get('link', ''),
           'original_link': rec.get('original_link', '')}, a.format)


def cmd_bar(a):
    items = load_bar().get('items', [])
    if a.state:
        items = [b for b in items if _norm(a.state) in _norm(b.get('name'))
                 or _norm(a.state) == _norm(b.get('abbreviation'))]
    _emit(items, a.format)


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--format', choices=['json', 'table'], default='json',
                        help='output format (default: json)')

    p = argparse.ArgumentParser(prog='orders', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                parents=[common])
    sub = p.add_subparsers(dest='cmd', required=True)

    ps = sub.add_parser('search', parents=[common],
                        help='full-text search over name/summary/judge/court')
    ps.add_argument('query')
    _add_filter_args(ps)
    ps.set_defaults(func=cmd_search)

    pl = sub.add_parser('list', parents=[common], help='list/filter records (no query)')
    _add_filter_args(pl)
    pl.set_defaults(func=cmd_list)

    pg = sub.add_parser('get', parents=[common], help='fetch one record by id')
    pg.add_argument('id')
    pg.set_defaults(func=cmd_get)

    pf = sub.add_parser('facets', parents=[common],
                        help='distinct values + counts for a field')
    pf.add_argument('field', help='e.g. judge, court, state, type, consequence, ai_type')
    pf.add_argument('--limit', type=int, default=None)
    pf.set_defaults(func=cmd_facets)

    pt = sub.add_parser('stats', parents=[common], help='dataset summary counts')
    pt.set_defaults(func=cmd_stats)

    pp = sub.add_parser('pdf', parents=[common],
                        help='self-hosted PDF + source links for a record')
    pp.add_argument('id')
    pp.set_defaults(func=cmd_pdf)

    pb = sub.add_parser('bar', parents=[common], help='state bar AI ethics opinions')
    pb.add_argument('state', nargs='?')
    pb.set_defaults(func=cmd_bar)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()

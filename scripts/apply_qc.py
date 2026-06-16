#!/usr/bin/env python3
"""Apply a QC-resolution wave to the dataset.

Input: a JSON file `{results:[{id,status,cl_docket_url,pdf_url,matched_caption,
notes}]}` (or a bare list) produced by the qc-opinion-links workflow.

For each record we INDEPENDENTLY re-verify before trusting the agent:
  - pdf_url given  -> download, require %PDF + the caption's party surnames in
    the text, then self-host and set `pdf` + `link`.
  - docket only    -> require the agent's matched_caption to agree with the
    record's own summary caption, then set `link` to the CL docket.
  - neither/no match -> clear the (hallucinated) link.

Writes data/processed/explorer_data.json. Run cleanup.py afterwards to
normalize/validate/flag and mirror to charts/data.

Usage: python3 scripts/apply_qc.py results.json [--key CL_TOKEN]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_archive  # noqa: E402

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(PROJECT, 'data', 'processed', 'explorer_data.json')
ORDERS = '/Users/hao/legalhack/public_html/orders'
_STOP = {'inc', 'llc', 'corp', 'company', 'services', 'the', 'case', 'court',
         'order', 'united', 'states', 'district', 'county', 'board', 'llp',
         'national', 'association', 'commission', 'et', 'al', 'pc', 'in', 're'}
# Only these are *provably* fabricated: dockets.justia.com / docs.justia.com
# links carry an internal numeric id that the AI pipeline guessed, so they
# resolve to the wrong case (confirmed on records 287, 121, 248). Real opinion
# pages (law.justia.com/cases/..., FindLaw, Leagle) are NOT cleared — they are
# kept and flagged `unverified` instead, since we can't fetch them to confirm.
_CLEARABLE = ('dockets.justia.com', 'docs.justia.com')


def _is_suspect(url):
    return any(s in (url or '').lower() for s in _CLEARABLE)


def _toks(s):
    return set(re.findall(r'[a-z]{3,}', (s or '').lower())) - _STOP


def _surnames(caption):
    """Significant tokens from a 'X v. Y' caption (both sides)."""
    parts = re.split(r'\bv\.?\b', caption or '', maxsplit=1)
    out = _toks(parts[0])
    if len(parts) > 1:
        out |= _toks(parts[1])
    return out


def _summary_caption(rec):
    m = re.search(r'\bIn\s+(?:re\s+)?(.+?)(?:,\s*(?:No\.|\d{4}|Case|[A-Z]\.?\d))',
                  rec.get('summary', '') or '')
    return m.group(1) if m else (rec.get('summary', '') or '')[:80]


def _verify_pdf(url, dest, key):
    cmd = ['curl', '-s', '-A', 'Mozilla/5.0', '-L', '--max-time', '90']
    if key:
        cmd += ['-H', 'Authorization: Token ' + key]
    cmd += ['-o', dest, url]
    if subprocess.run(cmd).returncode != 0 or not os.path.exists(dest):
        return None
    with open(dest, 'rb') as f:
        if f.read(4) != b'%PDF':
            return None
    return subprocess.run(['pdftotext', dest, '-'], capture_output=True,
                          timeout=90).stdout.decode('utf-8', 'ignore').lower()


def apply(results, key=''):
    data = json.load(open(DATA))
    byid = {r['id']: r for r in data}
    s = {'link': 0, 'pdf': 0, 'cleared': 0, 'kept_unsuspect': 0,
         'pdf_rejected': 0, 'skipped': 0}

    def _resolve_fail(rec):
        # Clear only fabricated suspect-host links; leave a real court/.gov link.
        if _is_suspect(rec.get('link', '')):
            rec['link'], rec['link_source'] = '', 'none'
            s['cleared'] += 1
        else:
            s['kept_unsuspect'] += 1

    for r in results:
        rec = byid.get(r.get('id'))
        if not rec:
            s['skipped'] += 1
            continue
        dock = (r.get('cl_docket_url') or '').strip()
        cap = r.get('matched_caption') or ''
        if not dock:
            _resolve_fail(rec)
            continue
        # docket link only accepted if the matched caption agrees with the record
        if not (_surnames(cap) & _toks(_summary_caption(rec)) or
                _surnames(cap) & _toks(rec.get('name', ''))):
            _resolve_fail(rec)
            continue
        rec['link'], rec['link_source'] = dock, 'courtlistener'
        s['link'] += 1
        pdf_url = (r.get('pdf_url') or '').strip()
        if pdf_url:
            dest = '/tmp/qcapply_%s.pdf' % r['id']
            txt = _verify_pdf(pdf_url, dest, key)
            want = _surnames(cap)
            if txt is not None and (want & _toks(txt) or len(txt) < 1500):
                # surnames present, or near-empty text (scanned) with a confirmed docket
                k = pdf_archive.stable_key(rec, src=pdf_url)
                shutil.copy(dest, os.path.join(ORDERS, k + '.pdf'))
                rec['pdf'] = 'https://legalhack.io/orders/%s.pdf' % k
                s['pdf'] += 1
            else:
                s['pdf_rejected'] += 1
    json.dump(data, open(DATA, 'w'), indent=2, ensure_ascii=False)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('results')
    ap.add_argument('--key', default=os.environ.get('CL_API_KEY', ''))
    a = ap.parse_args()
    obj = json.load(open(a.results))
    results = obj.get('results', obj) if isinstance(obj, dict) else obj
    print('applying', len(results), 'results...')
    print(apply(results, a.key))


if __name__ == '__main__':
    main()

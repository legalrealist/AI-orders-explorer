#!/usr/bin/env python3
"""Produce light-markdown text of each self-hosted order PDF for LLM ingestion.

For every record with a self-hosted `pdf`, extract the document text (pdftotext;
OCR via pdftoppm+tesseract when the PDF has no text layer), strip ECF/page-stamp
noise, and write `<key>.md` next to the PDF with a small metadata header.

Usage: python3 scripts/pdf_to_md.py [--force]
"""
import argparse
import json
import os
import re
import subprocess
import tempfile

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(PROJECT, 'charts', 'data', 'explorer_data.json')
ORDERS = '/Users/hao/legalhack/public_html/orders'

# Repeated per-page ECF/PACER stamps and bare page numbers -> drop.
_NOISE = [
    re.compile(r'^\s*Case\s+[\d:]+-[a-z]{1,3}-\d+.*?(?:Page|PageID).*$', re.I),
    re.compile(r'^\s*Document\s+\d+(-\d+)?\s+Filed.*$', re.I),
    re.compile(r'^\s*Page\s+\d+\s+of\s+\d+\s*$', re.I),
    re.compile(r'^\s*-?\s*\d+\s*-?\s*$'),          # bare page number lines
    re.compile(r'^\s*#:\s*\d+\s*$'),
]


def _clean(text):
    text = text.replace('\x0c', '\n\n')           # form-feed page breaks
    out = []
    for ln in text.split('\n'):
        if any(p.match(ln) for p in _NOISE):
            continue
        out.append(ln.rstrip())
    text = '\n'.join(out)
    text = re.sub(r'\n{3,}', '\n\n', text)         # collapse blank runs
    return text.strip()


def _pdftotext(pdf):
    r = subprocess.run(['pdftotext', '-nopgbrk', pdf, '-'],
                       capture_output=True, timeout=120)
    return r.stdout.decode('utf-8', 'ignore')


def _ocr(pdf):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(['pdftoppm', '-r', '300', '-png', pdf, os.path.join(d, 'p')],
                       capture_output=True, timeout=300)
        parts = []
        for png in sorted(os.listdir(d)):
            if not png.endswith('.png'):
                continue
            r = subprocess.run(['tesseract', os.path.join(d, png), '-', '--psm', '1'],
                               capture_output=True, timeout=180)
            parts.append(r.stdout.decode('utf-8', 'ignore'))
        return '\n\n'.join(parts)


def _header(rec):
    bits = [f"**Court:** {rec.get('court') or 'n/a'}",
            f"**Judge:** {rec.get('judge') or 'n/a'}",
            f"**Date:** {rec.get('date') or 'n/a'}",
            f"**Type:** {rec.get('type') or 'n/a'}"]
    src = rec.get('link') or rec.get('original_link') or ''
    head = f"# {rec.get('name') or 'Court order'}\n\n" + ' · '.join(bits)
    if src:
        head += f"\n\n**Source:** {src}"
    return head + "\n\n---\n\n"


def convert(records, force=False):
    stats = {'text': 0, 'ocr': 0, 'skip': 0, 'missing': 0}
    for rec in records:
        pdf_url = (rec.get('pdf') or '').strip()
        if not pdf_url:
            continue
        key = pdf_url.rsplit('/', 1)[-1][:-4]
        pdf = os.path.join(ORDERS, key + '.pdf')
        md = os.path.join(ORDERS, key + '.txt')
        if not os.path.exists(pdf):
            stats['missing'] += 1
            continue
        if os.path.exists(md) and not force and os.path.getmtime(md) >= os.path.getmtime(pdf):
            stats['skip'] += 1
            continue
        body = _clean(_pdftotext(pdf))
        if len(re.sub(r'\s', '', body)) < 200:      # scanned -> OCR
            body = _clean(_ocr(pdf))
            stats['ocr'] += 1
        else:
            stats['text'] += 1
        with open(md, 'w', encoding='utf-8') as f:
            f.write(_header(rec) + body + '\n')
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    records = json.load(open(DATA))
    print(convert(records, force=a.force))


if __name__ == '__main__':
    main()

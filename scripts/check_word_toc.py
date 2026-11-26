#!/usr/bin/env python3
"""Check cached Word TOC page numbers against a final, text-searchable render."""
import argparse
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile, BadZipFile

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def val(e, key):
    return e.get(W + key)
def text(e):
    return ''.join(t.text or '' for t in e.iter(W + 't'))
def compact(s):
    return re.sub(r'\s+', '', s)

def check(docx, layout):
    with ZipFile(docx) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    paragraphs = list(root.iter(W + 'p'))
    if not any(re.match(r'^\s*TOC(?:\s|$)', e.text or '') for e in root.iter(W + 'instrText')):
        return 0, ['未发现可更新的 Word TOC 域。']
    bookmarks = {val(k, 'name'): text(p) for p in paragraphs for k in p.iter(W + 'bookmarkStart')}
    pages = [p for p in layout.split('\f') if p.strip()]
    if len(pages) < 2:
        return 0, ['需要以换页符分隔的完整终稿文本（pdftotext -layout）。']
    errors = []
    count = 0
    for p in paragraphs:
        refs = [m.group(1).strip('"') for e in p.iter(W + 'instrText')
                if (m := re.match(r'^\s*PAGEREF\s+(\S+)', e.text or ''))]
        links = [h for h in p.iter(W + 'hyperlink') if val(h, 'anchor') in refs]
        for link in links:
            name = val(link, 'anchor')
            if not name or not name.startswith('_Toc'):
                continue
            count += 1
            label = bookmarks.get(name, '')
            ts = list(link.iter(W + 't'))
            cached = (ts[-1].text or '').strip() if ts else ''
            # Table-of-contents lines contain dot leaders and page numbers, unlike headings.
            locations = [(i, page) for i, page in enumerate(pages, 1)
                         if label and compact(label) in {compact(l) for l in page.splitlines()}]
            if len(locations) != 1:
                errors.append(f'{label or name}: 无法唯一定位最终分页，需在 Word 中核对。')
                continue
            i, page = locations[0]
            lines = [line.strip() for line in page.splitlines() if line.strip()]
            footer = lines[-1] if lines else ''
            if not re.fullmatch(r'\d+', footer):
                errors.append(f'{label}: 第 {i} 张的页脚非单独阿拉伯页码，需在 Word 中核对。')
            elif cached != footer:
                errors.append(f'{label}: 目录为 {cached or "空白"}，实际页脚为 {footer}。')
    if not count:
        errors.append('未识别支持的 TOC/PAGEREF 条目；请在 Word 中逐项核对。')
    # A nonstandard variant must be verified manually instead of claiming the tool checked every entry.
    linked_toc = [h for h in root.iter(W + 'hyperlink') if (val(h, 'anchor') or '').startswith('_Toc')]
    if len(linked_toc) != count:
        errors.append('存在未检查的目录链接，须在 Word 中核对。')
    return count, errors

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('docx', type=Path)
    parser.add_argument('layout', type=Path, help='pdftotext -layout 输出（须保留换页符）')
    args = parser.parse_args()
    try:
        count, errors = check(args.docx, args.layout.read_text(encoding='utf-8'))
    except (OSError, KeyError, ValueError, ET.ParseError, BadZipFile) as e:
        print(e, file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f'{count} 项目录页码与最终渲染页脚一致。')
    return 0

if __name__ == '__main__':
    sys.exit(main())

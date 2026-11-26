"""核对项目要点与报告标题。Python 3.10+，仅使用标准库。"""

import argparse
import csv
import os
import re
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def csv_rows(path, columns):
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        if not set(columns).issubset(reader.fieldnames or ()):
            raise ValueError(f"{path.name} 缺少表头：{'、'.join(columns)}")
        for row in reader:
            if not all((row.get(col) or '').strip() for col in columns):
                raise ValueError(f"{path.name} 第 {reader.line_num} 行有空值")
            yield tuple(row[col].strip() for col in columns)


def markdown_lines(path):
    fence = None
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            continue
        if marker:
            fence = marker[1]
            continue
        heading = re.match(r"^ {0,3}(#{1,6})[ \t]+(.+?)\s*$", line)
        if heading:
            yield number, len(heading[1]), re.sub(r"\s+#+$", "", heading[2]).strip()
        else:
            yield number, 0, line


def scope_ids(path, section):
    if path.suffix.lower() == ".csv" and not section:
        return [key for key, in csv_rows(path, ["原范围条项"])]
    if path.suffix.lower() != ".md" or not section:
        raise ValueError("范围请用 CSV，或用 Markdown 并以 --section 指定编号清单标题")
    ids = []
    matches = 0
    level = 0
    for _, depth, value in markdown_lines(path):
        if depth:
            if value == section:
                matches += 1
                level = depth
            elif depth <= level:
                level = 0
        elif level:
            item = re.match(r"^([0-9]+)[.、．)]\s*(?=\S)", value)
            if item:
                ids.append(item[1])
    if matches != 1:
        raise ValueError(f"范围标题须唯一，实际找到 {matches} 处：{section}")
    return ids


# 每个事件包含标题级别、块类型、原文和位置。表格文字逐格扫描，
# 表格本身仅计一次。只有表头或全空单元格的表格不构成章节内容。
def table_cells(line):
    return re.split(r"(?<!\\)\|", line.strip().strip("|"))


def markdown_blocks(path):
    lines = list(markdown_lines(path))
    i = 0
    paragraph = False
    while i < len(lines):
        number, depth, value = lines[i]
        i += 1
        location = f"第 {number} 行"
        if depth:
            yield depth, "heading", value, location
            paragraph = False
        elif not value.strip() or re.fullmatch(r"\s*(?:-{3,}|\*{3,}|_{3,})\s*", value):
            paragraph = False
        elif ("|" in value and i < len(lines) and "|" in lines[i][2]
              and all(re.fullmatch(r":?-+:?", cell.strip()) for cell in table_cells(lines[i][2]))):
            yield 0, "text", value, location
            i += 1
            filled = False
            while i < len(lines) and not lines[i][1] and "|" in lines[i][2]:
                row_num, _, row = lines[i]
                i += 1
                filled |= any(cell.strip() for cell in table_cells(row))
                yield 0, "text", row, f"第 {row_num} 行（表格）"
            if filled:
                yield 0, "table", "", location
            paragraph = False
        else:
            # Markdown 中连续的普通行属于同一段，列表项各起一段。
            item = re.match(r"^\s*(?:[-*+]\s+|\d+[.)、]\s*)", value)
            kind = "paragraph" if not paragraph or item else "continuation"
            yield 0, kind, value, number
            paragraph = True


def markdown_report(path):
    lines = []
    start = 0
    for depth, kind, value, location in markdown_blocks(path):
        if kind == "continuation" and lines and location == start + len(lines):
            lines.append(value)
            continue
        if lines:
            yield 0, "paragraph", "\n".join(lines), start
            lines = []
        if kind in {"paragraph", "continuation"}:
            start = location
            lines = [value]
        else:
            yield depth, kind, value, location
    if lines:
        yield 0, "paragraph", "\n".join(lines), start


def heading_level(paragraph, styles):
    outline = paragraph.find(f"{W}pPr/{W}outlineLvl")
    style = paragraph.find(f"{W}pPr/{W}pStyle")
    visited = set()
    while outline is None and style is not None:
        key = style.get(W + "val")
        if key in visited or key not in styles:
            break
        visited.add(key)
        owner = styles[key]
        outline = owner.find(f"{W}pPr/{W}outlineLvl")
        style = owner.find(W + "basedOn")
    if outline is None:
        return 0
    level = int(outline.get(W + "val"))
    return level + 1 if 0 <= level < 9 else 0


def word_blocks(element):
    for child in element:
        if child.tag in (W + "p", W + "tbl"):
            yield child
        elif child.tag in (W + "sdt", W + "sdtContent", W + "customXml", W + "ins"):
            yield from word_blocks(child)


def word_text(paragraph):
    return "".join(t.text or "" for t in paragraph.iter(W + "t"))


def word_report(path):
    with zipfile.ZipFile(path) as package:
        body = ET.fromstring(package.read("word/document.xml")).find(W + "body")
        styles_xml = ET.fromstring(package.read("word/styles.xml"))
    styles = {s.get(W + "styleId"): s for s in styles_xml.findall(W + "style")}
    p_number = t_number = 0
    for block in word_blocks(body):
        if block.tag == W + "p":
            p_number += 1
            value = word_text(block)
            if value.strip():
                depth = heading_level(block, styles)
                yield depth, "heading" if depth else "paragraph", value, f"正文第 {p_number} 段"
            continue
        t_number += 1
        filled = False
        for row_num, row in enumerate(block.findall(W + "tr"), 1):
            flag = row.find(f"{W}trPr/{W}tblHeader")
            header = flag is not None and flag.get(W + "val", "1") not in {"0", "false", "off"}
            for col_num, cell in enumerate(row.findall(W + "tc"), 1):
                location = f"表 {t_number} 第 {row_num} 行第 {col_num} 格"
                for p in cell.iter(W + "p"):
                    value = word_text(p)
                    if value.strip():
                        filled |= not header
                        yield 0, "text", value, location
        if filled:
            yield 0, "table", "", f"表 {t_number}"


MARKERS = re.compile(r"【[^【】]*】|\[(?:TBD|TBC|XX|date(?:\s+\d+)?|insert\s+[^\[\]]+)\]", re.I)


def find_markers(text, location, markdown=False):
    for match in MARKERS.finditer(text):
        token = match[0]
        if token.startswith("["):
            # Markdown 链接标签和引用定义可能与待填标记同名。
            if markdown and (text[match.end():match.end() + 1] in ("(", "[")
                             or re.match(r":[ \t]+\S", text[match.end():]) and not text[:match.start()].split("\n")[-1].strip()
                             or text[max(0, match.start() - 1):match.start()] == "]"):
                continue
            token = " ".join(token.split())
        else:
            token = token.replace("\n", "")
        if re.match(r"【(?:请公司补充|请公司确认|本所核对|经办确认)[｜|]", token):
            continue
        position = location
        if isinstance(location, int):
            first = location + text.count("\n", 0, match.start())
            last = first + match[0].count("\n")
            position = f"第 {first} 行" if last == first else f"第 {first} 至 {last} 行"
        yield position, token


def word_review_parts(path):
    note_parts = {
        "word/comments.xml": ("comment", "批注"),
        "word/footnotes.xml": ("footnote", "脚注"),
        "word/endnotes.xml": ("endnote", "尾注"),
    }
    comments = 0
    markers = []
    with zipfile.ZipFile(path) as package:
        for name in sorted(package.namelist()):
            if name in note_parts:
                tag, kind = note_parts[name]
                root = ET.fromstring(package.read(name))
                notes = root.findall(W + tag)
                if tag == "comment":
                    comments += len(notes)
                for note in notes:
                    label = f"{kind} ID {note.get(W + 'id', '未知')}"
                    for i, paragraph in enumerate(note.iter(W + "p"), 1):
                        markers.extend(find_markers(word_text(paragraph), f"{label} 第 {i} 段"))
            elif re.fullmatch(r"word/(?:header|footer)[^/]*\.xml", name):
                kind = "页眉" if name.startswith("word/header") else "页脚"
                root = ET.fromstring(package.read(name))
                for i, paragraph in enumerate(root.iter(W + "p"), 1):
                    label = f"{kind} {Path(name).stem} 第 {i} 段"
                    markers.extend(find_markers(word_text(paragraph), label))
    return comments, markers


@dataclass
class Section:
    title: str
    depth: int
    path: tuple = ()
    paragraphs: int = 0
    tables: int = 0
    marker_count: int = 0
    markers: list = field(default_factory=list)


def inspect_report(events, markdown=False):
    front = Section("首个标题前", 0)
    sections = [front]
    stack = []
    for depth, kind, value, location in events:
        if depth:
            while stack and stack[-1].depth >= depth:
                stack.pop()
            section = Section(value, depth, tuple(s.title for s in stack) + (value,))
            stack.append(section)
            sections.append(section)
        owner = stack[-1] if stack else front
        markers = list(find_markers(value, location, markdown))
        owner.markers.extend(markers)
        for section in stack or [front]:
            section.paragraphs += int(kind == "paragraph")
            section.tables += int(kind == "table")
            section.marker_count += len(markers)
    return sections

def check(args):
    ids = scope_ids(args.scope, args.section)
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("范围条项为空或重号。请按委托范围区分同号条项")
    readers = {".md": markdown_report, ".docx": word_report}
    reader = readers.get(args.report.suffix.lower())
    if reader is None:
        raise ValueError("报告请用 Markdown 或 DOCX")
    front, *sections = inspect_report(reader(args.report), markdown=(reader is markdown_report))
    headings = defaultdict(list)
    paths = defaultdict(list)
    for section in sections:
        key = tuple(" ".join(title.split()) for title in section.path)
        headings[key[-1]].append(section)
        for i in range(len(key) - 1):
            paths[key[i:]].append(section)
    if not sections:
        raise ValueError("未读到报告标题，请提供有标题样式的报告或 Markdown 标题")
    mapped = set()
    unresolved = set()
    issues = []
    for item, title in csv_rows(args.mapping, ["原范围条项", "报告位置"]):
        mapped.add(item)
        if item not in ids:
            issues.append(f"对应表有范围外编号：{item}")
        label = " ".join(title.split())
        matches = headings.get(label, [])
        if not matches:
            matches = paths.get(tuple(label.split(" > ")), [])
        count = len(matches)
        if count != 1:
            unresolved.add(item)
            message = f"{item}｜{title}：标题匹配 {count} 处，请核对位置"
            if count > 1:
                message += "。候选位置：" + "；".join(" > ".join(s.path) for s in matches)
            issues.append(message)
    issues.extend(f"未对应报告位置：{key}" for key in ids if key not in mapped)
    print(f"范围定位：应核 {len(ids)} 项，已列位置 {len(mapped.intersection(ids))} 项，"
          f"所列标题均可唯一定位 {len(mapped.intersection(ids) - unresolved)} 项。")
    for message in dict.fromkeys(issues):
        print(message)
    def display_title(section):
        if len(headings.get(" ".join(section.title.split()), [])) > 1:
            return " > ".join(section.path)
        return section.title

    empty = 0
    print("章节内容（含下属小节）")
    for section in sections:
        status = ""
        if not (section.paragraphs or section.tables):
            status = "｜空标题"
            empty += 1
        print(f"{display_title(section)}｜正文 {section.paragraphs} 段｜表格 {section.tables} 张"
              f"｜本节占位 {len(section.markers)} 处｜含下级共 {section.marker_count} 处{status}")
    hits = [f"{display_title(s)}｜{location}｜{token}" for s in [front, *sections]
            for location, token in s.markers]
    comments = 0
    if args.report.suffix.lower() == ".docx":
        comments, extra_markers = word_review_parts(args.report)
        hits.extend(f"{location}｜{token}" for location, token in extra_markers)
        print(f"Word 批注：共 {comments} 条。")
    print(f"占位位置：共 {len(hits)} 处。")
    for hit in hits:
        print(hit)
    return int(bool(issues or empty or (args.final and (hits or comments))))


if __name__ == "__main__":
    if not os.environ.get("PYTHONIOENCODING"):
        for stream in (sys.stdout, sys.stderr):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("scope", "mapping", "report"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--section", help="Markdown 范围中的清单标题")
    parser.add_argument("--final", action="store_true", help="清洁版检查：残留占位符或 Word 批注时返回非零")
    try:
        sys.exit(check(parser.parse_args()))
    except (ValueError, OSError, csv.Error, zipfile.BadZipFile, ET.ParseError, KeyError) as exc:
        sys.exit(f"输入错误：{exc}")

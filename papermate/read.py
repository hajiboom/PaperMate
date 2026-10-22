"""读取入口：PDF → 结构化 Document。

对外只暴露一个函数级接缝：

    read_pages(path, pages=...) -> Document

未来如果需要 OCR 或更强的版面引擎，写一个同样签名的函数替换即可，
不需要引擎注册表。
"""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from .figures import extract_figures
from .layout import (
    END_PUNCT,
    body_size,
    detect_two_column,
    drop_running_lines,
    extract_lines,
    find_running_keys,
    group_paragraphs,
    join_text,
    merge_same_baseline,
    order_runs,
    split_footnotes,
)
from .model import Block, Document, PageDoc
from .tables import extract_tables, line_inside


def parse_page_spec(spec: str | None, page_count: int) -> set[int] | None:
    if not spec:
        return None
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            pages.update(range(int(start), int(end) + 1))
        else:
            pages.add(int(part))
    return {page for page in pages if 1 <= page <= page_count}


def _merge_continuations(blocks: list[Block], body: float) -> list[Block]:
    """把被版面切断的短续行并回上一段（紧邻、且上一段没有句末标点时）。"""
    merged: list[Block] = []
    for block in blocks:
        if merged and block.kind == "paragraph" and merged[-1].kind == "paragraph":
            previous = merged[-1]
            gap = block.bbox[1] - previous.bbox[3]
            fragment = len(previous.text) <= 30 and not previous.text.endswith(END_PUNCT)
            if (
                (len(block.text) <= 30 or fragment)
                and -0.5 * body <= gap <= 2.0 * body
                and not previous.text.endswith(END_PUNCT)
            ):
                previous.text = join_text(previous.text, block.text)
                previous.lines.extend(block.lines)
                previous.bbox = (
                    min(previous.bbox[0], block.bbox[0]),
                    min(previous.bbox[1], block.bbox[1]),
                    max(previous.bbox[2], block.bbox[2]),
                    max(previous.bbox[3], block.bbox[3]),
                )
                continue
        merged.append(block)
    return merged


def _insert_tables(blocks: list[Block], tables: list[Block]) -> list[Block]:
    """按 y 坐标把表格插回段落之间。表格很少，位置粗略但可核对。"""
    for table in tables:
        index = 0
        for i, block in enumerate(blocks):
            if block.bbox[1] < table.bbox[1]:
                index = i + 1
        blocks.insert(index, table)
    return blocks


def _pick_title(page: PageDoc, body: float) -> str:
    candidates = [
        block
        for block in page.blocks
        if block.kind == "heading"
        and len(block.text) >= 4
        and block.lines
        and block.lines[0].size > body + 2.5
        and block.bbox[1] < 0.35 * page.height
        and any("\u4e00" <= ch <= "\u9fff" for ch in block.text)
    ]
    if not candidates:
        return ""
    largest = max(candidates, key=lambda block: block.lines[0].size)
    size = largest.lines[0].size
    nearby = [
        block
        for block in candidates
        if abs(block.lines[0].size - size) <= 0.8
        and abs(block.bbox[1] - largest.bbox[1]) < 100
    ]
    subtitle = [
        block
        for block in page.blocks
        if block.kind == "heading"
        and block.lines
        and block.text.startswith("——")
        and abs(block.bbox[1] - largest.bbox[1]) < 100
        and block not in nearby
    ]
    nearby = sorted([*nearby, *subtitle], key=lambda block: block.bbox[1])
    title = ""
    for block in nearby:
        title = join_text(title, block.text)
    return re.sub(r"\s+", " ", title).strip()


def read_pages(path: str | Path, pages: str | None = None) -> Document:
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)

    handle = pymupdf.open(pdf_path)
    try:
        pdf_pages = [handle.load_page(i) for i in range(handle.page_count)]
        raw = [extract_lines(page) for page in pdf_pages]
        heights = [float(page.rect.height) for page in pdf_pages]
        widths = [float(page.rect.width) for page in pdf_pages]
        running = find_running_keys(raw, heights)
        # 正文字号按整篇统计，避免某一页摘要/参考文献占比高时把正文误判成标题
        document_body = body_size([line for page_lines in raw for line in page_lines])
        selected = parse_page_spec(pages, handle.page_count)

        document = Document(path=str(pdf_path))
        for index, page in enumerate(pdf_pages, 1):
            if selected is not None and index not in selected:
                continue

            height = heights[index - 1]
            width = widths[index - 1]
            two_column, column_mid = detect_two_column(raw[index - 1], width)
            lines = drop_running_lines(raw[index - 1], running, height, document_body)
            lines = merge_same_baseline(lines, column_mid if two_column else None)

            tables, table_boxes, consumed = extract_tables(page, lines)
            figures, figure_lines = extract_figures(
                lines, document_body, width, table_boxes
            )
            consumed_ids = {id(line) for line in consumed} | figure_lines
            lines = [
                line
                for line in lines
                if id(line) not in consumed_ids and not line_inside(line, table_boxes)
            ]

            body_lines, notes = split_footnotes(
                lines, document_body, height, column_mid if two_column else None
            )
            runs = order_runs(body_lines, width, two_column)

            blocks: list[Block] = []
            for run in runs:
                blocks.extend(group_paragraphs(run, document_body))
            blocks = _merge_continuations(blocks, document_body)
            blocks = _insert_tables(blocks, tables)
            blocks = _insert_tables(blocks, figures)

            chars = sum(len(line.text) for line in body_lines)
            flags = {
                "two_column": len(runs) > 1,
                "tables": len(tables),
                "figures": len(figures),
                "notes": len(notes),
                "scanned": chars < 50 and bool(page.get_images()),
            }
            page_doc = PageDoc(
                page=index,
                width=width,
                height=height,
                blocks=blocks,
                footnotes=notes,
                flags=flags,
            )
            if not document.title and index == 1:
                document.title = _pick_title(page_doc, document_body)
            document.pages.append(page_doc)
        return document
    finally:
        handle.close()

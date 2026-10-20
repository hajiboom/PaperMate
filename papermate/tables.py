"""表格抽取：find_tables + 合并单元格补全 + 表题关联。"""

from __future__ import annotations

import re

from .layout import join_text, normalize
from .model import Block, Line

CAPTION_RE = re.compile(r"^\s*(?:表|Table)\s*\d+")


def _clean_cell(value) -> str:
    if value is None:
        return ""
    text = normalize(str(value))
    out = ""
    for part in text.split("\n"):
        part = part.strip()
        if part:
            out = join_text(out, part)
    return out


def _fill_down(rows: list[list[str]]) -> list[list[str]]:
    """rowspan 只落在首行：首列为空时继承上一行。

    只补首列，是一个保守的启发式：宁可留下空格，也不把真实空值填错。
    """
    for index in range(1, len(rows)):
        if rows[index] and not rows[index][0] and rows[index - 1]:
            rows[index][0] = rows[index - 1][0]
    return rows


def _find_caption(lines: list[Line], bbox) -> tuple[str, Line | None]:
    top = bbox[1]
    candidates = [
        line
        for line in lines
        if CAPTION_RE.match(line.text) and -50 < top - line.y1 < 4
    ]
    if not candidates:
        return "", None
    best = max(candidates, key=lambda line: line.y1)
    return best.text, best


def extract_tables(page, lines: list[Line]) -> tuple[list[Block], list[tuple], list[Line]]:
    """返回（表格块, 表格 bbox, 被表题占用的行）。"""
    blocks: list[Block] = []
    boxes: list[tuple] = []
    consumed: list[Line] = []

    try:
        finder = page.find_tables()
        found = list(getattr(finder, "tables", []))
    except Exception:  # noqa: BLE001 - 单页表格检测失败不应中断整篇
        return blocks, boxes, consumed

    for table in found:
        rows = [[_clean_cell(cell) for cell in row] for row in table.extract()]
        rows = _fill_down(rows)
        caption, caption_line = _find_caption(lines, table.bbox)
        if caption_line is not None:
            consumed.append(caption_line)
        x0, y0, x1, y1 = (float(v) for v in table.bbox)
        blocks.append(
            Block(
                kind="table",
                rows=rows,
                caption=caption,
                bbox=(x0, y0, x1, y1),
            )
        )
        boxes.append((x0, y0, x1, y1))

    return blocks, boxes, consumed


def line_inside(line: Line, boxes: list[tuple], pad: float = 2.0) -> bool:
    cx = line.center_x
    cy = (line.y0 + line.y1) / 2
    for x0, y0, x1, y1 in boxes:
        if x0 - pad <= cx <= x1 + pad and y0 - pad <= cy <= y1 + pad:
            return True
    return False

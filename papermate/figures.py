"""图与图内文字：把坐标轴数字、类别标签从正文里分离出来。

不做图像理解，只保证：图内文字不混进正文，并且明确标记"顺序不可靠"。
"""

from __future__ import annotations

import re

from .model import Block, Line

CAPTION_RE = re.compile(r"^\s*(?:图|Figure)\s*\d+")


def _numeric_ratio(text: str) -> float:
    compact = re.sub(r"\s+", "", text)
    if not compact:
        return 0.0
    numeric = sum(1 for ch in compact if ch.isdigit() or ch in "%.-")
    return numeric / len(compact)


def _inside(line: Line, boxes: list[tuple]) -> bool:
    cx = line.center_x
    cy = (line.y0 + line.y1) / 2
    return any(x0 <= cx <= x1 and y0 <= cy <= y1 for x0, y0, x1, y1 in boxes)


def extract_figures(
    lines: list[Line], body: float, page_width: float, table_boxes: list[tuple]
) -> tuple[list[Block], set[int]]:
    figures: list[Block] = []
    consumed: set[int] = set()

    for caption in [line for line in lines if CAPTION_RE.match(line.text)]:
        labels = [
            line
            for line in lines
            if line is not caption
            and -14 < caption.y0 - line.y1 < 240
            and line.size < body - 1.0
            and (_numeric_ratio(line.text) >= 0.5 or line.width < 0.22 * page_width)
            and not _inside(line, table_boxes)
        ]
        numbers = [line.text for line in labels if _numeric_ratio(line.text) >= 0.5]
        categories = [line.text for line in labels if _numeric_ratio(line.text) < 0.5]
        numbers = list(dict.fromkeys(numbers))
        categories = list(dict.fromkeys(categories))

        parts: list[str] = []
        if numbers:
            parts.append("图内数值：" + " ".join(numbers))
        if categories:
            parts.append("图内类别：" + " / ".join(categories))
        figures.append(
            Block(
                kind="figure",
                caption=caption.text,
                text="；".join(parts),
                note="图内文字顺序不可靠，数字需回原 PDF 核对" if parts else "未能提取图内文字",
            )
        )
        consumed.add(id(caption))
        consumed.update(id(line) for line in labels)

    return figures, consumed

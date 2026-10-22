"""页面版面归一化：行合并 → 页眉页脚 → 分栏 → 段落 → 脚注。

这里只做"把 PDF 的碎片还原成可读顺序"，不做任何学术判断。
"""

from __future__ import annotations

import re
from collections import Counter

from .model import Block, Line

CJK_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
END_PUNCT = ("。", "！", "？", "；", "：", "…", "」", "』", "）", ")")
HEADING_NUM = re.compile(
    r"^\s*(?:[一二三四五六七八九十]+、|[（(][一二三四五六七八九十]+[)）]|\d+[.、])"
)
NOTE_START = re.compile(
    r"^\s*(?:[①-⑳]|[（(]\d{1,2}[)）]|[［\[]\d{1,3}[］\]]|〔\d{1,3}〕)"
)
PAGE_NO = re.compile(r"^[·•\s]*\d{1,4}[·•\s]*$")
ISSUE_RE = re.compile(
    r"(?:(?:19|20)\d{2}\s*年\s*第\s*\d+\s*期|总第\s*\d+\s*期|第\s*\d+\s*期|(?:19|20)\d{2}\.\d{1,2})"
)
NOTE_HEADER = re.compile(r"^\s*(?:注释|注)\s*[:：]?\s*$")


def normalize(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def is_cjk(ch: str) -> bool:
    return bool(CJK_RE.match(ch))


def join_text(left: str, right: str) -> str:
    """拼接同一段落的两行：中文不加空格，英文加空格，处理行尾连字符。"""
    if not left:
        return right
    if not right:
        return left
    if left.endswith("-") and right[0].isascii() and right[0].isalpha():
        return left[:-1] + right
    if is_cjk(left[-1]) or is_cjk(right[0]):
        return left + right
    if left[-1] in "（(《“‘" or right[0] in "，。！？；：、）》”’":
        return left + right
    return left + " " + right


def extract_lines(page) -> list[Line]:
    """从 get_text('dict') 取行；行内 spans 合并成一条（暂不跨基线合并）。"""
    layout = page.get_text("dict")
    lines: list[Line] = []
    for block in layout.get("blocks", []):
        for line in block.get("lines", []):
            spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
            if not spans:
                continue
            text = normalize("".join(s["text"] for s in spans))
            if not text:
                continue
            x0, y0, x1, y1 = line["bbox"]
            direction = line.get("dir", (1, 0))
            lines.append(
                Line(
                    text=text,
                    x0=float(x0),
                    y0=float(y0),
                    x1=float(x1),
                    y1=float(y1),
                    size=max(float(s.get("size", 0.0)) for s in spans),
                    bold=any(int(s.get("flags", 0)) & 16 for s in spans),
                    rotated=abs(float(direction[0]) - 1.0) > 0.01,
                )
            )
    return lines


def detect_two_column(lines: list[Line], page_width: float) -> tuple[bool, float]:
    """按"是否有大量行横跨页中线"判断分栏，返回 (是否双栏, 中线 x)。

    双栏页的行不会跨中线；单栏页即使同一行被切成两段，两段合起来也会跨中线。
    """
    if not lines:
        return False, page_width / 2

    left, right = _content_bounds(lines, page_width)
    content_width = max(right - left, 1.0)
    mid = (left + right) / 2

    crossing = [
        line
        for line in lines
        if line.x0 < mid - 0.02 * content_width
        and line.x1 > mid + 0.02 * content_width
    ]
    left_lines = [
        line for line in lines if line.center_x < mid and line.width < 0.58 * content_width
    ]
    right_lines = [
        line for line in lines if line.center_x > mid and line.width < 0.58 * content_width
    ]
    two_column = (
        len(lines) >= 10
        and len(crossing) / len(lines) < 0.4
        and len(left_lines) >= 4
        and len(right_lines) >= 4
    )
    return two_column, mid


def merge_same_baseline(lines: list[Line], column_mid: float | None = None) -> list[Line]:
    """同一基线上被 PDF 切成多段的行，按 x 拼回去。

    column_mid 不为 None 时，只合并同一侧（同一栏）的碎片；
    双栏之间即使间隙很小，也不会被拼成一行。
    """
    if not lines:
        return []

    ordered = sorted(lines, key=lambda line: (line.y1, line.x0))
    groups: list[list[Line]] = []
    for line in ordered:
        if line.rotated:
            groups.append([line])
            continue
        for group in reversed(groups[-4:]):
            gap = line.x0 - group[-1].x1
            same_side = (
                column_mid is None
                or (group[-1].center_x < column_mid) == (line.center_x < column_mid)
            )
            if (
                abs(group[0].y1 - line.y1) <= 3.0
                and gap <= max(4.0, 0.8 * line.size)
                and same_side
            ):
                group.append(line)
                break
        else:
            groups.append([line])

    merged: list[Line] = []
    for group in groups:
        group.sort(key=lambda line: line.x0)
        text = ""
        for piece in group:
            piece_text = piece.text
            # 过大的破折号字形会重复一个 "—"
            if text.endswith("—") and piece_text.startswith("—"):
                piece_text = piece_text[1:]
            text = join_text(text, piece_text)
        merged.append(
            Line(
                text=normalize(text),
                x0=min(line.x0 for line in group),
                y0=min(line.y0 for line in group),
                x1=max(line.x1 for line in group),
                y1=max(line.y1 for line in group),
                size=max(group, key=lambda piece: len(piece.text)).size,
                bold=any(line.bold for line in group),
            )
        )
    return merged


def _running_key(text: str) -> str:
    key = re.sub(r"[\d\s·•:：\-—–_()（）\[\]【】]", "", text)
    return key if len(key) >= 4 else ""


def find_running_keys(pages: list[list[Line]], heights: list[float]) -> set[str]:
    """在多页顶部/底部重复出现的行 = 页眉页脚。"""
    counts: Counter[str] = Counter()
    for lines, height in zip(pages, heights):
        seen: set[str] = set()
        for line in lines:
            if not (line.y1 < 0.10 * height or line.y0 > 0.90 * height):
                continue
            key = _running_key(line.text)
            if key:
                seen.add(key)
        counts.update(seen)
    threshold = max(3, int(len(pages) * 0.3))
    return {key for key, count in counts.items() if count >= threshold}


def drop_running_lines(
    lines: list[Line], running: set[str], height: float, body: float = 0.0
) -> list[Line]:
    kept: list[Line] = []
    for line in lines:
        # 纯符号行（分隔线、栏目符）和孤立页码
        if not re.search(r"[\w\u4e00-\u9fff]", line.text):
            continue
        if PAGE_NO.match(line.text) and line.width < 20:
            continue
        top_band = line.y0 < 0.11 * height
        bottom_band = line.y0 > 0.90 * height
        # 页眉里的全大写英文（期刊名），不随字号变化
        if top_band and line.text.isascii() and line.text.isupper() and len(line.text) > 3:
            continue
        # 页眉区域里明显小于正文的字号：刊名、期号、日期、页码
        if top_band and body and line.size < body - 0.8:
            continue
        if top_band and ISSUE_RE.search(line.text):
            continue
        if top_band or bottom_band:
            if _running_key(line.text) in running:
                continue
            if PAGE_NO.match(line.text):
                continue
        kept.append(line)
    return kept


def body_size(lines: list[Line]) -> float:
    weighted: Counter[float] = Counter()
    for line in lines:
        weighted[round(line.size, 1)] += len(line.text)
    if not weighted:
        return 0.0
    return weighted.most_common(1)[0][0]


def _content_bounds(lines: list[Line], page_width: float) -> tuple[float, float]:
    if not lines:
        return 0.0, page_width
    xs0 = sorted(line.x0 for line in lines)
    xs1 = sorted(line.x1 for line in lines)
    left = xs0[int(len(xs0) * 0.05)]
    right = xs1[min(int(len(xs1) * 0.95), len(xs1) - 1)]
    return left, right


def order_runs(
    lines: list[Line], page_width: float, two_column: bool | None = None
) -> list[list[Line]]:
    """把行切成"阅读顺序正确的串"。双栏页按栏切，单栏页直接按 y 排。"""
    if not lines:
        return []

    left, right = _content_bounds(lines, page_width)
    content_width = max(right - left, 1.0)
    mid = (left + right) / 2

    if two_column is None:
        narrow = [line for line in lines if line.width < 0.62 * content_width]
        left_lines = [line for line in narrow if line.center_x < mid - 0.05 * content_width]
        right_lines = [line for line in narrow if line.center_x > mid + 0.05 * content_width]
        two_column = (
            len(left_lines) >= 4
            and len(right_lines) >= 4
            and min(len(left_lines), len(right_lines)) / max(len(left_lines), len(right_lines)) > 0.2
        )

    if not two_column:
        return [[line for line in sorted(lines, key=lambda item: (item.y0, item.x0))]]

    full_threshold = 0.72 * content_width
    bands: list[tuple[str, list[Line]]] = []
    current: list[Line] = []
    mode: str | None = None
    for line in sorted(lines, key=lambda item: (item.y0, item.x0)):
        line_mode = "full" if line.width > full_threshold else "narrow"
        if mode is not None and line_mode != mode:
            # 整行块后面的短续行（如关键词第二行）：起点对齐且间距很小，留在原块
            if mode == "full" and current:
                previous = current[-1]
                if (
                    abs(line.x0 - previous.x0) <= 10
                    and line.y0 - previous.y1 < 1.2 * line.size
                ):
                    current.append(line)
                    continue
            bands.append((mode, current))
            current = []
        mode = line_mode
        current.append(line)
    if current and mode is not None:
        bands.append((mode, current))

    runs: list[list[Line]] = []
    for band_mode, band in bands:
        if band_mode == "full" or len(band) == 1:
            runs.append(sorted(band, key=lambda item: (item.y0, item.x0)))
            continue
        left_band = [line for line in band if line.center_x < mid]
        right_band = [line for line in band if line.center_x >= mid]
        if len(left_band) >= 2 and len(right_band) >= 2:
            runs.append(sorted(left_band, key=lambda item: (item.y0, item.x0)))
            runs.append(sorted(right_band, key=lambda item: (item.y0, item.x0)))
        else:
            runs.append(sorted(band, key=lambda item: (item.y0, item.x0)))
    return runs


def _is_heading(line: Line, body: float) -> bool:
    text = line.text.strip()
    if len(text) < 2 or len(text) > 48:
        return False
    if line.size > body + 1.0:
        return True
    return bool(
        HEADING_NUM.match(text) and len(text) <= 40 and not text.endswith(END_PUNCT)
    )


def group_paragraphs(run: list[Line], body: float) -> list[Block]:
    """把一条栏内行串还原成段落与标题。"""
    if not run:
        return []

    starts = sorted(line.x0 for line in run)
    column_left = starts[int(len(starts) * 0.1)]
    widths = sorted(line.width for line in run)
    column_width = widths[min(len(widths) - 1, int(len(widths) * 0.9))] or 1.0

    blocks: list[Block] = []
    current: list[Line] = []

    def flush() -> None:
        nonlocal current
        if not current:
            return
        text = ""
        for line in current:
            text = join_text(text, line.text)
        blocks.append(
            Block(
                kind="paragraph",
                text=normalize(text),
                lines=list(current),
                bbox=(
                    min(line.x0 for line in current),
                    min(line.y0 for line in current),
                    max(line.x1 for line in current),
                    max(line.y1 for line in current),
                ),
            )
        )
        current = []

    for line in run:
        if current:
            previous = current[-1]
            # 同一视觉行上的补字/重叠片段：直接并回，不新起段落
            if (
                abs(line.y0 - previous.y0) < 0.6 * max(line.size, previous.size)
                and line.x0 < previous.x1 - 2
            ):
                if previous.text.endswith("—") and line.text.startswith("—"):
                    line.text = line.text[1:]
                current.append(line)
                continue

        if _is_heading(line, body):
            flush()
            blocks.append(
                Block(
                    kind="heading",
                    text=line.text,
                    lines=[line],
                    bbox=(line.x0, line.y0, line.x1, line.y1),
                )
            )
            continue

        if not current:
            current = [line]
            continue

        prev = current[-1]
        # 首字下沉/单字孤行：并回下一行
        if len(prev.text) <= 1:
            current.append(line)
            continue
        gap = line.y0 - prev.y1
        line_height = max(line.size, 1.0)
        ends_sentence = prev.text.endswith(END_PUNCT)
        short_prev = prev.width < 0.82 * column_width
        indented = line.x0 - column_left > 1.4 * body

        new_paragraph = (
            gap > 1.5 * line_height
            or (ends_sentence and short_prev and gap > 0.25 * line_height)
            or indented
        )
        if new_paragraph:
            flush()
            current = [line]
        else:
            current.append(line)

    flush()
    return blocks


def split_footnotes(
    lines: list[Line], body: float, height: float, column_mid: float | None = None
) -> tuple[list[Line], list[Block]]:
    """切出脚注。

    双栏页里脚注可能只占一栏，而另一栏正文还在往下走，所以不能简单按 y 切：
    有「注释：」小标题时，只切该标题所在那一栏的下方；否则退回按 y 切。
    """
    ordered = sorted(lines, key=lambda line: (line.y0, line.x0))

    header = next((line for line in ordered if NOTE_HEADER.match(line.text)), None)
    if header is not None and column_mid is not None:
        on_right = header.center_x >= column_mid
        note_ids = {id(header)}
        note_lines: list[Line] = []
        for line in ordered:
            same_column = (line.center_x >= column_mid) == on_right
            if same_column and line.y0 >= header.y0 - 1:
                note_ids.add(id(line))
                if line is not header:
                    note_lines.append(line)
        body_lines = [line for line in ordered if id(line) not in note_ids]
        return body_lines, group_notes(_clean_notes(note_lines))

    start: int | None = None
    for index, line in enumerate(ordered):
        if line.y0 < 0.55 * height:
            continue
        if NOTE_START.match(line.text) and line.size <= body + 1.0:
            start = index
            break
        if line.y0 > 0.72 * height and line.size < body - 0.5:
            start = index
            break
    if start is None:
        return ordered, []

    body_lines = ordered[:start]
    return body_lines, group_notes(_clean_notes(ordered[start:]))


def _clean_notes(lines: list[Line]) -> list[Line]:
    return [
        line
        for line in lines
        if not PAGE_NO.match(line.text) and line.text.strip() not in {"·", "•"}
    ]


def group_notes(lines: list[Line]) -> list[Block]:
    notes: list[Block] = []
    current: list[Line] = []

    def flush() -> None:
        nonlocal current
        if not current:
            return
        text = ""
        for line in current:
            text = join_text(text, line.text)
        match = NOTE_START.match(text)
        notes.append(
            Block(
                kind="note",
                text=text,
                marker=match.group(0).strip() if match else "",
                lines=list(current),
                bbox=(
                    min(line.x0 for line in current),
                    min(line.y0 for line in current),
                    max(line.x1 for line in current),
                    max(line.y1 for line in current),
                ),
            )
        )
        current = []

    for line in lines:
        if NOTE_START.match(line.text) and current:
            flush()
        current.append(line)
    flush()
    return notes

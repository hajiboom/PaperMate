"""知网 PDF 文本清洗。

原则（见 .agent/mvp.md 第 9.2 节）：
- 只清除有把握的页眉、页脚、页码；
- 对无法确定的内容保留原文；
- 不编造内容。
"""

from __future__ import annotations

import re

# 每页内明显是页码的行：如 "12" "- 12 -" "·12·" "第 12 页"
PAGE_NUMBER_RE = re.compile(
    r"^\s*(?:[-—·•]?\s*\d{1,4}\s*[-—·•]?|第\s*\d{1,4}\s*页)\s*$"
)

# 知网常见页眉/页脚残留
NOISE_LINE_RE = re.compile(
    r"^\s*(?:"
    r"网络首发时间[:：].*"
    r"|网络首发地址[:：].*"
    r"|时间[:：]?\s*20\d\d[-/年]\d{1,2}[-/月]\d{1,2}.*"
    r"|网址[:：].*"
    r"|https?://\S+"
    r"|www\.\S+"
    r"|\d+\s*年\s*\d+\s*月.*第?\s*\d*\s*期.*"
    r"|·\s*\d+\s*·.*"
    r"|―+\s*\d+\s*―+"
    r"|—+\s*\d+\s*—+"
    r"|[─―—_=]{3,}.*"
    r"|[\s　·●○■□★☆◆◇]+$"
    r")\s*$"
)

# 页面上大量重复装饰字符（纯符号行）
DECORATION_RE = re.compile(r"^[\s　·．.。*#%-—―─_=]{4,}$")


def clean_page_text(text: str) -> str:
    """清洗单页文本，返回清洗后的多行文本（保留换行结构）。"""
    lines = text.splitlines()
    kept: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            # 保留空行作为段落分隔候选
            kept.append("")
            continue
        if PAGE_NUMBER_RE.match(stripped):
            continue
        if NOISE_LINE_RE.match(stripped):
            continue
        if DECORATION_RE.match(stripped):
            continue
        kept.append(line.rstrip())

    result = "\n".join(kept)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def normalize_spaces(line: str) -> str:
    """统一可见空白：全角空格转普通空格（标题/关键词行内部）。"""
    return line.replace("\u3000", " ").strip()

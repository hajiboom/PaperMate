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

# 期刊页眉/页脚里的「刊名 + 年份 + 期号」组合，作为子串删除（可能粘连正文）
JOURNAL_ISSUE_SUBS = (
    re.compile(r"《[^》]{1,25}》\s*20\d{2}\s*年\s*第\s*\d{1,3}\s*期(?:《[^》]{1,25}》)?"),
    re.compile(r"20\d{2}\s*年\s*第\s*\d{1,3}\s*期\s*《[^》]{1,25}》"),
    re.compile(r"DOI\s*[:：]\s*\S+", re.IGNORECASE),
)

# 独立的期刊期号行
ISSUE_LINE_RE = re.compile(r"^20\d{2}\s*年\s*第\s*\d{1,3}\s*期\s*$")

# 破折号开头的作者/标题页脚模式
DASH_PREFIX_RE = re.compile(r"^—{1,2}")
# 行首破折号前的短作者行（下一行以 —— 开头时一并删除）
SHORT_NAME_RE = re.compile(r"^[\u4e00-\u9fff]{1,4}$")
# 孤立符号行
LONE_SYMBOL_RE = re.compile(r"^[\s□○●◎◆◇▪◦○\[\]()（）·]+$")


def clean_page_text(text: str) -> str:
    """清洗单页文本，返回清洗后的多行文本（保留换行结构）。"""
    lines = text.splitlines()
    kept: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            # 保留空行作为段落分隔候选
            kept.append("")
            continue
        if PAGE_NUMBER_RE.match(stripped):
            continue
        if ISSUE_LINE_RE.match(stripped):
            continue
        if LONE_SYMBOL_RE.match(stripped):
            continue
        if DASH_PREFIX_RE.match(stripped):
            continue
        if (
            SHORT_NAME_RE.match(stripped)
            and i + 1 < len(lines)
            and DASH_PREFIX_RE.match(lines[i + 1].strip())
        ):
            continue

        # 期刊页眉（刊名+期号）、DOI 作为子串删除，保留粘连的后文
        for pattern in JOURNAL_ISSUE_SUBS:
            stripped = pattern.sub("", stripped)
        # 保留行首缩进（markdown 渲染依赖缩进判断分段）
        indent = line[: len(line) - len(line.lstrip())]
        cleaned = indent + stripped.lstrip()
        if not cleaned.strip():
            continue
        if NOISE_LINE_RE.match(stripped):
            continue
        if DECORATION_RE.match(stripped):
            continue
        kept.append(stripped)

    result = "\n".join(kept)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def normalize_spaces(line: str) -> str:
    """统一可见空白：全角空格转普通空格（标题/关键词行内部）。"""
    return line.replace("\u3000", " ").strip()

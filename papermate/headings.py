"""中文标题层级识别与章节标记识别。

针对知网社科论文常见层级：
- 一级：一、二、三、……
- 二级：（一）（二）（三）……
- 三级：1. 2. 3. ……

另有结构性标记：摘要 / 关键词 / 参考文献。
"""

from __future__ import annotations

import re

LEVEL1_RE = re.compile(r"^([一二三四五六七八九十]{1,3})\s*[、]\s*(.+)$")
LEVEL2_RE = re.compile(r"^[（(]([一二三四五六七八九十]{1,3})[)）]\s*(.+)$")
LEVEL3_RE = re.compile(r"^(\d{1,2})\s*[.、]\s*(.+)$")

# 结构性标记（按出现的行匹配）
ABSTRACT_RE = re.compile(r"^[\s　]*[【\[]?\s*摘\s*要\s*[:：\]】]?\s*(.*)$")
KEYWORDS_RE = re.compile(r"^[\s　]*[【\[]?\s*关\s*键\s*词\s*[:：\]】]?\s*(.*)$")
REFERENCE_RE = re.compile(r"^[\s　]*(\[?参考文献\]?|[参 考 文 献]+)\s*[:：]?\s*$")
DOI_RE = re.compile(r"DOI\s*[:：]", re.IGNORECASE)

_HEADING_MARKERS = ("一、", "二、", "三、", "四、", "五、", "六、", "七、", "八、", "九、", "十、")

# 句末标点：出现在行首数字编号后面的正文内容通常以这些结尾
_SENTENCE_END = tuple("。！？；")


def classify(line: str) -> dict | None:
    """判断一行是否为标题，返回 {'level': 1|2|3, 'text': 标题文本} 或 None。"""
    stripped = line.strip()
    if not stripped:
        return None
    # 去掉可能的页首残留标记
    stripped = re.sub(r"^<!--\s*Page\s*\d+\s*-->\s*$", "", stripped)
    if not stripped or len(stripped) > 60:
        return None

    match = LEVEL1_RE.match(stripped)
    if match and _looks_like_title(match.group(2)):
        return {"level": 1, "text": f"{match.group(1)}、{match.group(2).strip()}"}

    match = LEVEL2_RE.match(stripped)
    if match and _looks_like_title(match.group(2)):
        return {"level": 2, "text": f"（{match.group(1)}）{match.group(2).strip()}"}

    match = LEVEL3_RE.match(stripped)
    if match and _looks_like_title(match.group(2)):
        return {"level": 3, "text": f"{match.group(1)}. {match.group(2).strip()}"}

    return None


def _looks_like_title(text: str) -> bool:
    """过滤误匹配：列表项、句子、参考文献条目不是标题。"""
    text = text.strip()
    if not text or len(text) > 40:
        return False
    # 以句末标点结尾的多半是正文
    if text.endswith(_SENTENCE_END):
        return False
    # 含较多逗号/顿号的长句不是标题（允许少量顿号列举）
    if text.count("，") > 1 or text.count(",") > 1:
        return False
    # 纯数字/英文编号行
    if re.fullmatch(r"[\d\W]+", text):
        return False
    return True


def classify_line(line: str) -> str:
    """识别结构性标记行，返回 'abstract' | 'keywords' | 'references' | ''。"""
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return ""
    if ABSTRACT_RE.match(stripped):
        return "abstract"
    if KEYWORDS_RE.match(stripped):
        return "keywords"
    if REFERENCE_RE.match(stripped):
        return "references"
    return ""

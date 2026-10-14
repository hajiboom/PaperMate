"""Markdown 生成：text.md 构建，以及通用的 ## 章节提取（供 matrix 使用）。

规则：
- 中文标题层级统一输出为 ## 标题；
- 摘要 / 关键词 / 参考文献作为独立 ## 章节；
- 正文段落合并被换行切断的行；
- 识别不了的行原样保留，不编造。
"""

from __future__ import annotations

import re

from . import headings

_CJK_END_RE = re.compile(r"[\u4e00-\u9fff。，、；：？！）】》]$")
_LATIN_END_RE = re.compile(r"[A-Za-z0-9%]$")

SectionDict = dict[str, str]


_SENTENCE_ENDING = tuple("。！？；")


def build_text_md(title: str, pages: list[tuple[int, str]]) -> str:
    """把清洗后的页面文本组装成 text.md。"""
    out: list[str] = [f"# {title}", ""]
    for page_no, page_text in pages:
        out.append(f"<!-- Page {page_no} -->")
        out.append("")
        out.extend(_render_page(page_text, title))
        out.append("")
    text = "\n".join(out)
    # 压缩多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def _render_page(page_text: str, title: str = "") -> list[str]:
    """渲染单页：识别标题与结构标记，合并正文断行。

    换段规则：下一非空行带段首缩进（知网段落首行常见两个空格）时，
    或遇到空行/标题/结构标记时，才视为新段落。
    """
    out: list[str] = []
    buffer: list[str] = []  # 正文段落缓冲
    in_references = False
    title_key = title.replace(" ", "") if title else ""
    lines = page_text.splitlines()

    def flush() -> None:
        if buffer:
            out.append(_merge_lines(buffer))
            out.append("")
            buffer.clear()

    for idx, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush()
            continue

        # 跳过正文里重复出现的标题行（知网每页页眉常带论文标题）
        if title_key and stripped.replace(" ", "") == title_key:
            continue

        marker, inline = headings.classify_line(stripped)
        if marker == "abstract":
            flush()
            out.append("## 摘要")
            out.append("")
            if inline:
                buffer.append(inline)
            continue
        if marker == "keywords":
            flush()
            out.append("## 关键词")
            out.append("")
            if inline:
                out.append(inline)
                out.append("")
            continue
        if marker == "references":
            flush()
            out.append("## 参考文献")
            out.append("")
            in_references = True
            continue

        heading = headings.classify(stripped)
        if heading:
            if in_references and heading["level"] != 1:
                # 参考文献条目不是正文标题，保持原样
                out.append(stripped)
                out.append("")
                continue
            flush()
            # 一级标题可以终止参考文献状态
            if heading["level"] == 1:
                in_references = False
            out.append(f"## {heading['text']}")
            out.append("")
            continue

        if in_references:
            # 参考文献区：每条独占一段，不做合并
            out.append(stripped)
            out.append("")
            continue

        # 极短的无标点行（图注、表格残片、页眉残留）独立成行，不并入正文段落
        if len(stripped) <= 6 and not re.search(r"[，。；：？！,;:?.]", stripped):
            flush()
            out.append(stripped)
            out.append("")
            continue

        # 下一非空行带段首缩进 → 当前段落结束
        next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
        if buffer and _is_indented(next_line):
            flush()

        buffer.append(stripped)

    flush()
    return out


def _is_indented(line: str) -> bool:
    """判断一行是否带段首缩进（两个以上空格或全角空格开头）。"""
    if not line.strip():
        return False
    return line.startswith(("\u3000", "  "))


def _merge_lines(lines: list[str]) -> str:
    """合并被换行切断的段落：CJK 直接拼接，西文补空格。"""
    result = ""
    for line in lines:
        if not result:
            result = line
            continue
        if _LATIN_END_RE.search(result) and not _CJK_END_RE.search(line[:1]):
            result += " " + line
        else:
            result += line
    return result


def extract_sections(markdown_text: str) -> SectionDict:
    """把 Markdown 按 '## 章节名' 切开，返回 {章节名: 正文}。"""
    sections: SectionDict = {}
    current = ""
    body: list[str] = []

    for line in markdown_text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            if current:
                sections[current] = "\n".join(body).strip()
            current = match.group(1)
            body = []
        elif current:
            body.append(line)
    if current:
        sections[current] = "\n".join(body).strip()
    return sections


def compress_for_table(text: str, max_len: int = 60) -> str:
    """把多行内容压成表格单元格用的单行文本。"""
    text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    # 转义表格分隔符
    text = text.replace("|", "\\|")
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return text

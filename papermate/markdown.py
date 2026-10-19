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
    pages = _join_cross_page_sentences(pages)
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


# 页末断句：以这些字符结尾视为句子未完（跨页接续的判断条件）
_CJK_CONT_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9，、：,]$")
# 句子结束：续行移动到此为止
_SENTENCE_OVER_RE = re.compile(r"[。！？；…”』]$")


def _join_cross_page_sentences(
    pages: list[tuple[int, str]],
) -> list[tuple[int, str]]:
    """跨页断句接续：上一页末行句子未完时，把下一页的续行移上去。

    续行整体移动直到句子结束（或遇到段落边界/标题/缩进新段落），
    保证接缝落在句子边界而不是词中间；不改变页码标记的位置。
    """
    joined: list[tuple[int, str]] = []
    for page_no, text in pages:
        lines = text.splitlines()
        if joined:
            prev_no, prev_text = joined[-1]
            last = _last_nonempty(prev_text.splitlines())
            first_idx = _first_nonempty(lines)
            if (
                last
                and first_idx is not None
                and not last.startswith("<!--")
                and not lines[first_idx].startswith("<!--")
                and not lines[first_idx].startswith((" ", "\u3000"))  # 缩进 = 新段落
                and _CJK_CONT_RE.search(last)
                and _is_continuation_line(lines[first_idx])
            ):
                moved = 0
                for k in range(first_idx, len(lines)):
                    cur = lines[k].strip()
                    if not cur:  # 空行 = 段落边界
                        break
                    if k > first_idx and (
                        lines[k].startswith((" ", "\u3000"))
                        or cur.startswith("<!--")
                        or headings.classify(cur)
                        or headings.classify_line(cur)[0]
                    ):
                        break
                    prev_text = f"{prev_text}\n{cur}"
                    moved += 1
                    if _SENTENCE_OVER_RE.search(cur):
                        break
                if moved:
                    joined[-1] = (prev_no, prev_text)
                    del lines[first_idx : first_idx + moved]
        joined.append((page_no, "\n".join(lines).strip()))
    return joined


def _last_nonempty(lines: list[str]) -> str:
    for line in reversed(lines):
        if line.strip():
            return line.strip()
    return ""


def _first_nonempty(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        if line.strip():
            return i
    return None


def _is_continuation_line(line: str) -> bool:
    """下一页首行是否像被截断的句子续行（而非新段落/标题/标记）。"""
    stripped = line.strip()
    if len(stripped) < 6:
        return False
    if headings.classify(stripped) or headings.classify_line(stripped)[0]:
        return False
    return True


def _render_page(page_text: str, title: str = "") -> list[str]:
    """渲染单页：识别标题与结构标记，合并正文断行。

    换段规则：下一非空行带段首缩进（知网段落首行常见两个空格）时，
    或遇到空行/标题/结构标记时，才视为新段落。
    """
    out: list[str] = []
    buffer: list[str] = []  # 正文段落缓冲
    in_references = False
    title_key = title.replace(" ", "") if title else ""
    lines = _mask_figure_blocks(page_text.splitlines())

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

        # 折叠注释 / 省略注释原样透传，不并入正文
        if stripped.startswith("<!--"):
            flush()
            out.append(stripped)
            out.append("")
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
            # 标题在 PDF 里被折成两行时，紧随其后的短行并入标题
            cont = _consume_heading_continuation(lines, idx)
            out.append(f"## {heading['text']}{cont}")
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


def _mask_figure_blocks(lines: list[str]) -> list[str]:
    """把连续多行的短碎片（图表文字块）折叠成一条注释。

    知网的示意图/流程图由文字框拼成，文本层逐行散出"上海市""人大常"
    这类 2~12 字碎片；连续出现 4 行以上时整块判为图表并折叠，
    避免污染正文。图注（"图1 ..."）通常超过 12 字，不受影响。
    """
    def is_fragment(s: str) -> bool:
        return (
            bool(s)
            and len(s) <= 12
            and not re.search(r"[。！？；…]", s)
            and not s.startswith("<!--")
            and headings.classify(s) is None
            and not headings.classify_line(s)[0]
        )

    out: list[str] = []
    run: list[str] = []  # 当前碎片行
    blanks: list[str] = []  # 碎片块内部的空行（不打断块，最多容忍连续空行）

    def flush() -> None:
        if len(run) >= 4:
            out.append(f"<!-- 图表文字块（{len(run)} 行碎片），已折叠 -->")
        else:
            out.extend(run)
        out.extend(blanks)
        run.clear()
        blanks.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if run:
                blanks.append(line)  # 碎片块内的空行暂挂，不立即输出
            else:
                out.append(line)
            continue
        if is_fragment(stripped):
            run.append(line)
            blanks.clear()  # 碎片之间的空行视作块内噪音
            continue
        flush()
        out.append(line)
    flush()
    return out


def _consume_heading_continuation(lines: list[str], idx: int) -> str:
    """若标题行在 PDF 中被折成两行，把紧随其后的短行并入标题并消费掉。

    例如"一、22个……内部运行结" + 下一行"构类型化分析" → 合并为一个标题。
    返回拼在标题后的文本（含前导空格），无续行时返回 ""。
    """
    j = idx + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j >= len(lines):
        return ""
    nxt = lines[j].strip()
    if (
        1 <= len(nxt) <= 12
        and not re.search(r"[。！？；…]$", nxt)
        and not nxt.startswith("<!--")
        and not nxt.startswith((" ", "\u3000"))  # 缩进说明是新段落
        and headings.classify(nxt) is None
        and not headings.classify_line(nxt)[0]
    ):
        lines[j] = ""
        return nxt
    return ""


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

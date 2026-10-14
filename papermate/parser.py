"""PDF 解析（PyMuPDF）。

只负责提取：页面文本、PDF 元数据、标题候选。不做任何学术判断。
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path

try:  # PyMuPDF >= 1.28 推荐 import pymupdf，旧版只有 fitz
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore[no-redef]

from .cleaner import clean_page_text

# 标题候选的最小/最大长度
_TITLE_MIN_LEN = 4
_TITLE_MAX_LEN = 60

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


class PdfParseError(Exception):
    """PDF 解析失败。"""


def parse_pdf(pdf_path: str | Path) -> dict:
    """解析 PDF，返回 {'metadata', 'pages', 'page_count', 'title_hint'}。

    pages: [(page_number, cleaned_text), ...]，page_number 从 1 开始。
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise PdfParseError(f"PDF 文件不存在：{path}")

    if path.suffix.lower() != ".pdf":
        raise PdfParseError(f"不是 PDF 文件：{path}")

    try:
        doc = fitz.open(path)
    except Exception as exc:  # PyMuPDF 打不开的损坏文件
        raise PdfParseError(f"无法打开 PDF（文件可能损坏）：{path}（{exc}）") from exc

    try:
        if doc.is_encrypted:
            raise PdfParseError("PDF 已加密，无法解析。")
        if doc.page_count == 0:
            raise PdfParseError("PDF 没有任何页面，无法解析。")

        metadata = doc.metadata or {}
        pages: list[tuple[int, str]] = []
        for page_num, page in enumerate(doc, 1):
            raw = page.get_text("text")
            cleaned = clean_page_text(raw)
            pages.append((page_num, cleaned))

        # 判断是否解析到了任何文字（扫描版 PDF 会得到空文本）
        if not any(text.strip() for _, text in pages):
            raise PdfParseError(
                "PDF 中没有提取到任何文字，可能是扫描版（图片型）PDF。"
                "第一版不支持 OCR，请使用文字版 PDF。"
            )

        title_hint = _extract_title_from_layout(doc) or _clean_title(
            metadata.get("title", "")
        )
        year_hint = _extract_year_hint(
            [text for _, text in pages], metadata.get("creationDate", "") or ""
        )

        return {
            "metadata": {
                "title": _clean_title(metadata.get("title", "")),
                "author": _clean_title(metadata.get("author", "")),
                "creation_date": metadata.get("creationDate", "") or "",
            },
            "pages": pages,
            "page_count": doc.page_count,
            "title_hint": title_hint,
            "year_hint": year_hint,
        }
    finally:
        doc.close()


def _extract_year_hint(page_texts: list[str], creation_date: str) -> str:
    """从前两页文本中推断发表年份（多个候选时取出现最多的）。"""
    first_pages = "\n".join(page_texts[:2])
    this_year = date.today().year
    candidates = [
        y
        for y in re.findall(r"(?:19|20)\d{2}", first_pages)
        if 1990 <= int(y) <= this_year
    ]
    if candidates:
        return Counter(candidates).most_common(1)[0][0]
    match = re.search(r"D:(\d{4})", creation_date)
    return match.group(1) if match else ""


def _extract_title_from_layout(doc: "fitz.Document") -> str:
    """从第 1 页版面提取标题：取字号最大、以中文为主的那一行文本。"""
    try:
        page = doc[0]
        spans: list[tuple[float, str]] = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                line_text = ""
                line_size = 0.0
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text:
                        line_text += text
                        line_size = max(line_size, span.get("size", 0.0))
                line_text = line_text.strip()
                if (
                    line_text
                    and _TITLE_MIN_LEN <= len(line_text) <= _TITLE_MAX_LEN
                    and _cjk_ratio(line_text) >= 0.3
                ):
                    spans.append((line_size, line_text))
        if not spans:
            return ""
        spans.sort(key=lambda item: item[0], reverse=True)
        top = spans[0][0]
        # 与最大字号接近的行拼接（标题可能被拆成多行）
        candidates = [text for size, text in spans if size >= top - 0.5]
        candidates = candidates[:2]
        return _clean_title("".join(candidates))
    except Exception:
        return ""


def _cjk_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(_CJK_RE.findall(text)) / len(text)


def _clean_title(raw: str) -> str:
    title = (raw or "").replace("\n", " ").strip()
    title = re.sub(r"\s+", " ", title)
    # 知网常见垃圾标题
    if not title or re.fullmatch(r"(?i)(untitled|unknown|none|\W+)", title):
        return ""
    return title

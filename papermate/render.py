"""把结构化 Document 渲染成 Markdown（带页码锚点）和 JSON。"""

from __future__ import annotations

import json
import re
from dataclasses import asdict

from .model import Block, Document

AFFILIATION_RE = re.compile(r"(课题组|大学|学院|研究院|研究所|党校|委员会)")


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", "<br>")


def render_table(rows: list[list[str]] | None) -> str:
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    header = "| " + " | ".join(_cell(cell) for cell in normalized[0]) + " |"
    divider = "|" + "---|" * width
    body = [
        "| " + " | ".join(_cell(cell) for cell in row) + " |"
        for row in normalized[1:]
    ]
    return "\n".join([header, divider, *body])


def render_block(block: Block) -> str:
    if block.kind == "heading":
        if len(block.text) < 40 and AFFILIATION_RE.search(block.text):
            return block.text
        return f"## {block.text}"
    if block.kind == "table":
        caption = f"**{block.caption}**\n\n" if block.caption else ""
        return f"{caption}{render_table(block.rows)}".strip()
    if block.kind == "figure":
        parts: list[str] = []
        if block.caption:
            parts.append(f"**{block.caption}**")
        if block.text:
            parts.append(block.text)
        if block.note:
            parts.append(f"（{block.note}）")
        return "\n\n".join(parts) if parts else "[图]"
    return block.text


def render_markdown(document: Document) -> str:
    parts: list[str] = []
    if document.title:
        parts.append(f"# {document.title}")

    for page in document.pages:
        parts.append(f"<!-- Page {page.page} -->")
        for block in page.blocks:
            if (
                page.page == 1
                and block.kind == "heading"
                and document.title
                and block.text
                and block.text in document.title
            ):
                continue
            rendered = render_block(block).strip()
            if rendered:
                parts.append(rendered)
        if page.footnotes:
            parts.append("**脚注**")
            for note in page.footnotes:
                parts.append(note.text)
        if page.flags.get("scanned"):
            parts.append("> 本页几乎无可提取文本，可能是扫描页，需要 OCR 后才能核对。")

    return "\n\n".join(parts) + "\n"


def render_json(document: Document) -> str:
    return json.dumps(asdict(document), ensure_ascii=False, indent=2)

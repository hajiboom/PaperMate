"""meta.md（YAML frontmatter）的读写。

只用最小实现，避免引入 PyYAML 之类的额外依赖：
meta.md 是我们自己生成的，格式固定，字符串值一律加双引号。
"""

from __future__ import annotations

import re
from pathlib import Path

# 用户可设置的受控取值
STATUS_VALUES = ("unread", "skimming", "close_reading", "archived", "rejected")
READING_RECOMMENDATION_VALUES = (
    "skip",
    "skim",
    "cautious_close_read",
    "important_close_read",
)
USER_LABEL_VALUES = (
    "useful",
    "weak_evidence",
    "worth_reading",
    "background_only",
    "policy_useful",
    "method_reference",
    "doubtful",
    "reject",
)

# CLI 能从 PDF 提取的字段顺序，其余字段保留默认
META_FIELDS = (
    "title",
    "authors",
    "year",
    "venue",
    "keywords",
    "tags",
    "added_at",
    "source_pdf",
    "status",
    "reading_recommendation",
    "user_label",
)

_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")


def load_meta(paper_dir: Path) -> dict:
    """读取 meta.md 的 frontmatter。文件缺失或损坏时返回最小骨架。"""
    meta = {field: "" for field in META_FIELDS}
    meta["status"] = "unread"

    meta_path = paper_dir / "meta.md"
    if not meta_path.is_file():
        return meta

    text = meta_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return meta
    end = text.find("\n---", 3)
    if end < 0:
        return meta
    block = text[3:end]

    for line in block.splitlines():
        match = _LINE_RE.match(line.strip())
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        value = _unquote(value)
        if key in meta:
            meta[key] = value
    return meta


def save_meta(paper_dir: Path, meta: dict) -> None:
    """把 meta 写成 meta.md（覆盖）。"""
    lines = ["---"]
    for field in META_FIELDS:
        lines.append(f"{field}: {_quote(str(meta.get(field, '')))}")
    lines.append("---")
    (paper_dir / "meta.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def init_meta(paper_dir: Path, meta: dict) -> None:
    """新建 meta.md，不覆盖已有内容。"""
    if (paper_dir / "meta.md").exists():
        return
    save_meta(paper_dir, meta)


def _quote(value: str) -> str:
    if value == "":
        return '""'
    if re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _unquote(value: str) -> str:
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        inner = value[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    return value

"""INDEX.md 管理。"""

from __future__ import annotations

from pathlib import Path


def append_entry(index_path: Path, entry: dict) -> bool:
    """向 INDEX.md 追加一行论文条目。

    entry: {'date', 'title', 'tags', 'recommendation', 'label', 'path'}
    已存在相同路径的条目时跳过，返回 False。
    """
    header = "| 日期 | 标题 | 主题 | 阅读建议 | 用户判断 | 路径 |"
    separator = "|---|---|---|---|---|---|"

    row = _format_row(entry)
    row_path = entry["path"]

    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        if row_path in content:
            return False  # 不重复登记
    else:
        content = f"# 文献索引\n\n{header}\n{separator}\n"

    # 保证有表头（用户可能手工删过）
    if header not in content:
        content = f"# 文献索引\n\n{header}\n{separator}\n" + content

    content = content.rstrip("\n") + "\n" + row + "\n"
    index_path.write_text(content, encoding="utf-8")
    return True


def _format_row(entry: dict) -> str:
    def cell(value: str) -> str:
        text = str(value or "").replace("|", "\\|").replace("\n", " ").strip()
        return text or " "

    return (
        f"| {cell(entry.get('date', ''))} "
        f"| {cell(entry.get('title', ''))} "
        f"| {cell(entry.get('tags', ''))} "
        f"| {cell(entry.get('recommendation', ''))} "
        f"| {cell(entry.get('label', ''))} "
        f"| {cell(entry.get('path', ''))} |"
    )

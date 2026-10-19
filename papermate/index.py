"""INDEX.md 管理。"""

from __future__ import annotations

import re
from pathlib import Path

# 表格分隔符：不吞掉值里转义的 \|
_CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")


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
        # 按整行路径单元格精确匹配，避免 "-2" 后缀文件夹的前缀误判
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|") or stripped.startswith(("| 日期", "|---")):
                continue
            cells = _CELL_SPLIT_RE.split(stripped.strip("|"))
            if len(cells) == 6 and cells[5].strip() == row_path:
                return False  # 不重复登记
    else:
        content = f"# 文献索引\n\n{header}\n{separator}\n"

    # 保证有表头（用户可能手工删过）
    if header not in content:
        content = f"# 文献索引\n\n{header}\n{separator}\n" + content

    content = content.rstrip("\n") + "\n" + row + "\n"
    index_path.write_text(content, encoding="utf-8")
    return True


def refresh_entries(index_path: Path, metas: dict[str, dict]) -> bool:
    """用各论文的 meta.md 回刷 INDEX.md 的主题 / 阅读建议 / 用户判断列。

    metas: {论文文件夹名: meta dict}。行按路径字段匹配论文文件夹，
    parse 时留空的列在共读 agent 更新 meta 后得以补齐。其余列不动。
    返回是否有改动。
    """
    if not index_path.exists():
        return False

    lines = index_path.read_text(encoding="utf-8").splitlines()
    changed = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith(("| 日期", "|---")):
            continue
        cells = _CELL_SPLIT_RE.split(stripped.strip("|"))
        if len(cells) != 6:
            continue
        folder = (
            cells[5].replace("\\|", "|").strip().rstrip("/").rsplit("/", 1)[-1].strip()
        )
        meta = metas.get(folder)
        if not meta:
            continue
        new_cells = [
            cells[0],
            cells[1],
            _cell(meta.get("tags", "")),
            _cell(meta.get("reading_recommendation", "")),
            _cell(meta.get("user_label", "")),
            cells[5],
        ]
        new_line = "| " + " | ".join(cell.strip() for cell in new_cells) + " |"
        if new_line != line:
            lines[i] = new_line
            changed = True

    if changed:
        index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


def _cell(value: str) -> str:
    text = str(value or "").replace("|", "\\|").replace("\n", " ").strip()
    return text or " "


def _format_row(entry: dict) -> str:
    return (
        f"| {_cell(entry.get('date', ''))} "
        f"| {_cell(entry.get('title', ''))} "
        f"| {_cell(entry.get('tags', ''))} "
        f"| {_cell(entry.get('recommendation', ''))} "
        f"| {_cell(entry.get('label', ''))} "
        f"| {_cell(entry.get('path', ''))} |"
    )

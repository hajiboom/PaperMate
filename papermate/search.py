"""本地关键词搜索：在每篇论文的 Markdown 文件里做简单字符串搜索。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SEARCH_FILES = (
    "meta.md",
    "text.md",
    "brief.md",
    "critique.md",
    "notes.md",
    "slides.md",
    "state.md",
)

_SNIPPET_WIDTH = 30  # 片段前后各保留的字符数


@dataclass
class Hit:
    paper: str
    file: str
    line_no: int
    snippet: str

    def format(self) -> str:
        return f"    文件：{self.file}\n    片段：……{self.snippet}……"


def search(library_papers_dir: Path, keyword: str) -> list[Hit]:
    """在 papers/ 下搜索关键词，返回命中列表（按论文、文件排序）。"""
    keyword = keyword.strip()
    if not keyword:
        return []

    needle = keyword.lower()
    hits: list[Hit] = []
    if not library_papers_dir.exists():
        return []

    for paper_dir in sorted(p for p in library_papers_dir.iterdir() if p.is_dir()):
        for file_name in SEARCH_FILES:
            file_path = paper_dir / file_name
            if not file_path.is_file():
                continue
            try:
                lines = file_path.read_text(encoding="utf-8").splitlines()
            except Exception:
                continue
            for line_no, line in enumerate(lines, 1):
                if needle in line.lower():
                    hits.append(
                        Hit(
                            paper=paper_dir.name,
                            file=file_name,
                            line_no=line_no,
                            snippet=_snippet(line, needle),
                        )
                    )
    return hits


def _snippet(line: str, needle: str) -> str:
    lower = line.lower()
    index = lower.find(needle)
    if index < 0:
        index = 0
    start = max(0, index - _SNIPPET_WIDTH)
    end = min(len(line), index + len(needle) + _SNIPPET_WIDTH)
    snippet = line[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(line):
        snippet = snippet + "…"
    return snippet

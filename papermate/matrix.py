"""文献矩阵聚合。

CLI 只负责聚合每篇论文已有的 meta.md / brief.md / critique.md，
不做任何学术判断；字段缺失时填「未提供」。
"""

from __future__ import annotations

from pathlib import Path

from .library import Library
from .markdown import compress_for_table, extract_sections
from .meta import load_meta

NOT_PROVIDED = "未提供"

# brief.md 中需要聚合的章节 → 矩阵列
BRIEF_SECTIONS = ("研究问题", "理论视角", "研究方法", "数据来源", "核心结论")


def build_matrix(library: Library) -> tuple[str, int]:
    """聚合所有论文，返回 (matrix.md 内容, 论文行数)。"""
    header = "# 文献矩阵\n\n"
    header += (
        "| 标题 | 年份 | 研究问题 | 理论视角 | 研究方法 "
        "| 数据来源 | 核心结论 | 主要局限 | 可借鉴点 |\n"
    )
    header += "|---|---|---|---|---|---|---|---|---|\n"

    rows: list[str] = []
    for paper_dir in library.paper_dirs():
        meta = load_meta(paper_dir)
        brief = _read(paper_dir / "brief.md")
        critique = _read(paper_dir / "critique.md")

        brief_sections = extract_sections(brief) if brief else {}
        critique_sections = extract_sections(critique) if critique else {}

        title = meta.get("title", "") or paper_dir.name
        year = meta.get("year", "") or NOT_PROVIDED

        def brief_cell(name: str) -> str:
            value = brief_sections.get(name, "")
            return compress_for_table(value) if value else NOT_PROVIDED

        limitation = critique_sections.get("主要风险", "")
        limitation = limitation or critique_sections.get("风险与问题", "")
        reference = critique_sections.get("使用建议", "")
        if not reference:
            reference = critique_sections.get("使用建议", "")

        rows.append(
            "| {title} | {year} | {question} | {theory} | {method} | {data} "
            "| {conclusion} | {limitation} | {reference} |".format(
                title=compress_for_table(title),
                year=year or NOT_PROVIDED,
                question=brief_cell("研究问题"),
                theory=brief_cell("理论视角"),
                method=brief_cell("研究方法"),
                data=brief_cell("数据来源"),
                conclusion=brief_cell("核心结论"),
                limitation=compress_for_table(limitation) if limitation else NOT_PROVIDED,
                reference=compress_for_table(reference) if reference else NOT_PROVIDED,
            )
        )

    body = header + "\n".join(rows) + ("\n" if rows else "")
    return body, len(rows)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""

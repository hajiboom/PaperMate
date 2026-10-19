"""CLI 入口（Click）。

papermate 只负责文件处理和本地整理：
init / parse / list / show / matrix / search
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path

import click

from . import parser as pdf_parser
from . import search as search_mod
from .cleaner import normalize_spaces
from .index import append_entry, refresh_entries
from .library import PAPER_FILES, Library, default_library_root, write_template_file
from .markdown import build_text_md
from .meta import load_meta, save_meta


def _dir_option(func):
    """所有命令共用 --dir 参数。"""
    return click.option(
        "--dir",
        "library_dir",
        default=None,
        type=click.Path(file_okay=False, path_type=Path),
        help="工作区目录（默认 ./research-library）",
    )(func)


@click.group()
@click.version_option(package_name="papermate", prog_name="papermate")
def main() -> None:
    """PaperMate —— 社科论文共读助手（本地 CLI，配合 OpenCode Skill 使用）。"""


def _resolve_library(library_dir: Path | None) -> Library:
    root = Path(library_dir) if library_dir else default_library_root()
    return Library(root)


@main.command()
@_dir_option
def init(library_dir: Path | None) -> None:
    """初始化本地工作区。"""
    library = _resolve_library(library_dir)
    if library.init():
        click.echo(f"已初始化工作区：{library.root}")
        click.echo(f"  {library.papers_dir}")
        click.echo(f"  {library.matrix_dir}")
        click.echo(f"  {library.weekly_dir}")
        click.echo(f"  {library.index_path}")
    else:
        click.echo(f"工作区已存在，未做任何改动：{library.root}")


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@_dir_option
@click.option("--title", default=None, help="手动指定论文标题")
@click.option("--tags", default=None, help="主题标签，逗号分隔")
@click.option("--force", is_flag=True, help="重复解析时覆盖当天已生成的论文文件夹")
def parse(pdf_path: Path, library_dir: Path | None, title: str | None, tags: str | None, force: bool) -> None:
    """解析知网 PDF，生成论文文件夹和 text.md / meta.md。"""
    library = _resolve_library(library_dir)
    library.init()  # 工作区不存在时顺带初始化（不覆盖已有数据）

    click.echo(f"正在解析：{pdf_path}")
    try:
        result = pdf_parser.parse_pdf(pdf_path)
    except pdf_parser.PdfParseError as exc:
        raise click.ClickException(str(exc)) from exc

    # 确定标题
    paper_title = title or result["title_hint"]
    if not paper_title:
        paper_title = _guess_title_from_text(result["pages"])
    if not paper_title:
        raise click.ClickException(
            "无法确定论文标题：PDF 版面与元数据中都没有可用的标题，"
            "请用 --title \"论文标题\" 手动指定。"
        )
    paper_title = normalize_spaces(paper_title)

    # 创建论文文件夹
    paper_dir = library.new_paper_dir(paper_title, force=force)
    click.echo(f"论文文件夹：{paper_dir}")

    # 复制原始 PDF
    shutil.copyfile(pdf_path, paper_dir / "source.pdf")

    # 生成 text.md
    text_md = build_text_md(paper_title, result["pages"])
    (paper_dir / "text.md").write_text(text_md, encoding="utf-8")

    # 从正文提取摘要 / 关键词兜底
    abstract, keywords = _extract_abstract_keywords(text_md)

    # 生成 meta.md
    meta = load_meta(paper_dir)
    meta["title"] = paper_title
    if result["metadata"]["author"] and not meta.get("authors"):
        meta["authors"] = result["metadata"]["author"]
    if result.get("year_hint") and not meta.get("year"):
        meta["year"] = result["year_hint"]
    meta["keywords"] = keywords
    meta["tags"] = tags or ""
    meta["added_at"] = date.today().isoformat()
    meta["source_pdf"] = str(pdf_path)
    save_meta(paper_dir, meta)

    # 生成 notes.md / state.md
    write_template_file(paper_dir / "notes.md", "notes.md")
    write_template_file(paper_dir / "state.md", "state.md")

    # 更新 INDEX.md
    added = append_entry(
        library.index_path,
        {
            "date": date.today().isoformat(),
            "title": paper_title,
            "tags": tags or "",
            "recommendation": "",
            "label": "",
            "path": f"papers/{paper_dir.name}",
        },
    )
    if not added:
        click.echo("INDEX.md 中已有该论文条目，未重复登记。")

    click.echo(f"完成：{result['page_count']} 页，已生成 {paper_dir.name}/ 下的")
    click.echo("  source.pdf text.md meta.md notes.md state.md")
    if abstract:
        click.echo(f"摘要：{abstract[:40]}…")


def _guess_title_from_text(pages: list[tuple[int, str]]) -> str:
    """兜底：取第 1 页前几行中最像标题的一行。"""
    for _, page_text in pages[:1]:
        for line in page_text.splitlines():
            stripped = line.strip()
            if 4 <= len(stripped) <= 60 and not stripped.startswith(("摘", "关键词")):
                return stripped
    return ""


def _sync_index(library: Library) -> bool:
    """用各论文 meta.md 的最新受控字段回刷 INDEX.md。

    parse 登记时阅读建议/用户判断为空，共读 agent 更新 meta 后，
    任何 list / matrix 调用都会把 INDEX.md 补齐。返回是否有改动。
    """
    metas = {d.name: load_meta(d) for d in library.paper_dirs()}
    return refresh_entries(library.index_path, metas)


def _extract_abstract_keywords(text_md: str) -> tuple[str, str]:
    """从生成的 text.md 中提取摘要正文与关键词（用于 meta.md）。"""
    abstract = ""
    keywords = ""

    in_abstract = False
    for line in text_md.splitlines():
        if line.startswith("## "):
            in_abstract = line.startswith("## 摘要")
            continue
        if in_abstract and line.strip() and not line.startswith("<!--"):
            abstract += line.strip()

    match = re.search(r"^##\s*关键词\s*\n+\s*(.+)$", text_md, re.MULTILINE)
    if match:
        keywords = match.group(1).strip()

    # meta 字段截断，避免过长
    return abstract[:200], keywords[:120]


@main.command("list")
@_dir_option
@click.option("--json", "as_json", is_flag=True, help="以 JSON 输出")
def list_papers(library_dir: Path | None, as_json: bool) -> None:
    """列出本地论文。"""
    library = _resolve_library(library_dir)
    if _sync_index(library) and not as_json:
        click.echo("INDEX.md 已根据各论文 meta.md 更新。")
    papers = []
    for paper_dir in library.paper_dirs():
        meta = load_meta(paper_dir)
        papers.append(
            {
                "slug": paper_dir.name,
                "title": meta.get("title", ""),
                "status": meta.get("status", ""),
                "path": str(paper_dir),
            }
        )
    if as_json:
        click.echo(json.dumps(papers, ensure_ascii=False, indent=2))
        return
    if not papers:
        click.echo("工作区中还没有论文。先运行：papermate parse <pdf>")
        return
    for item in papers:
        click.echo(item["slug"])
        click.echo(f"  标题：{item['title'] or '（未提取到标题）'}")
        click.echo(f"  状态：{item['status'] or 'unread'}")
        click.echo(f"  路径：{item['path']}")


@main.command()
@_dir_option
@click.option("--json", "as_json", is_flag=True, help="以 JSON 输出")
@click.argument("paper_slug")
def show(paper_slug: str, library_dir: Path | None, as_json: bool) -> None:
    """查看某篇论文的信息。"""
    library = _resolve_library(library_dir)
    paper_dir = library.find_paper(paper_slug)
    if paper_dir is None:
        raise click.ClickException(f"找不到论文：{paper_slug}（用 papermate list 查看）")

    meta = load_meta(paper_dir)
    files = {name: (paper_dir / name).is_file() for name in PAPER_FILES}

    if as_json:
        click.echo(
            json.dumps(
                {"slug": paper_dir.name, "path": str(paper_dir), "meta": meta, "files": files},
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    click.echo(f"论文：{paper_dir.name}")
    click.echo(f"路径：{paper_dir}")
    click.echo("meta.md：")
    for key, value in meta.items():
        click.echo(f"  {key}: {value}")
    click.echo("文件：")
    for name, exists in files.items():
        click.echo(f"  {'[有]' if exists else '[无]'} {name}")


@main.command()
@_dir_option
def matrix(library_dir: Path | None) -> None:
    """聚合多篇论文笔记，生成文献矩阵 matrix.md。"""
    from .matrix import NOT_PROVIDED, build_matrix

    library = _resolve_library(library_dir)
    if not library.papers_dir.exists():
        raise click.ClickException(f"工作区不存在：{library.root}（先运行 papermate init）")
    if not library.paper_dirs():
        click.echo("还没有论文，先运行：papermate parse <pdf>")
        return

    content, count = build_matrix(library)
    matrix_path = library.matrix_dir / "matrix.md"
    matrix_path.write_text(content, encoding="utf-8")
    if _sync_index(library):
        click.echo("INDEX.md 已根据各论文 meta.md 更新。")
    click.echo(f"已生成 {matrix_path}（{count} 篇论文）")
    rows_missing = content.count(NOT_PROVIDED)
    if rows_missing:
        click.echo(
            "提示：矩阵中有「未提供」字段。"
            "brief.md / critique.md 由共读 Skill 生成，可先在共读中补齐后重新运行 papermate matrix。"
        )


@main.command()
@_dir_option
@click.argument("keyword")
def search(keyword: str, library_dir: Path | None) -> None:
    """在本地论文笔记中搜索关键词。"""
    library = _resolve_library(library_dir)
    hits = search_mod.search(library.papers_dir, keyword)
    if not hits:
        click.echo(f"未搜索到包含「{keyword}」的笔记。")
        return

    click.echo(f"关键词「{keyword}」共命中 {len(hits)} 处：")
    current_paper = None
    for hit in hits:
        if hit.paper != current_paper:
            click.echo(f"- {hit.paper}")
            current_paper = hit.paper
        click.echo(hit.format())


if __name__ == "__main__":
    main()

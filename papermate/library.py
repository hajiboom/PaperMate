"""本地工作区（research-library/）管理。"""

from __future__ import annotations

import re
from pathlib import Path
from datetime import date

import papermate

DEFAULT_LIBRARY_NAME = "research-library"
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

PAPER_FILES = (
    "source.pdf",
    "text.md",
    "meta.md",
    "brief.md",
    "critique.md",
    "slides.md",
    "notes.md",
    "state.md",
)


def default_library_root() -> Path:
    return Path.cwd() / DEFAULT_LIBRARY_NAME


class Library:
    """research-library/ 工作区。"""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.papers_dir = self.root / "papers"
        self.matrix_dir = self.root / "matrix"
        self.weekly_dir = self.root / "weekly"
        self.index_path = self.root / "INDEX.md"

    # ---------- init ----------

    def init(self) -> bool:
        """初始化工作区。已存在时不动用户数据，返回是否实际创建了目录。"""
        if self.index_path.exists() or self.papers_dir.exists():
            return False
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.matrix_dir.mkdir(parents=True, exist_ok=True)
        self.weekly_dir.mkdir(parents=True, exist_ok=True)
        write_template_file(self.index_path, "INDEX.md")
        return True

    # ---------- papers ----------

    def paper_dirs(self) -> list[Path]:
        if not self.papers_dir.exists():
            return []
        return sorted(d for d in self.papers_dir.iterdir() if d.is_dir())

    def find_paper(self, paper_slug: str) -> Path | None:
        """按论文 slug（文件夹名）查找，允许忽略首尾空格。"""
        target = (self.papers_dir / paper_slug.strip()).resolve()
        if not target.exists() or not target.is_dir():
            return None
        # 防止 ../ 逃逸出 papers/
        if self.papers_dir.resolve() not in target.parents:
            return None
        return target

    def new_paper_dir(self, title: str, force: bool = False) -> Path:
        """创建论文文件夹：papers/YYYY-MM-DD__短标题。

        force 为 True 时，若今天的同名文件夹已存在（重复解析同一篇），
        直接复用该文件夹而不另建 -2 后缀目录。
        """
        slug_date = date.today().isoformat()
        slug = make_slug(title)
        folder_name = f"{slug_date}__{slug}"
        paper_dir = self.papers_dir / folder_name
        if force and paper_dir.exists():
            return paper_dir
        counter = 2
        while paper_dir.exists():
            paper_dir = self.papers_dir / f"{folder_name}-{counter}"
            counter += 1
        paper_dir.mkdir(parents=True)
        return paper_dir

    def paper_file(self, paper_dir: Path, name: str) -> Path | None:
        path = paper_dir / name
        return path if path.is_file() else None


def make_slug(title: str) -> str:
    """由标题生成文件夹短名：去掉非法字符、空格换连字符、限长。"""
    slug = (title or "").strip()
    slug = re.sub(r"[\\/:*?\"<>|\r\n\t]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = slug.strip("-. ")
    if not slug:
        slug = "untitled"
    return slug[:24]


def write_template_file(target: Path, template_name: str) -> None:
    """把 templates/ 下的模板写入目标路径（不覆盖已存在文件）。"""
    if target.exists():
        return
    template_path = TEMPLATE_DIR / template_name
    if template_path.exists():
        target.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        target.write_text("", encoding="utf-8")


def copy_template(name: str) -> str:
    """读取模板内容（供生成器使用）。"""
    template_path = TEMPLATE_DIR / name
    return template_path.read_text(encoding="utf-8")


def package_version() -> str:
    return papermate.__version__

"""PaperMate v0.2 的结构化文档模型。

原则：一页里的每个元素要么被解析，要么被显式标记；不做静默丢弃。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Line:
    """PDF 里的一条文本行（已合并同一基线上的碎片）。"""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    bold: bool = False
    rotated: bool = False

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2


@dataclass
class Block:
    """段落、标题、表格、图占位或脚注。"""

    kind: str  # paragraph | heading | table | figure | note
    text: str = ""
    lines: list[Line] = field(default_factory=list)
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    rows: list[list[str]] | None = None
    caption: str = ""
    marker: str = ""
    note: str = ""  # 给不支持的块留一句可核对的话


@dataclass
class PageDoc:
    page: int
    width: float
    height: float
    blocks: list[Block] = field(default_factory=list)
    footnotes: list[Block] = field(default_factory=list)
    flags: dict = field(default_factory=dict)


@dataclass
class Document:
    path: str
    title: str = ""
    pages: list[PageDoc] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)

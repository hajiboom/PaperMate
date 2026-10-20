# PaperMate

[English](README.md) | 简体中文

面向中文社科论文（知网等）的**共读工具**，分两层：

- **Skill**：阅读节奏、评价标准、笔记与汇报结构。负责判断。
- **CLI**：`papermate read` 把 PDF 还原成按页的 `text.md` / `pages.json`。负责"读得准"。

CLI 不调用模型，不做学术判断；所有判断由当前会话里的 Agent 完成。数据全部留在本地。

## 为什么是"CLI + Skill"，而不是纯 Skill 或插件

- **纯 Skill 在 dsh 上不成立**：dsh 内置 `read` 只接受 UTF-8 文本，打不开 PDF，必须依赖 PDF 插件。
- **插件不是通用层**：dsh 插件是 Cordis/Node，OpenCode 又是另一套；跨 harness 能用的只有 Markdown skill 和本地 CLI。
- **v0.1 的教训不是"不该有 CLI"**，而是"不该在 CLI 里做有损清洗"。当时 `cleaner.py` 把表 1 压成"4 行碎片，已折叠"，模型仍自信引用 Page 4。

v0.2 的契约反过来：**每个块要么被解析，要么被显式标记，永不静默丢弃。**

- 表格 → Markdown 表格（合并单元格做 fill-down）
- 图 → 图题 + 图内文字单列，并标"顺序不可靠，需回原 PDF 核对"
- 脚注 → 从页面下方第一条标记开始整体切出，含续行
- 每页保留 `<!-- Page N -->` 锚点

## 为什么没有 `engines/` 抽象

先跑了 14 篇、144 页的中文社科语料（`bench/FINDINGS.md`）：

| 指标 | 结果 |
|---|---|
| 含图片 | 0 / 14 |
| 扫描页 | 0 / 14 |
| 含表格 | 3 / 14 |
| 平均字符/页 | 1,553 |

单一 PyMuPDF 覆盖全部样本；真正的失败模式在**行级 block 的排序、分栏、段落重建和脚注切分**，不在抽取引擎。所以只保留一个函数级接缝：

```python
def read_pages(path, pages=None) -> Document: ...
```

将来真出现扫描件，再写 `read_pages_mineru()` 用同一返回类型替换，不建引擎注册表。

## 安装

```bash
git clone https://github.com/hajiboom/PaperMate.git
cd PaperMate
uv venv .venv && uv pip install -e . -p .venv   # 或 pip install -e .
./install.sh                                     # 安装 skill 到 ~/.dsh/skills 与 ~/.agents/skills
```

## 用法

```bash
# 1. 解析一篇论文
papermate read paper.pdf --out research-library/papers/2026-10-20__短标题

# 2. 到 Agent 里说
#    "帮我读一下这篇论文"
#    "这篇值不值得读 / 水不水 / 能不能引用"
#    "帮我准备组会 / 写讲稿"
```

`papermate read` 生成 `text.md`（人读）与 `pages.json`（程序读）。可选 `--pages 1-3,5` 只读部分页面。

## 工作区

```
research-library/
  papers/YYYY-MM-DD__短标题/
    source.pdf
    text.md        # CLI：按页文本，表格为 Markdown
    pages.json     # CLI：结构化块
    meta.md        # status / reading_recommendation / user_label
    notes.md       # 阅读笔记（追加）
    state.md       # 读到哪、已形成的问题
    brief.md       # 可选，文献卡片
    critique.md    # 可选
    slides.md      # 可选
  matrix/matrix.md
  weekly/YYYY-WXX.md
```

## 已知边界

- **扫描件**：没有 OCR，页面会被标记为"扫描页，需 OCR"，不会假装读过。
- **图**：只把图内文字分离出来，不做图像理解；数字需回原 PDF 核对。
- **复杂表格**：合并单元格只补首列；跨页表、无框线表仍可能出错，标出来而不是猜。
- **不联网**：不调用任何模型 API，不上传论文。

## 基准

- `bench/probe.py`：单篇版面探针
- `bench/run.py`：语料结构分数表
- `bench/regress.py`：v0.2 回归（段落/标题/表/图/脚注/行序/页眉残留）
- `bench/FINDINGS.md`：结论与决定

## 许可

MIT

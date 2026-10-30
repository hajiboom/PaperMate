# PaperMate v0.3：PPT 生成调研与方案

> 日期：2026-10-30  
> 状态：调研记录，不是已发布功能  
> 适用版本：PaperMate 0.2.0

本文整理当前会话中关于“让 PaperMate 直接生成组会 PPT”的调研结论、技术判断和候选实施方案。外部产品能力会变化，正式实现前应重新核对官方文档。

## 1. 结论先行

PaperMate 的首个 PPT 生成版本应采用“内容中间层 + 确定性本地渲染器”：

1. Agent 从 `brief.md`、`notes.md`、`matrix.md` 等材料中组织受控内容，并保留论文、页码和原文短句。
2. CLI 把受控 Markdown 校验并渲染为可编辑的 `.pptx`。
3. 首版完全离线，不调用模型 API，不上传论文或笔记。
4. 不依赖 LaTeX、Pandoc 或 LibreOffice；这些只作为后续可选导出路径。
5. 不引入 `engines/` 注册表，也不做 Web 编辑器和任意 PPTX 重排。

LaTeX/Beamer 适合公式密集和打印场景，但其主要产物是可打印 PDF，不是用户可继续编辑的 PPTX；不应成为 v0.3 主链路。

## 2. 产品路径调研

### Claude

- Claude Artifacts 提供 Slides 模板，可从聊天内容生成 deck，支持在线编辑、演示、导出 PowerPoint/PDF，以及转到 Google Slides。
- 该流程依赖 Artifacts、云端代码执行和文件创建，内容会进入托管工作流。
- Claude for Google Workspace 可在已打开的 Google Slides 中新建或修改幻灯片，但仍是 beta，且不能创建、复制或导出其他 Drive 文件。
- 判断：适合作为可选的人工快速出稿路径，不适合作为 PaperMate 默认链路，因为与“论文和笔记不出本地”的项目规则冲突。

### Codex / ChatGPT

- ChatGPT 桌面端和 Work 可创建、预览、标注并修订 presentations。
- Codex CLI 可在工作目录创建和编辑文件，但没有视觉预览和标注界面，因此需要明确输出路径并执行结构检查。
- Skills 适合封装可重复流程，并可配合确定性脚本。
- 判断：Codex 的合理角色是“内容规划 + 调用本地生成器 + 运行检查”，不能只依赖 Agent 自由编写 PPTX/LaTeX 来保证布局和证据链。

### LaTeX

优点：

- 公式、引用和高密度学术排版控制力强。
- Beamer 适合技术汇报和讲义 PDF。

限制：

- 主要产出是 PDF，难以继续在 PowerPoint/WPS 中编辑。
- 转回 PPTX 后，版式通常不可控。
- 内容与版式耦合，改一句话也可能导致溢出或重排。
- 需要额外安装 TeX Live、XeLaTeX、Pandoc 和中文字体。

当前环境背景（调研时）：

- 未发现 `pandoc`、`xelatex/lualatex/pdflatex` 或 LibreOffice。
- `fc-list` 未返回中文字体。

因此，首版主产物应是可以继续编辑的 PPTX；LaTeX/Typst 留给公式密集或打印版的后续可选导出。

## 3. 推荐架构

```text
brief.md / notes.md / matrix.md
        ↓ Agent：组织观点与证据
slides.md（受控 Markdown，含证据页码）
        ↓ CLI：校验、布局、渲染，不调用模型
deck.json / validation report
        ↓
deck.pptx（主产物；PDF 可选）
```

设计原则：

1. Agent 生成内容，不直接拼 OOXML 或 LaTeX。
2. CLI 负责版式、溢出检查、主题、页码、备注和确定性输出。
3. 证据引用是内容模型的一等字段，不只是页脚装饰。
4. 文本、形状、表格和图表使用 PowerPoint 原生对象，保持可编辑。
5. 首版离线，不调用 Claude、ChatGPT 或其他第三方 API。
6. 优先单一生成器，不为 PPT 引入引擎注册表或前端编辑器。

## 4. 候选实施路线

### P0：首个可用版本

定义 `slides.md` 的最小语法：

- front matter：标题、副题、作者、日期、主题、16:9。
- 每页：标题、一个核心判断、2–4 个 bullets。
- evidence：`来源 | Page N | 原文短句`。
- speaker notes：讲稿提示。
- layout：`title`、`section`、`claim`、`bullets`、`quote`、`comparison`、`timeline`。

建议新增 CLI：

```text
papermate deck check slides.md
papermate deck build slides.md --out deck.pptx
```

依赖建议使用 `python-pptx`。项目已经是 Python/PyMuPDF 技术栈，无需再引入 Node、Pandoc 或 TeX。

首版学术主题：

- 16:9，白底，深蓝/灰色，等宽页码。
- 标题 30–36pt，正文 20–24pt，页脚 10–12pt。
- 每页最多 4 条 bullet，每条约 40–60 个中文字符。
- 字体名可配置；Linux 端字体缺失时明确警告，不静默替换。

生成与校验：

- 生成原生 PowerPoint 表格、基础条形图、引用块和演讲者备注。
- 页脚统一显示论文短题、年份、页码和 `PaperMate`。
- 检查缺标题、空页、bullet 过多、标题过长、缺证据、页码格式错误。
- 检测“原文未提及”“页码待核”等未完成证据，并阻止带病输出。
- 估算文本溢出；超限时失败，并定位到页和字段。
- 用 `python-pptx` 重新打开产物，检查 slide 数、备注、媒体和关系文件。

### P1：接入真实组会工作流

- `papermate deck new --paper <paper-dir>`：从单篇 `brief.md` 建立骨架。
- `papermate deck new --matrix <matrix.md>`：从横向比较建立 10–15 页多篇 deck。
- 用 `pages.json` 的 figure/table bbox 和源 PDF 裁剪图表。
- 图表自动附带 caption、来源页和可选原文引用。
- 找不到 bbox 时只显示占位，不猜测图片内容。
- 提供两种 deck profile：
  - 组会单篇：背景、问题、框架、方法、证据、发现、批评、启发、讨论。
  - 文献综合：共同问题、共识、分歧、证据强度、研究缺口、自己的切口。
- 将讲稿写入 PPTX 演讲者备注，并同时保留独立讲稿文件。
- 只有检测到 LibreOffice 时才启用可选 PDF 导出。
- 建立金样测试：至少覆盖一篇单篇 deck 和一份多篇综合 deck。

### P2：后续增强

- 可选 Beamer/Typst 导出，用于公式密集或打印版 PDF。
- 可选 `deck.handoff.md`，把已核验内容交给 Claude Slides 或 ChatGPT 文件工作流；这不能成为默认数据路径。
- 更多学术主题、校徽和页眉模板。
- 表格跨页、复杂合并单元格和参考文献样式适配。

## 5. 明确暂不做

- 不调用模型 API，不自动上传论文。
- 不做 Web UI、幻灯片编辑器或数据库。
- 不让模型直接生成原始 PPTX XML。
- 不把 LaTeX 设为必需依赖。
- 不把“看起来像图”的区域自动截图冒充图表。
- 首版不支持导入任意现有 PPTX 并自动重排。

## 6. 首个 POC 的验收标准

建议使用 `research-library/matrix/matrix.md` 的 4 篇横向比较生成约 12 页 deck。

1. `deck.pptx` 可在 PowerPoint/WPS 中打开，也可被 `python-pptx` 重新读取。
2. 标题、正文、表格、页脚和备注都是可编辑对象。
3. 涉及论文主张的页面都有“作者/标题、页码、原文短句”；缺证据时 `deck check` 失败。
4. 16:9 下无越界；同时按字数和文本框尺寸检查溢出。
5. 不联网，不依赖 LaTeX 或 LibreOffice。
6. Markdown 到 PPTX 的 CLI 在数秒内完成，错误信息能定位到页和字段。

## 7. 尚待产品决策

1. 第一个 POC 做“单篇约 12 页”，还是“四篇综合约 12–15 页”？当前建议后者，可同时检验论证链和比较表。
2. 组会模板优先极简学术白底，还是学校/课题组固定视觉规范？
3. 讲稿是否默认同时写入 PPTX 备注和独立 Markdown 文件？当前建议两者都生成。
4. PDF 是否进入首发验收？当前建议不进入，先保证可编辑 PPTX。
5. 图表首版是否从 PDF 裁真实图？当前建议只处理有明确 bbox 的图表，其余留占位。

## 8. 调研来源

Claude：

- https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them.md
- https://support.claude.com/en/articles/16951679-use-claude-in-google-docs-sheets-and-slides.md

Codex / ChatGPT：

- https://learn.chatgpt.com/docs/artifacts-viewer.md
- https://learn.chatgpt.com/docs/skills-and-plugins.md
- https://learn.chatgpt.com/docs/build-skills.md

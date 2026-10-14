# PaperMate

面向**中文社科论文阅读**的本地共读工作流：

> PaperMate = 通用 AI Agent 共读 Skill（大脑）+ papermate CLI（手脚）

- **Skill**：在任何支持 agent skill 的编码助手中（OpenCode / Codex / Claude Code 等）陪用户共读论文——解释概念、审视方法、批判结论、生成阅读卡片、质量报告、组会大纲、文献矩阵、周报，并把判断沉淀为本地 Markdown。
- **CLI**：`papermate` 只做文件处理和本地整理——解析知网 PDF（PyMuPDF）、清洗文本、生成论文文件夹、维护 INDEX.md、聚合文献矩阵、本地关键词搜索。
- **CLI 不调用任何模型，不做任何学术判断。** 所有思考由当前 Agent 会话里的模型完成。
- **所有数据保存在本地**，不上传 PDF、不上传笔记、不联网。

## 安装

```bash
# Python 3.10+
git clone <repo-url>
cd PaperMate
pip install -e .

# 或使用 uv
uv pip install -e .
```

安装后获得 `papermate` 命令（等价于 `python -m papermate`）。

## 快速上手

```bash
# 1. 初始化工作区（当前目录下生成 research-library/）
papermate init

# 2. 解析一篇知网 PDF
papermate parse ./papers/example.pdf
# 可选：--dir ./research-library  --force  --title "标题"  --tags "基层治理,数字化"

# 3. 之后到你的 Agent（OpenCode 等）里说：
#    "帮我读一下 research-library/papers/xxx/text.md"
#    "这篇值不值得读？" "帮我准备组会" "帮我做文献矩阵"
```

## CLI 命令

| 命令 | 用途 |
|---|---|
| `papermate init` | 初始化 `research-library/` 工作区（已存在则不改动） |
| `papermate parse <pdf>` | 解析 PDF：创建 `papers/YYYY-MM-DD__短标题/`，生成 `source.pdf` `text.md` `meta.md` `notes.md` `state.md`，更新 `INDEX.md` |
| `papermate list [--json]` | 列出本地论文 |
| `papermate show <paper_slug> [--json]` | 查看某篇论文的 meta 与文件清单 |
| `papermate matrix` | 聚合各篇 `meta.md` `brief.md` `critique.md`，生成 `matrix/matrix.md` |
| `papermate search <关键词>` | 在 7 类论文 Markdown 中做字符串搜索，输出命中片段 |

所有命令支持 `--dir` 指定工作区，默认 `./research-library`。

## 工作区结构

```
research-library/
  INDEX.md                  # 文献索引
  papers/
    2026-10-12__基层治理数字化/
      source.pdf            # 原始 PDF
      text.md               # 解析后的正文（含页码标记，供引用原文位置）
      meta.md               # YAML 元数据（status / reading_recommendation / user_label）
      brief.md              # 文献阅读卡片（Skill 生成）
      critique.md           # 质量审视报告（Skill 生成）
      slides.md             # 组会汇报大纲（Skill 生成）
      notes.md              # 阅读笔记
      state.md              # 阅读状态
  matrix/matrix.md          # 文献矩阵（CLI 聚合 + Skill 解读）
  weekly/2026-W41.md        # 周报（Skill 生成）
```

规则：CLI 只写入 `parse` 时生成的 5 个文件；`brief.md` `critique.md` `slides.md` `weekly/` 由共读 Skill 按用户要求生成。

## Agent Skill（共读工作流）

Skill 正文见 **[SKILL.md](SKILL.md)**，接入说明见 **[AGENTS.md](AGENTS.md)**。

- 直接把 SKILL.md 的内容作为系统提示 / skill 文件加载，即可让任意 Agent 按同一套共读流程工作；
- OpenCode：复制为 `.opencode/skill/papermate/SKILL.md`；
- Codex：内容并入或链接到项目的 `AGENTS.md`；
- Claude Code：复制为 `~/.claude/skills/papermate/SKILL.md`。

## 开发

```bash
uv venv .venv && uv pip install -e . -p .venv   # 依赖：click、PyMuPDF
pytest                                          # （测试待补）
python testdata/make_sample_pdf.py                   # 重新生成 testdata/sample.pdf
```

## 设计边界（第一版明确不做）

不做独立聊天界面、账号系统、云同步、数据库、HTTP API、向量检索、PDF 阅读器；
CLI 不调用 LLM、不生成学术总结、不判断论文质量、不要求配置模型 API。

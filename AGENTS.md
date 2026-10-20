# AGENTS.md —— PaperMate 接入说明

本项目有两个产物：

- `skills/papermate/`：与工具无关的共读 skill（判断、流程、模板）
- `papermate/`：按页读取 PDF 的 CLI（`papermate read`），不调用模型

v0.1 的旧 CLI 已封存在 `v0.1-final` tag；v0.2 只保留按页读取，不做 `engines/` 抽象。

## 接入方式

| 工具 | 做法 |
|---|---|
| dsh | `./install.sh` → `~/.dsh/skills/papermate/`，用 `/papermate` 触发 |
| OpenCode | `./install.sh --project` → `.opencode/skill/papermate/` |
| Codex | `./install.sh` → `~/.agents/skills/papermate/`，或把 SKILL.md 并入 AGENTS.md |
| Claude Code | `cp -R skills/papermate ~/.claude/skills/papermate` |
| 其他 / API | 把 `skills/papermate/SKILL.md` 放进系统提示或项目指令文件 |

skill 靠目录扫描发现，`dsh plugin add` 不安装 skill。

## 读取流程

1. `papermate --version` 确认 CLI 可用。
2. `papermate read <pdf> --out research-library/papers/YYYY-MM-DD__短标题`。
3. 读生成的 `text.md`：带 `<!-- Page N -->`，表格是 Markdown，图内文字单列。
4. 标了「扫描页 / 需回原 PDF 核对 / 顺序不可靠」的地方，回原文件确认，不要从残片推断。

CLI 不可用时，才退回会话里的按页 PDF 工具或用户粘贴的文本。

## Agent 使用本项目时的硬性规则

1. **CLI 优先**：用 `papermate read` 生成的 `text.md`，不要临时手写脚本把 PDF 转文本。有损转换会静默丢掉表格、图注和脚注。
2. 判断基于原文，给「章节标题 + 原文短句」；页码以 `<!-- Page N -->` 为准，不确定就标「页码待核」；信息不足写「原文未提及」。
3. 表格和图是证据：表格按行列读，图内文字只作线索；读不清就说「需回原 PDF 核对」。
4. 保存判断时**追加**到 `notes.md` / `state.md`，不覆盖用户内容；`meta.md` 的受控字段保持 YAML 合法。
5. 数据不出本地：不上传论文或笔记到任何第三方服务。

## 维护

- 读取逻辑在 `papermate/`：`read.py`（编排）、`layout.py`（行/栏/段/脚注）、`tables.py`、`figures.py`、`render.py`。
- 只保留一个函数级接缝 `read_pages()`；不要引入引擎注册表，除非基准测试证明单一 PyMuPDF 不够。
- 改版面逻辑后跑 `bench/regress.py`，要求：行序倒置 0、页眉残留 0、短段不显著增加。
- 改 skill 只改 `skills/papermate/`（正文 + `templates/`）。

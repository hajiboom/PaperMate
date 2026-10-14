# AGENTS.md —— PaperMate 共读 Skill 通用接入说明

本项目的核心产出之一是一套**与工具无关**的社科论文共读 Skill（见 `SKILL.md`）。
任何能按 Markdown 指令工作的编码 Agent（OpenCode、Codex、Claude Code 等）都可以使用。

## 接入方式

| 工具 | 做法 |
|---|---|
| OpenCode | `mkdir -p .opencode/skill/papermate && cp SKILL.md .opencode/skill/papermate/SKILL.md` |
| Codex | 把 SKILL.md 全文并入项目的 `AGENTS.md`（或用 `@SKILL.md` 引用） |
| Claude Code | `mkdir -p ~/.claude/skills/papermate && cp SKILL.md ~/.claude/skills/papermate/SKILL.md` |
| 其他工具 / API | 把 SKILL.md 内容放入系统提示或项目级指令文件 |

## Skill 与 CLI 的分工

- **CLI（`papermate`）**：解析 PDF、清洗文本、建论文文件夹、维护 INDEX.md、聚合矩阵、本地搜索。
  它**不含任何模型调用与学术判断**。
- **Agent（加载 SKILL.md 后）**：共读、解释、批判、评估政策建议、生成 brief/critique/slides/weekly，
  并把结论写回对应论文文件夹的 Markdown 文件（追加，不覆盖）。

## Agent 使用本项目时的硬性规则

1. 检测到论文类请求时，先检查 `papermate` 命令是否可用；可用则优先 `papermate parse <pdf>`，
   再读取生成的 `text.md`。不可用时提示安装，或直接讨论用户粘贴的文本。
2. 所有输出基于本地解析后的文本或用户提供的原文；信息不足时明确说"原文未提及"，
   **不编造引用、数据、参考文献或作者观点**。
3. 保存判断时追加到 `notes.md` / `state.md`，不覆盖用户内容；
   阅读建议与用户判断的受控取值写回 `meta.md` 时保持 YAML 格式合法。
4. 需要文献矩阵时先运行 `papermate matrix`，再基于 matrix.md 做归纳解读。
5. 数据不出本地：不要把论文内容或笔记上传到任何第三方服务。

详细工作流、模板与输出风格见 `SKILL.md`。

#!/usr/bin/env bash
# 安装 PaperMate skill 到本地 agent 的 skill 目录。
# 用法：
#   ./install.sh                 安装到用户级（~/.dsh/skills 与 ~/.agents/skills）
#   ./install.sh --project       安装到当前项目（.dsh/skills 与 .opencode/skill）
#   ./install.sh --target DIR    安装到指定目录
#   ./install.sh --force         覆盖已存在的同名 skill
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$ROOT/skills/papermate"
FORCE=0
TARGETS=()

usage() {
  sed -n '2,7p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      TARGETS+=("$PWD/.dsh/skills/papermate" "$PWD/.opencode/skill/papermate")
      shift
      ;;
    --target)
      [[ $# -ge 2 ]] || { echo "缺少 --target 的参数" >&2; exit 1; }
      TARGETS+=("$2")
      shift 2
      ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage 0 ;;
    *) echo "未知参数：$1" >&2; usage 1 ;;
  esac
done

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  TARGETS=("$HOME/.dsh/skills/papermate" "$HOME/.agents/skills/papermate")
fi

[[ -f "$SRC/SKILL.md" ]] || { echo "找不到 $SRC/SKILL.md" >&2; exit 1; }

for dst in "${TARGETS[@]}"; do
  if [[ -e "$dst" && $FORCE -ne 1 ]]; then
    echo "已存在，跳过：$dst（用 --force 覆盖）"
    continue
  fi
  rm -rf "$dst"
  mkdir -p "$(dirname "$dst")"
  cp -R "$SRC" "$dst"
  echo "已安装：$dst"
done

cat <<'EOF'

下一步：
  dsh      → 运行 `npx @deepseek-ai/dsh web`，在输入框用 `/papermate` 触发
  OpenCode → 重启后直接说“帮我读一下这篇论文”
  其他工具 → 把 SKILL.md 作为 skill / 系统提示加载

注意：skill 是目录扫描发现的，`dsh plugin add` 不安装 skill。
EOF

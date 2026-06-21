#!/bin/bash
# ══════════════════════════════════════════════════════
#  Claude Code Skill OS v4 — 卸载脚本
#  用法：bash skill-os-uninstall.sh
# ══════════════════════════════════════════════════════

set -e

TARGET="$(pwd)"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   Claude Code Skill OS v4 — 卸载              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── 1. 确认 ──────────────────────────────────────────
echo "  将要移除以下内容："
echo "    • .claude/skill-rules.json"
echo "    • .claude/hooks/skill-router.py"
echo "    • .claude/hooks/task-guard.py"
echo "    • .claude/hooks/completion-guard.py"
echo "    • .claude/skills/"
echo "    • .claude/router/"
echo "    • .claude/protocols/"
echo "    • .claude/system/"
echo "    • .claude/workflows/"
echo "    • .claude/orchestration/"
echo "    • .claude/agents/"
echo ""
echo "  ⚠ settings.json 中的 hook 条目需要手动移除"
echo ""

read -p "  确认卸载？(y/N) " -r CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
  echo "  已取消。"
  exit 0
fi

# ── 2. 备份 ──────────────────────────────────────────
BACKUP_DIR="$TARGET/.claude/backups"
mkdir -p "$BACKUP_DIR"
BACKUP_NAME="uninstall-$(date +%Y%m%d-%H%M%S)"

if [ -f "$TARGET/.claude/settings.json" ]; then
  cp "$TARGET/.claude/settings.json" "$BACKUP_DIR/$BACKUP_NAME-settings.json"
  echo "  ✓ 已备份 settings.json"
fi
if [ -f "$TARGET/.claude/skill-rules.json" ]; then
  cp "$TARGET/.claude/skill-rules.json" "$BACKUP_DIR/$BACKUP_NAME-skill-rules.json"
  echo "  ✓ 已备份 skill-rules.json"
fi

# ── 3. 移除 Skill OS 文件 ────────────────────────────
echo ""
echo "  → 移除 Skill OS 文件..."

rm -f "$TARGET/.claude/skill-rules.json"
rm -f "$TARGET/.claude/hooks/skill-router.py"
rm -f "$TARGET/.claude/hooks/task-guard.py"
rm -f "$TARGET/.claude/hooks/completion-guard.py"
rm -rf "$TARGET/.claude/skills"
rm -rf "$TARGET/.claude/router"
rm -rf "$TARGET/.claude/protocols"
rm -rf "$TARGET/.claude/system"
rm -rf "$TARGET/.claude/workflows"
rm -rf "$TARGET/.claude/orchestration"
rm -rf "$TARGET/.claude/agents"

echo "  ✓ 已移除"

# ── 4. 清理 practice/ 和 knowledge/ 的 .gitkeep ─────
# 不删除用户的学习产物，只提示
echo ""
echo "  ⚠ 以下目录未删除（可能包含你的学习产物）："
[ -d "$TARGET/practice" ] && echo "    • practice/"
[ -d "$TARGET/.claude/system/knowledge" ] && echo "    • .claude/system/knowledge/（如存在）"

# ── 5. 提示手动步骤 ──────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  卸载完成！                                  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  ⚠ 请手动编辑 .claude/settings.json，移除以下 hook 条目："
echo ""
echo "    在 \"hooks\" > \"UserPromptSubmit\" 中，删除："
echo "    {"
echo "      \"command\": \"python3 \$CLAUDE_PROJECT_DIR/.claude/hooks/skill-router.py\","
echo "      \"type\": \"command\""
echo "    }"
echo ""
echo "  备份位于：.claude/backups/$BACKUP_NAME-*"
echo ""

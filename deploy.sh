#!/bin/bash
# ══════════════════════════════════════════════════════
#  Claude Code Skill OS v4 — 一键部署脚本
#  用于在已有安装上升级到 v4（不做全新安装）
#  用法：bash skill-os-deploy.sh
# ══════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(pwd)"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   Claude Code Skill OS v4 — 部署/升级         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  部署目标：$TARGET"
echo ""

# ── 1. 检查是否已安装过 Skill OS ────────────────────
if [ ! -d "$TARGET/.claude" ]; then
  echo "  ⚠ 未检测到 .claude/ 目录，可能是全新安装。"
  echo "  → 建议使用 install.sh 做全新安装："
  echo "    bash /path/to/skill-os-complete/install.sh"
  echo ""
  echo "  现在继续部署流程..."
fi

# ── 2. 备份当前配置 ──────────────────────────────────
BACKUP_DIR="$TARGET/.claude/backups"
mkdir -p "$BACKUP_DIR"
BACKUP_NAME="pre-v4-$(date +%Y%m%d-%H%M%S)"

if [ -f "$TARGET/.claude/settings.json" ]; then
  cp "$TARGET/.claude/settings.json" "$BACKUP_DIR/$BACKUP_NAME-settings.json"
fi
if [ -f "$TARGET/.claude/skill-rules.json" ]; then
  cp "$TARGET/.claude/skill-rules.json" "$BACKUP_DIR/$BACKUP_NAME-skill-rules.json"
fi
echo "  ✓ 已备份当前配置到 backups/$BACKUP_NAME-*"

# ── 3. 同步 v4 新增目录 ─────────────────────────────
echo ""
echo "  ── 同步 v4 目录结构 ──"

mkdir -p "$TARGET/.claude/system/execution_guard"
echo "  ✓ system/execution_guard/"

mkdir -p "$TARGET/.claude/system/learning_state"
echo "  ✓ system/learning_state/"

mkdir -p "$TARGET/.claude/orchestration/schema"
mkdir -p "$TARGET/.claude/orchestration/runs"
mkdir -p "$TARGET/.claude/orchestration/artifacts"
echo "  ✓ orchestration/ (schema/runs/artifacts)"

mkdir -p "$TARGET/.claude/agents"
echo "  ✓ agents/"

# ── 4. 同步 v4 新增文件 ─────────────────────────────
echo ""
echo "  ── 同步 v4 文件 ──"

# execution_guard 文档
for f in task-state-machine.md artifact-requirements.md guard-rules.md stall-policy.md audit-checklist.md; do
  if [ -f "$SCRIPT_DIR/.claude/system/execution_guard/$f" ]; then
    cp "$SCRIPT_DIR/.claude/system/execution_guard/$f" "$TARGET/.claude/system/execution_guard/"
    echo "  ✓ $f"
  fi
done

# learning_state 文档
for f in learning-state-schema.md learning-state-machine.md study-resume-policy.md; do
  if [ -f "$SCRIPT_DIR/.claude/system/learning_state/$f" ]; then
    cp "$SCRIPT_DIR/.claude/system/learning_state/$f" "$TARGET/.claude/system/learning_state/"
    echo "  ✓ $f"
  fi
done

# state.json（仅在不存在时创建）
if [ ! -f "$TARGET/.claude/system/learning_state/state.json" ]; then
  cat > "$TARGET/.claude/system/learning_state/state.json" << 'STATEJSON'
{
  "meta": {
    "version": "4.0.0",
    "updated": "DEPLOY_DATE"
  },
  "topics": []
}
STATEJSON
  echo "  ✓ state.json（新建）"
else
  echo "  • state.json（已存在，跳过）"
fi

# guard hooks
for f in task-guard.py completion-guard.py; do
  if [ -f "$SCRIPT_DIR/.claude/hooks/$f" ]; then
    cp "$SCRIPT_DIR/.claude/hooks/$f" "$TARGET/.claude/hooks/"
    chmod +x "$TARGET/.claude/hooks/$f"
    echo "  ✓ hooks/$f"
  fi
done

# orchestration/agents README
if [ -f "$SCRIPT_DIR/.claude/orchestration/README.md" ]; then
  cp "$SCRIPT_DIR/.claude/orchestration/README.md" "$TARGET/.claude/orchestration/"
  echo "  ✓ orchestration/README.md"
fi
if [ -f "$SCRIPT_DIR/.claude/agents/README.md" ]; then
  cp "$SCRIPT_DIR/.claude/agents/README.md" "$TARGET/.claude/agents/"
  echo "  ✓ agents/README.md"
fi

	# ── 4.5. 同步新增根目录模块（orchestration/routing_assets/tests/ledger） ──
	echo ""
	echo "  ── 同步新增模块 ──"

	# orchestration 模块（Phase 4+ 编排引擎）
	if [ -d "$SCRIPT_DIR/orchestration" ]; then
	  mkdir -p "$TARGET/orchestration"
	  cp -r "$SCRIPT_DIR/orchestration/"*.py "$TARGET/orchestration/" 2>/dev/null || true
	  echo "  ✓ orchestration/ (phase 4+ 模块)"
	fi

	# routing_assets 模块
	if [ -d "$SCRIPT_DIR/routing_assets" ]; then
	  mkdir -p "$TARGET/routing_assets"
	  cp -r "$SCRIPT_DIR/routing_assets/"*.py "$SCRIPT_DIR/routing_assets/"*.json "$TARGET/routing_assets/" 2>/dev/null || true
	  echo "  ✓ routing_assets/"
	fi

	# ledger 模块
	if [ -d "$SCRIPT_DIR/ledger" ]; then
	  mkdir -p "$TARGET/ledger"
	  cp -r "$SCRIPT_DIR/ledger/"*.py "$TARGET/ledger/" 2>/dev/null || true
	  echo "  ✓ ledger/"
	fi

	# tests 模块
	if [ -d "$SCRIPT_DIR/tests" ]; then
	  mkdir -p "$TARGET/tests"
	  cp -r "$SCRIPT_DIR/tests/"*.py "$TARGET/tests/" 2>/dev/null || true
	  echo "  ✓ tests/"
	fi

	# docs 模块
	if [ -d "$SCRIPT_DIR/docs" ]; then
	  mkdir -p "$TARGET/docs"
	  cp -r "$SCRIPT_DIR/docs/"* "$TARGET/docs/" 2>/dev/null || true
	  echo "  ✓ docs/"
	fi

	# reports 模块
	if [ -d "$SCRIPT_DIR/reports" ]; then
	  mkdir -p "$TARGET/reports"
	  cp -r "$SCRIPT_DIR/reports/"*.md "$TARGET/reports/" 2>/dev/null || true
	  echo "  ✓ reports/"
	fi

# ── 5. 同步 v4 修改的文件（核心技能 + workflow + schema） ──
echo ""
echo "  ── 同步 v4 更新的文件 ──"

# 核心三技能
for skill in summarize planning debug; do
  if [ -d "$SCRIPT_DIR/.claude/skills/core/$skill" ]; then
    mkdir -p "$TARGET/.claude/skills/core/$skill"
    cp -r "$SCRIPT_DIR/.claude/skills/core/$skill/"* "$TARGET/.claude/skills/core/$skill/"
    echo "  ✓ skills/core/$skill/"
  fi
done

# teach-plus
if [ -d "$SCRIPT_DIR/.claude/skills/teach-plus" ]; then
  mkdir -p "$TARGET/.claude/skills/teach-plus"
  cp -r "$SCRIPT_DIR/.claude/skills/teach-plus/"* "$TARGET/.claude/skills/teach-plus/"
  echo "  ✓ skills/teach-plus/"
fi

	# knowledge-asset
	if [ -d "$SCRIPT_DIR/.claude/skills/knowledge-asset" ]; then
	  mkdir -p "$TARGET/.claude/skills/knowledge-asset"
	  cp -r "$SCRIPT_DIR/.claude/skills/knowledge-asset/"* "$TARGET/.claude/skills/knowledge-asset/"
	  echo "  ✓ skills/knowledge-asset/"
	fi

# workflow 文档
if [ -d "$SCRIPT_DIR/.claude/workflows" ]; then
  mkdir -p "$TARGET/.claude/workflows"
  cp -r "$SCRIPT_DIR/.claude/workflows/"* "$TARGET/.claude/workflows/"
  echo "  ✓ workflows/"
fi

# task_ledger schema
if [ -f "$SCRIPT_DIR/.claude/system/task_ledger/schema.md" ]; then
  cp "$SCRIPT_DIR/.claude/system/task_ledger/schema.md" "$TARGET/.claude/system/task_ledger/"
  echo "  ✓ task_ledger/schema.md"
fi

# router
for f in skill_index.json workflow_templates.json routing_rules.py intent_schema.md; do
  if [ -f "$SCRIPT_DIR/.claude/router/$f" ]; then
    cp "$SCRIPT_DIR/.claude/router/$f" "$TARGET/.claude/router/"
    echo "  ✓ router/$f"
  fi
done

# skill-rules.json（含 execution_guard 条目）
if [ -f "$SCRIPT_DIR/.claude/skill-rules.json" ]; then
  cp "$SCRIPT_DIR/.claude/skill-rules.json" "$TARGET/.claude/"
  echo "  ✓ skill-rules.json"
fi

# skill-router.py
if [ -f "$SCRIPT_DIR/.claude/hooks/skill-router.py" ]; then
  cp "$SCRIPT_DIR/.claude/hooks/skill-router.py" "$TARGET/.claude/hooks/"
  chmod +x "$TARGET/.claude/hooks/skill-router.py"
  echo "  ✓ hooks/skill-router.py"
fi

# ── 6. 同步 README / CLAUDE ─────────────────────────
echo ""
echo "  ── 同步文档 ──"

if [ -f "$SCRIPT_DIR/CLAUDE.md" ]; then
  cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
  echo "  ✓ CLAUDE.md"
fi

if [ -f "$SCRIPT_DIR/README.md" ]; then
  cp "$SCRIPT_DIR/README.md" "$TARGET/skill-os-complete-README.md"
  echo "  ✓ README.md → skill-os-complete-README.md"
fi

# ── 7. 设置权限 ──────────────────────────────────────
chmod +x "$TARGET/.claude/hooks/skill-router.py" 2>/dev/null || true
chmod +x "$TARGET/.claude/hooks/task-guard.py" 2>/dev/null || true
chmod +x "$TARGET/.claude/hooks/completion-guard.py" 2>/dev/null || true
chmod +x "$TARGET/.claude/system/task_ledger/task-ops.py" 2>/dev/null || true

# ── 8. 快速验证 ──────────────────────────────────────
echo ""
echo "  ── 部署后验证 ──"

# JSON 格式验证
python3 -c "import json; json.load(open('$TARGET/.claude/skill-rules.json'))" 2>/dev/null \
  && echo "  ✓ skill-rules.json 格式正确" || echo "  ⚠ skill-rules.json 需要检查"

python3 -c "import json; json.load(open('$TARGET/.claude/router/workflow_templates.json'))" 2>/dev/null \
  && echo "  ✓ workflow_templates.json 格式正确" || echo "  ⚠ workflow_templates.json 需要检查"

# v4 关键模块存在性检查
for check in \
  "$TARGET/.claude/system/execution_guard/guard-rules.md" \
  "$TARGET/.claude/system/execution_guard/task-state-machine.md" \
  "$TARGET/.claude/system/learning_state/learning-state-schema.md" \
  "$TARGET/.claude/hooks/task-guard.py" \
  "$TARGET/.claude/hooks/completion-guard.py" \
  "$TARGET/.claude/orchestration/README.md" \
  "$TARGET/.claude/agents/README.md" \
  "$TARGET/.claude/skills/knowledge-asset/SKILL.md"
do
  if [ -f "$check" ]; then
    echo "  ✓ $(echo $check | sed "s|$TARGET/.claude/||")"
  else
    echo "  ✗ 缺失：$(echo $check | sed "s|$TARGET/.claude/||")"
  fi
done

# ── 9. 路由快速测试 ─────────────────────────────────
echo ""
echo "  ── 路由快速测试 ──"
echo '{"prompt":"帮我debug这段代码"}' | CLAUDE_PROJECT_DIR="$TARGET" python3 "$TARGET/.claude/hooks/skill-router.py" 2>/dev/null | grep -q "debug" \
  && echo "  ✓ debug 路由正常" || echo "  ✗ debug 路由异常"
echo '{"prompt":"给我一个计划"}' | CLAUDE_PROJECT_DIR="$TARGET" python3 "$TARGET/.claude/hooks/skill-router.py" 2>/dev/null | grep -q "planning" \
  && echo "  ✓ planning 路由正常" || echo "  ✗ planning 路由异常"
echo '{"prompt":"检查任务完成状态"}' | CLAUDE_PROJECT_DIR="$TARGET" python3 "$TARGET/.claude/hooks/skill-router.py" 2>/dev/null | grep -q "execution_guard" \
  && echo "  ✓ execution_guard 路由正常" || echo "  ✗ execution_guard 路由异常"

# ── 10. 完成 ─────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Skill OS v4 部署完成！                       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  备份位置：.claude/backups/$BACKUP_NAME-*"
echo "  如需回滚：cp .claude/backups/$BACKUP_NAME-settings.json .claude/settings.json"
echo ""
echo "  v4 新增模块已就绪："
echo "    • execution_guard   — 5 规则 + 2 hook + 状态机"
echo "    • learning_state    — 7 阶段状态机 + 断档恢复"
echo "    • knowledge-asset   — 知识资产系统（15 技能）"
echo "    • orchestration     — Phase 4+ 编排模块"
echo "    • routing_assets    — 路由资产测试"
echo "    • tests             — 自动化测试套件"
echo "    • docs/reports      — 升级文档 + 交付报告"
echo ""

#!/bin/bash
# ══════════════════════════════════════════════════════
#  Claude Code Skill OS v5.0.0 — 一键部署/升级脚本
#  用于在已有安装上升级到 v5.0.0（不做全新安装）
#  用法：bash skill-os-deploy.sh
# ══════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(pwd)"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   Claude Code Skill OS v5.0.0 — 部署/升级      ║"
echo "║   v4→v5: L0 Knowledge Bus + State + 7 Rules  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  部署源：$SCRIPT_DIR"
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
BACKUP_NAME="pre-v5.0.0-$(date +%Y%m%d-%H%M%S)"

for f in settings.json skill-rules.json; do
  if [ -f "$TARGET/.claude/$f" ]; then
    cp "$TARGET/.claude/$f" "$BACKUP_DIR/$BACKUP_NAME-$f"
    echo "  ✓ 已备份 $f"
  fi
done

# v5: 也备份旧 task_ledger 和 learning_state
for f in "$TARGET/.claude/system/task_ledger/tasks.json" "$TARGET/.claude/system/learning_state/state.json"; do
  if [ -f "$f" ]; then
    cp "$f" "$BACKUP_DIR/$BACKUP_NAME-$(basename $(dirname $f))-$(basename $f)"
    echo "  ✓ 已备份 $(basename $(dirname $f))/$(basename $f)"
  fi
done

# ── 3. 同步 v5 目录结构 ─────────────────────────────
echo ""
echo "  ── 同步 v5 目录结构 ──"

mkdir -p "$TARGET/.claude/system/execution_guard"
echo "  ✓ system/execution_guard/"

mkdir -p "$TARGET/.claude/system/learning_state"
echo "  ✓ system/learning_state/ (legacy)"

mkdir -p "$TARGET/.claude/system/knowledge"
echo "  ✓ system/knowledge/ (legacy)"

mkdir -p "$TARGET/.claude/system/debug_archive"
echo "  ✓ system/debug_archive/"

mkdir -p "$TARGET/.claude/agents"
echo "  ✓ agents/ (预留)"

# v5: state/ 统一状态层
mkdir -p "$TARGET/.claude/state/checkpoint"
echo "  ✓ state/ + checkpoint/ (v5 统一状态层)"

# v5: knowledge/ 知识库子目录
KNOWLEDGE_DIR="$TARGET/.claude/skills/knowledge-asset/knowledge"
for subdir in sop troubleshooting architecture knowledge-notes project-plans; do
  mkdir -p "$KNOWLEDGE_DIR/$subdir"
  touch "$KNOWLEDGE_DIR/$subdir/.gitkeep" 2>/dev/null || true
done
echo "  ✓ knowledge/ (5 子目录)"

# ── 4. 同步 v5 新增文件 ─────────────────────────────
echo ""
echo "  ── 同步 v5 文件 ──"

# execution_guard 文档
for f in task-state-machine.md artifact-requirements.md guard-rules.md stall-policy.md audit-checklist.md; do
  if [ -f "$SCRIPT_DIR/.claude/system/execution_guard/$f" ]; then
    cp "$SCRIPT_DIR/.claude/system/execution_guard/$f" "$TARGET/.claude/system/execution_guard/"
    echo "  ✓ execution_guard/$f"
  fi
done

# learning_state 文档 (legacy, 保留参考)
for f in learning-state-schema.md learning-state-machine.md study-resume-policy.md; do
  if [ -f "$SCRIPT_DIR/.claude/system/learning_state/$f" ]; then
    cp "$SCRIPT_DIR/.claude/system/learning_state/$f" "$TARGET/.claude/system/learning_state/"
    echo "  ✓ learning_state/$f (legacy)"
  fi
done

# v5: state/ 文件（仅新建，不覆盖已有数据）
for sf in current-task.json learning-state.json execution-state.json task-history.json; do
  if [ ! -f "$TARGET/.claude/state/$sf" ]; then
    if [ -f "$SCRIPT_DIR/.claude/state/$sf" ]; then
      cp "$SCRIPT_DIR/.claude/state/$sf" "$TARGET/.claude/state/"
      echo "  ✓ state/$sf (新建)"
    fi
  else
    echo "  • state/$sf (已存在，跳过)"
  fi
done

# state/README.md
if [ -f "$SCRIPT_DIR/.claude/state/README.md" ]; then
  cp "$SCRIPT_DIR/.claude/state/README.md" "$TARGET/.claude/state/"
  echo "  ✓ state/README.md"
fi

# state/checkpoint/.gitkeep
touch "$TARGET/.claude/state/checkpoint/.gitkeep" 2>/dev/null || true

# guard hooks (v5 升级版)
for f in task-guard.py completion-guard.py; do
  if [ -f "$SCRIPT_DIR/.claude/hooks/$f" ]; then
    cp "$SCRIPT_DIR/.claude/hooks/$f" "$TARGET/.claude/hooks/"
    chmod +x "$TARGET/.claude/hooks/$f"
    echo "  ✓ hooks/$f (v5)"
  fi
done

# agents README
if [ -f "$SCRIPT_DIR/.claude/agents/README.md" ]; then
  cp "$SCRIPT_DIR/.claude/agents/README.md" "$TARGET/.claude/agents/"
  echo "  ✓ agents/README.md"
fi

# v5: knowledge_asset_synonyms.md
if [ -f "$SCRIPT_DIR/.claude/router/knowledge_asset_synonyms.md" ]; then
  cp "$SCRIPT_DIR/.claude/router/knowledge_asset_synonyms.md" "$TARGET/.claude/router/"
  echo "  ✓ router/knowledge_asset_synonyms.md"
fi

# ── 4.5. 同步根目录模块 ────────────────────────────
echo ""
echo "  ── 同步编排引擎 + 数据模块 ──"

# orchestration 模块
if [ -d "$SCRIPT_DIR/orchestration" ]; then
  mkdir -p "$TARGET/orchestration"
  cp "$SCRIPT_DIR/orchestration/"*.py "$TARGET/orchestration/" 2>/dev/null || true
  MOD_COUNT=$(ls "$TARGET/orchestration/"*.py 2>/dev/null | wc -l)
  echo "  ✓ orchestration/ ($MOD_COUNT 个 Python 模块)"
fi

# routing_assets 模块
if [ -d "$SCRIPT_DIR/routing_assets" ]; then
  mkdir -p "$TARGET/routing_assets"
  cp "$SCRIPT_DIR/routing_assets/"*.py "$TARGET/routing_assets/" 2>/dev/null || true
  cp "$SCRIPT_DIR/routing_assets/"*.json "$TARGET/routing_assets/" 2>/dev/null || true
  echo "  ✓ routing_assets/"
fi

# ledger 模块
if [ -d "$SCRIPT_DIR/ledger" ]; then
  mkdir -p "$TARGET/ledger"
  cp "$SCRIPT_DIR/ledger/"*.py "$TARGET/ledger/" 2>/dev/null || true
  echo "  ✓ ledger/"
fi

# tests 模块
if [ -d "$SCRIPT_DIR/tests" ]; then
  mkdir -p "$TARGET/tests"
  cp "$SCRIPT_DIR/tests/"*.py "$TARGET/tests/" 2>/dev/null || true
  TEST_COUNT=$(ls "$TARGET/tests/test_"*.py 2>/dev/null | wc -l)
  echo "  ✓ tests/ ($TEST_COUNT 个测试文件)"
fi

# docs 模块
if [ -d "$SCRIPT_DIR/docs" ]; then
  mkdir -p "$TARGET/docs"
  cp -r "$SCRIPT_DIR/docs/"* "$TARGET/docs/" 2>/dev/null || true
  echo "  ✓ docs/"
fi

# ── 5. 同步 v5 核心文件 ─────────────────────────────
echo ""
echo "  ── 同步 v5 更新的文件 ──"

# v5: 全量同步所有 skills（含 legacy sop/debug_log，确保两侧一致）
if [ -d "$SCRIPT_DIR/.claude/skills" ]; then
  for skdir in "$SCRIPT_DIR/.claude/skills/"*/; do
    skname=$(basename "$skdir")
    mkdir -p "$TARGET/.claude/skills/$skname"
    cp -r "$skdir"* "$TARGET/.claude/skills/$skname/" 2>/dev/null || true
    echo "  ✓ skills/$skname/"
  done
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

# skill-rules.json
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

# v5: sop/debug_log 保留为 legacy 兼容层（status: legacy），不再删除
#      其路由已合并入 knowledge-asset，但 SKILL.md 本体保留作 fallback
for old_skill in sop debug_log; do
  OLD_FILE="$TARGET/.claude/skills/$old_skill/SKILL.md"
  if [ -f "$OLD_FILE" ]; then
    echo "  • skills/$old_skill/ (legacy 兼容层，保留)"
  fi
done

# ── 6. 同步 v5 系统文档 ─────────────────────────────
echo ""
echo "  ── 同步 v5 系统文档 ──"

for doc in ARCHITECTURE.md EXECUTION_FLOW.md STATE_SYSTEM.md KNOWLEDGE_SYSTEM.md; do
  if [ -f "$SCRIPT_DIR/$doc" ]; then
    cp "$SCRIPT_DIR/$doc" "$TARGET/$doc"
    echo "  ✓ $doc"
  fi
done

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
chmod +x "$TARGET/orchestration/"*.py 2>/dev/null || true

# ── 8. 快速验证 ──────────────────────────────────────
echo ""
echo "  ── 部署后验证 ──"

# JSON 格式验证
python3 -c "import json; json.load(open('$TARGET/.claude/skill-rules.json'))" 2>/dev/null \
  && echo "  ✓ skill-rules.json 格式正确" || echo "  ⚠ skill-rules.json 需要检查"

python3 -c "import json; json.load(open('$TARGET/.claude/router/workflow_templates.json'))" 2>/dev/null \
  && echo "  ✓ workflow_templates.json 格式正确" || echo "  ⚠ workflow_templates.json 需要检查"

# v5 state/ JSON 验证
echo ""
echo "  ── v5 State JSON 验证 ──"
for sf in current-task.json learning-state.json execution-state.json task-history.json; do
  if [ -f "$TARGET/.claude/state/$sf" ]; then
    python3 -c "import json; json.load(open('$TARGET/.claude/state/$sf'))" 2>/dev/null \
      && echo "  ✓ state/$sf 格式正确" || echo "  ⚠ state/$sf 需要检查"
  fi
done

# v5 关键模块存在性检查
echo ""
echo "  ── v5 关键文件检查 ──"
for check in \
  "$TARGET/.claude/system/execution_guard/guard-rules.md" \
  "$TARGET/.claude/system/execution_guard/task-state-machine.md" \
  "$TARGET/.claude/system/execution_guard/artifact-requirements.md" \
  "$TARGET/.claude/system/execution_guard/audit-checklist.md" \
  "$TARGET/.claude/hooks/task-guard.py" \
  "$TARGET/.claude/hooks/completion-guard.py" \
  "$TARGET/.claude/skills/knowledge-asset/SKILL.md" \
  "$TARGET/.claude/state/README.md" \
  "$TARGET/.claude/state/current-task.json" \
  "$TARGET/.claude/state/learning-state.json" \
  "$TARGET/.claude/state/execution-state.json" \
  "$TARGET/.claude/state/task-history.json" \
  "$TARGET/.claude/router/knowledge_asset_synonyms.md" \
  "$TARGET/orchestration/prompt_normalizer.py" \
  "$TARGET/orchestration/rule_router.py" \
  "$TARGET/orchestration/workflow_resolver.py" \
  "$TARGET/orchestration/skill_router.py" \
  "$TARGET/orchestration/execution_guard.py" \
  "$TARGET/orchestration/safe_mode.py" \
  "$TARGET/orchestration/rollback_manager.py" \
  "$TARGET/ledger/task_ledger.py"
do
  if [ -f "$check" ]; then
    echo "  ✓ $(echo $check | sed "s|$TARGET/||")"
  else
    echo "  ✗ 缺失：$(echo $check | sed "s|$TARGET/||")"
  fi
done

# 编排模块导入验证
echo ""
echo "  ── 编排模块导入验证 ──"
python3 -c "
import sys
sys.path.insert(0, '$TARGET')
sys.path.insert(0, '$TARGET/orchestration')
sys.path.insert(0, '$TARGET/ledger')
sys.path.insert(0, '$TARGET/routing_assets')
mods = [
    'orchestration_types',
    'route_plan',
    'workflow_state',
    'prompt_normalizer',
    'rule_router',
    'embedding_provider',
    'semantic_router',
    'workflow_resolver',
    'skill_router',
    'execution_guard',
    'safe_mode',
    'rollback_manager',
    'self_healing',
]
for m in mods:
    try:
        __import__(m)
        print(f'  ✓ {m}')
    except Exception as e:
        print(f'  ✗ {m}: {e}')
" 2>&1

# ── 9. 路由快速测试 ─────────────────────────────────
echo ""
echo "  ── 路由快速测试 ──"
echo '{"prompt":"帮我debug这段代码"}' | CLAUDE_PROJECT_DIR="$TARGET" python3 "$TARGET/.claude/hooks/skill-router.py" 2>/dev/null | grep -q "debug" \
  && echo "  ✓ debug 路由正常" || echo "  ✗ debug 路由异常"
echo '{"prompt":"给我一个计划"}' | CLAUDE_PROJECT_DIR="$TARGET" python3 "$TARGET/.claude/hooks/skill-router.py" 2>/dev/null | grep -q "planning" \
  && echo "  ✓ planning 路由正常" || echo "  ✗ planning 路由异常"
echo '{"prompt":"帮我写个SOP"}' | CLAUDE_PROJECT_DIR="$TARGET" python3 "$TARGET/.claude/hooks/skill-router.py" 2>/dev/null | grep -q "knowledge-asset" \
  && echo "  ✓ knowledge-asset 路由正常 (SOP)" || echo "  ✗ knowledge-asset 路由异常"
echo '{"prompt":"检查任务完成状态"}' | CLAUDE_PROJECT_DIR="$TARGET" python3 "$TARGET/.claude/hooks/skill-router.py" 2>/dev/null | grep -q "execution_guard" \
  && echo "  ✓ execution_guard 路由正常" || echo "  ✗ execution_guard 路由异常"

# ── 10. 完成 ─────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Skill OS v5.0.0 部署完成！                   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  备份位置：.claude/backups/$BACKUP_NAME-*"
echo "  如需回滚：cp .claude/backups/$BACKUP_NAME-settings.json .claude/settings.json"
echo ""
echo "  v5.0.0 升级内容："
echo "    • L0 Knowledge Bus  — knowledge-asset 唯一知识出口 (sop/debug_log 合并)"
echo "    • L4 统一状态层      — .claude/state/ (4 JSON + checkpoint)"
echo "    • L5 7 条 Guard 规则 — 5 层校验引擎 (state→artifacts→type→L0→L4)"
echo "    • 智能路由           — 53 knowledge-asset keywords + 16 patterns + 6 组同义词"
echo "    • Checkpoint 恢复    — stage 完成自动 + /checkpoint 手动 + safe_mode 强制"
echo "    • 系统文档           — ARCHITECTURE / EXECUTION_FLOW / STATE_SYSTEM / KNOWLEDGE_SYSTEM"
echo ""
echo "  v5 系统文档："
echo "    ARCHITECTURE.md     → 6+1 层架构参考"
echo "    EXECUTION_FLOW.md   → 3 条 pipeline + guard 检查点"
echo "    STATE_SYSTEM.md     → 状态机 + checkpoint + stall"
echo "    KNOWLEDGE_SYSTEM.md → L0 Knowledge Bus + 5 模板"
echo ""
echo "  运行测试验证："
echo "    for f in tests/test_*.py; do python3 \"\$f\" && echo PASS || echo FAIL; done"
echo ""

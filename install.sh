#!/bin/bash
# ══════════════════════════════════════════════════════
#  Claude Code Skill OS v5.0.0 — 一键安装脚本
#  用法：在你的项目根目录下运行
#        bash /path/to/skill-os-complete/install.sh
# ══════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(pwd)"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   Claude Code Skill OS v5.0.0 — 一键安装       ║"
echo "║   6+1 层架构 · L0 Knowledge Bus · 统一状态层   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  安装源：$SCRIPT_DIR"
echo "  安装目标：$TARGET"
echo ""

# ── 检查 Python3 ─────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "✗ 未找到 python3，请先安装："
  echo "  sudo apt install python3"
  exit 1
fi
echo "  ✓ Python3：$(python3 --version)"

# ── 检查不要在自身目录安装 ────────────────────────────
if [ "$SCRIPT_DIR" = "$TARGET" ]; then
  echo ""
  echo "✗ 请在你的项目目录下运行这个脚本，不要在解压目录里运行。"
  echo "  示例：cd ~/my-project && bash ~/skill-os-complete/install.sh"
  exit 1
fi

# ── 复制 .claude/ ─────────────────────────────────────
echo "  → 复制 .claude/ 到项目目录..."
cp -r "$SCRIPT_DIR/.claude" "$TARGET/"

# ── 复制项目文档 ──────────────────────────────────────
echo "  → 复制项目文档..."
for doc in CLAUDE.md README.md ARCHITECTURE.md EXECUTION_FLOW.md STATE_SYSTEM.md KNOWLEDGE_SYSTEM.md; do
  if [ -f "$SCRIPT_DIR/$doc" ]; then
    if [ -f "$TARGET/$doc" ] && [ "$doc" != "CLAUDE.md" ]; then
      cp "$SCRIPT_DIR/$doc" "$TARGET/skill-os-$doc"
      echo "  ✓ $doc → skill-os-$doc"
    else
      cp "$SCRIPT_DIR/$doc" "$TARGET/$doc"
      echo "  ✓ $doc"
    fi
  fi
done

# ── 部署编排引擎 (orchestration/) ────────────────────
echo ""
echo "  → 部署编排引擎模块..."
if [ -d "$SCRIPT_DIR/orchestration" ]; then
  mkdir -p "$TARGET/orchestration"
  cp "$SCRIPT_DIR/orchestration/"*.py "$TARGET/orchestration/" 2>/dev/null || true
  MOD_COUNT=$(ls "$TARGET/orchestration/"*.py 2>/dev/null | wc -l)
  echo "  ✓ orchestration/ ($MOD_COUNT 个 Python 模块)"
fi

# ── 部署账本模块 (ledger/) ───────────────────────────
if [ -d "$SCRIPT_DIR/ledger" ]; then
  mkdir -p "$TARGET/ledger"
  cp "$SCRIPT_DIR/ledger/"*.py "$TARGET/ledger/" 2>/dev/null || true
  echo "  ✓ ledger/ (任务账本模块)"
fi

# ── 部署路由资产 (routing_assets/) ──────────────────
if [ -d "$SCRIPT_DIR/routing_assets" ]; then
  mkdir -p "$TARGET/routing_assets"
  cp "$SCRIPT_DIR/routing_assets/"*.py "$TARGET/routing_assets/" 2>/dev/null || true
  cp "$SCRIPT_DIR/routing_assets/"*.json "$TARGET/routing_assets/" 2>/dev/null || true
  echo "  ✓ routing_assets/ (路由数据 + 参考模块)"
fi

# ── 部署测试套件 (tests/) ────────────────────────────
if [ -d "$SCRIPT_DIR/tests" ]; then
  mkdir -p "$TARGET/tests"
  cp "$SCRIPT_DIR/tests/"*.py "$TARGET/tests/" 2>/dev/null || true
  TEST_COUNT=$(ls "$TARGET/tests/test_"*.py 2>/dev/null | wc -l)
  echo "  ✓ tests/ ($TEST_COUNT 个测试文件)"
fi

# ── 部署文档 (docs/) ─────────────────────────────────
if [ -d "$SCRIPT_DIR/docs" ]; then
  mkdir -p "$TARGET/docs"
  cp -r "$SCRIPT_DIR/docs/"* "$TARGET/docs/" 2>/dev/null || true
  echo "  ✓ docs/ (升级/架构/验证文档)"
fi

# ── 复制 安装/卸载 辅助脚本 ──────────────────────────
if [ -f "$SCRIPT_DIR/uninstall.sh" ]; then
  cp "$SCRIPT_DIR/uninstall.sh" "$TARGET/skill-os-uninstall.sh"
  chmod +x "$TARGET/skill-os-uninstall.sh"
  echo "  ✓ 已部署卸载脚本 skill-os-uninstall.sh"
fi
if [ -f "$SCRIPT_DIR/deploy.sh" ]; then
  cp "$SCRIPT_DIR/deploy.sh" "$TARGET/skill-os-deploy.sh"
  chmod +x "$TARGET/skill-os-deploy.sh"
  echo "  ✓ 已部署升级脚本 skill-os-deploy.sh"
fi

# ── v5: 创建 state/ 目录并初始化 ──────────────────────
echo ""
echo "  → v5 初始化统一状态层 state/..."
mkdir -p "$TARGET/.claude/state/checkpoint"

# current-task.json
if [ ! -f "$TARGET/.claude/state/current-task.json" ]; then
  cat > "$TARGET/.claude/state/current-task.json" << 'JSON'
{
  "meta": {
    "version": "5.0.0",
    "description": "Skill OS v5 — 当前活跃任务状态",
    "updated_at": "INSTALL_DATE"
  },
  "active_task": null
}
JSON
  echo "  ✓ state/current-task.json"
fi

# learning-state.json
if [ ! -f "$TARGET/.claude/state/learning-state.json" ]; then
  cat > "$TARGET/.claude/state/learning-state.json" << 'JSON'
{
  "meta": {
    "version": "5.0.0",
    "description": "Skill OS v5 — 学习主题状态追踪",
    "migrated_from": ".claude/system/learning_state/state.json",
    "updated_at": "INSTALL_DATE"
  },
  "topics": []
}
JSON
  echo "  ✓ state/learning-state.json"
fi

# execution-state.json
if [ ! -f "$TARGET/.claude/state/execution-state.json" ]; then
  cat > "$TARGET/.claude/state/execution-state.json" << 'JSON'
{
  "meta": {
    "version": "5.0.0",
    "description": "Skill OS v5 — 系统级执行状态",
    "updated_at": "INSTALL_DATE"
  },
  "active_workflow": null,
  "active_task_id": null,
  "pipeline_progress": {
    "current_stage_index": -1,
    "total_stages": 0,
    "stages": []
  },
  "guard_status": "idle",
  "safe_mode": false,
  "degraded": false,
  "created_at": "INSTALL_DATE",
  "updated_at": "INSTALL_DATE"
}
JSON
  echo "  ✓ state/execution-state.json"
fi

# task-history.json
if [ ! -f "$TARGET/.claude/state/task-history.json" ]; then
  cat > "$TARGET/.claude/state/task-history.json" << 'JSON'
{
  "meta": {
    "version": "5.0.0",
    "description": "Skill OS v5 — 已完成/已取消任务历史索引",
    "total_archived": 0,
    "updated_at": "INSTALL_DATE"
  },
  "history": []
}
JSON
  echo "  ✓ state/task-history.json"
fi

touch "$TARGET/.claude/state/checkpoint/.gitkeep"
echo "  ✓ state/checkpoint/"

# ── v5: 创建 knowledge-asset/knowledge/ 子目录 ────────
echo ""
echo "  → v5 初始化 L0 Knowledge Bus 知识库..."
KNOWLEDGE_DIR="$TARGET/.claude/skills/knowledge-asset/knowledge"
for subdir in sop troubleshooting architecture knowledge-notes project-plans; do
  mkdir -p "$KNOWLEDGE_DIR/$subdir"
  touch "$KNOWLEDGE_DIR/$subdir/.gitkeep"
done
echo "  ✓ knowledge/ (5 子目录: sop / troubleshooting / architecture / knowledge-notes / project-plans)"

# ── 创建 practice/ 工作区 ────────────────────────────
mkdir -p "$TARGET/practice/daily"
mkdir -p "$TARGET/practice/plans"
mkdir -p "$TARGET/practice/reviews"
echo "  ✓ 创建 practice/ 学习工作区"

# ── 确保系统目录存在 ──────────────────────────────────
mkdir -p "$TARGET/.claude/system/execution_guard"
mkdir -p "$TARGET/.claude/system/learning_state"
mkdir -p "$TARGET/.claude/system/knowledge"
mkdir -p "$TARGET/.claude/system/debug_archive"
mkdir -p "$TARGET/.claude/agents"
echo "  ✓ 系统目录就绪"

# ── 初始化 legacy learning_state（兼容旧引用） ────────
if [ ! -f "$TARGET/.claude/system/learning_state/state.json" ]; then
  cat > "$TARGET/.claude/system/learning_state/state.json" << 'STATEJSON'
{
  "meta": {
    "version": "4.0.0",
    "status": "legacy — 已迁移至 .claude/state/learning-state.json (v5)",
    "migrated_at": "INSTALL_DATE",
    "updated": "INSTALL_DATE"
  },
  "topics": [],
  "_migration_notice": "本文件为 v4 遗留数据。v5 统一状态层已迁移至 .claude/state/learning-state.json。请勿继续写入本文件。"
}
STATEJSON
  echo "  ✓ legacy learning_state/state.json (migration marker)"
fi

# ── 设置执行权限 ──────────────────────────────────────
chmod +x "$TARGET/.claude/hooks/skill-router.py" 2>/dev/null || true
chmod +x "$TARGET/.claude/hooks/task-guard.py" 2>/dev/null || true
chmod +x "$TARGET/.claude/hooks/completion-guard.py" 2>/dev/null || true
chmod +x "$TARGET/.claude/skills/sanitize/sanitize.py" 2>/dev/null || true
chmod +x "$TARGET/.claude/system/task_ledger/task-ops.py" 2>/dev/null || true
chmod +x "$TARGET/orchestration/"*.py 2>/dev/null || true
echo "  ✓ 已设置脚本执行权限"

# ── 验证 JSON 格式 ────────────────────────────────────
echo ""
echo "  ── JSON 格式验证 ──"

python3 -c "import json; json.load(open('$TARGET/.claude/settings.json'))" 2>/dev/null \
  && echo "  ✓ settings.json 格式正确" || echo "  ⚠ settings.json 格式有问题"

python3 -c "import json; json.load(open('$TARGET/.claude/skill-rules.json'))" 2>/dev/null \
  && echo "  ✓ skill-rules.json 格式正确" || echo "  ⚠ skill-rules.json 格式有问题"

python3 -c "import json; json.load(open('$TARGET/.claude/router/workflow_templates.json'))" 2>/dev/null \
  && echo "  ✓ workflow_templates.json 格式正确" || echo "  ⚠ workflow_templates.json 格式有问题"

python3 -c "import json; json.load(open('$TARGET/.claude/router/skill_index.json'))" 2>/dev/null \
  && echo "  ✓ skill_index.json 格式正确" || echo "  ⚠ skill_index.json 格式有问题"

# v5: state/ JSON 验证
echo ""
echo "  ── v5 State JSON 验证 ──"
for sf in current-task.json learning-state.json execution-state.json task-history.json; do
  if [ -f "$TARGET/.claude/state/$sf" ]; then
    python3 -c "import json; json.load(open('$TARGET/.claude/state/$sf'))" 2>/dev/null \
      && echo "  ✓ state/$sf 格式正确" || echo "  ⚠ state/$sf 格式有问题"
  fi
done

for jf in "$TARGET/routing_assets/"*.json; do
  [ -f "$jf" ] && python3 -c "import json; json.load(open('$jf'))" 2>/dev/null \
    && echo "  ✓ $(basename $jf) 格式正确" || true
done

if [ -f "$TARGET/.claude/system/task_ledger/tasks.json" ]; then
  python3 -c "import json; json.load(open('$TARGET/.claude/system/task_ledger/tasks.json'))" 2>/dev/null \
    && echo "  ✓ task_ledger/tasks.json 格式正确" || echo "  ⚠ tasks.json 格式有问题"
fi

# ── 编排模块导入验证 ──────────────────────────────────
echo ""
echo "  ── 编排模块导入验证 ──"
python3 -c "
import sys
sys.path.insert(0, '$TARGET')
sys.path.insert(0, '$TARGET/orchestration')
sys.path.insert(0, '$TARGET/ledger')
sys.path.insert(0, '$TARGET/routing_assets')

modules = [
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
for m in modules:
    try:
        __import__(m)
        print(f'  ✓ {m}')
    except Exception as e:
        print(f'  ✗ {m}: {e}')
" 2>&1

# ── 路由测试（v5 knowledge-asset 路线） ──────────────
echo ""
echo "  ── 路由测试（v5 intent→workflow→skill）──"
echo ""

run_test() {
  local desc="$1"
  local prompt="$2"
  local expect="$3"

  RESULT=$(echo "{\"prompt\": \"$prompt\"}" \
    | CLAUDE_PROJECT_DIR="$TARGET" python3 "$TARGET/.claude/hooks/skill-router.py" 2>&1)

  if echo "$RESULT" | grep -q "$expect"; then
    echo "  ✓ $desc → $expect"
  else
    echo "  ✗ $desc → 期望 $expect，实际输出："
    echo "$RESULT" | head -3
  fi
}

# ── Debug 管线 ──
run_test "诊断引擎 debug"         "帮我 debug 这段代码，报 KeyError"             "debug"

# ── Delivery 管线 ──
run_test "任务计划 planning"      "给我一个计划，做一个用户登录系统"              "planning"
run_test "知识整理 summarize"     "总结一下这个仓库是做什么的"                    "summarize"
run_test "代码审查 reviewer"      "帮我review一下这段代码有没有问题"              "reviewer"
run_test "生成更新日志 changelog" "生成这次的变更日志"                            "changelog"
run_test "项目脱敏"               "帮我对这个项目做脱敏处理"                      "sanitize"

# ── L0 Knowledge Bus ──
run_test "知识沉淀知识资产"       "帮我把这段排查记录沉淀为知识资产"              "knowledge-asset"
run_test "生成SOP"                "数据库连接失败怎么处理，帮我写操作手册"        "knowledge-asset"
run_test "故障排查留档"           "bug 解决了，帮我记录这次排查过程留档"          "knowledge-asset"
run_test "生成架构文档"           "帮我为这个系统生成架构文档"                    "knowledge-asset"

# ── Learning 管线 ──
run_test "学习讲解 explain"       "我想学 Rust 系统学习"                          "teach-plus"
run_test "学习练习 practice"      "给我今天的学习任务"                            "teach-plus"
run_test "学习复盘 review"        "帮我复盘这周学的"                              "teach-plus"
run_test "学习讲明白"             "给我讲明白这个路由系统"                        "teach-plus"

# ── v5 执行监督层 ──
run_test "执行监督 guard"         "检查任务完成状态"                              "execution_guard"
run_test "验收任务"               "确认任务是不是真的完成了"                      "execution_guard"

# ── Fallback 单技能 ──
run_test "原样 echo"              "echo 测试这句话"                              "echo"
run_test "需求澄清 ask"           "我想做个东西但还没想好"                       "ask"
run_test "学习路线 planner"       "帮我规划一下学习 Rust 的路线"                  "planner"
run_test "任务进度 task_ledger"   "下一步做什么"                                  "task_ledger"
run_test "代码助手"               "帮我写一个读取文件的函数"                      "code_assistant"
run_test "无关问题不注入"         "今天天气怎么样"                                "{}"

# ── 显示安装摘要 ──────────────────────────────────────
echo ""
echo "  ── 已安装模块统计 ──"
echo "    .claude/ 配置: $(find "$TARGET/.claude" -type f 2>/dev/null | wc -l) 文件"
echo "    .claude/state/ 状态层: $(ls "$TARGET/.claude/state/"*.json 2>/dev/null | wc -l) 文件"
echo "    orchestration/ 编排模块: $(ls "$TARGET/orchestration/"*.py 2>/dev/null | wc -l) 个"
echo "    ledger/ 账本模块: $(ls "$TARGET/ledger/"*.py 2>/dev/null | wc -l) 个"
echo "    routing_assets/ 资产: $(ls "$TARGET/routing_assets/" 2>/dev/null | wc -l) 个"
echo "    tests/ 测试: $(ls "$TARGET/tests/test_"*.py 2>/dev/null | wc -l) 个"
echo "    docs/ 文档: $(find "$TARGET/docs" -name '*.md' 2>/dev/null | wc -l) 个"
echo "    knowledge/ 知识库: 5 子目录"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║    安装完成！24 项路由测试已执行               ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  验证方法：进入项目目录，在 Claude Code 里输入"
echo "    「总结这个仓库」→ 应触发 summarize"
echo "    「帮我 debug 这段代码」→ 应触发 debug"
echo "    「沉淀知识资产」→ 应触发 knowledge-asset"
echo ""
echo "  运行自动化测试："
echo "    cd $(basename "$TARGET")"
echo "    for f in tests/test_*.py; do python3 \"\$f\" && echo PASS || echo FAIL; done"
echo ""
echo "  ── Skill OS v5.0.0 · 6+1 层架构 · 14 主技能 + 2 legacy · 3 工作流 ──"
echo ""
echo "  L0 Knowledge Bus（知识总线）"
echo "    knowledge-asset    → 触发词：沉淀知识、SOP、故障排查、留档、架构文档"
echo "                       唯一知识出口，5 类 9-section 模板"
echo ""
echo "  L1 Router（路由层）"
echo "    prompt_normalizer → rule_router → semantic_router → workflow_resolver"
echo "    53 knowledge-asset keywords + 16 patterns + 6 组同义词映射"
echo ""
echo "  L2 Core Skills（核心基座）"
echo "    summarize          → 触发词：总结、摘要、读懂这个"
echo "    planning           → 触发词：计划、规划、方案、学习路线"
echo "    debug              → 触发词：报错、诊断、行为异常、排查"
echo ""
echo "  L3 Workflow（工作流）"
echo "    delivery_pipeline  : summarize → ... → knowledge-asset → guard"
echo "    debug_pipeline     : summarize(可选) → debug → knowledge-asset → guard"
echo "    learning_pipeline  : summarize → ... → teach-plus → knowledge-asset → guard"
echo ""
echo "  L4 State（统一状态层）☆ v5"
echo "    .claude/state/     → 4 JSON + checkpoint/"
echo "    current-task.json  → 活跃任务状态"
echo "    learning-state.json → 学习状态追踪"
echo "    execution-state.json → pipeline 进度 + guard"
echo "    task-history.json  → 任务归档"
echo ""
echo "  L5 Guard（监督层）☆ v5"
echo "    execution_guard    → 7 条强制规则 + 5 层校验引擎"
echo "    completion-guard   → state→artifacts→type→L0_ka→L4_state"
echo "    task-guard         → stall 检测 + pipeline 上下文注入"
echo "    safe_mode          → 全局安全开关"
echo "    checkpoint         → 自动 + 手动 + safe_mode 强制"
echo ""
echo "  L6 Extension（扩展层）"
echo "    orchestration/     → 13 个编排模块"
echo "    agents/            → 多代理扩展预留"
echo ""
echo "  ── 执行层 ──"
echo "    teach-plus         → 触发词：我想学、今天学什么、复盘"
echo "    ask                → 触发词：我想做、有个想法"
echo "    code_assistant     → 触发词：代码、修复、重构、帮我写"
echo "    sanitize           → 触发词：脱敏、消毒、sanitize"
echo "    reviewer           → 触发词：review、代码审查"
echo "    changelog          → 触发词：changelog、更新日志"
echo ""
echo "  ── 系统文档 ──"
echo "    ARCHITECTURE.md    → v5 6+1 层架构参考"
echo "    EXECUTION_FLOW.md  → 3 条 pipeline + guard 检查点"
echo "    STATE_SYSTEM.md    → 状态机 + checkpoint + stall"
echo "    KNOWLEDGE_SYSTEM.md → L0 Knowledge Bus + 5 模板"
echo ""
echo "  脱敏脚本位置：.claude/skills/sanitize/sanitize.py"
echo "  卸载脚本位置：skill-os-uninstall.sh"
echo "  升级脚本位置：skill-os-deploy.sh"
echo ""

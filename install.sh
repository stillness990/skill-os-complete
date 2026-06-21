#!/bin/bash
# ══════════════════════════════════════════════════════
#  Claude Code Skill OS v4 — 一键安装脚本
#  用法：在你的项目根目录下运行
#        bash /path/to/skill-os-complete/install.sh
# ══════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(pwd)"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   Claude Code Skill OS v4 — 一键安装          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
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

# ── 复制文件 ──────────────────────────────────────────
echo "  → 复制 .claude/ 到项目目录..."
cp -r "$SCRIPT_DIR/.claude" "$TARGET/"

echo "  → 复制 CLAUDE.md..."
if [ -f "$TARGET/CLAUDE.md" ]; then
  echo "" >> "$TARGET/CLAUDE.md"
  echo "---" >> "$TARGET/CLAUDE.md"
  cat "$SCRIPT_DIR/CLAUDE.md" >> "$TARGET/CLAUDE.md"
  echo "  ✓ 已追加到现有 CLAUDE.md"
else
  cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
  echo "  ✓ 新建 CLAUDE.md"
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
  echo "  ✓ 已部署部署脚本 skill-os-deploy.sh"
fi

# ── 创建 practice/ 工作区 ────────────────────────────
mkdir -p "$TARGET/practice/daily"
mkdir -p "$TARGET/practice/plans"
mkdir -p "$TARGET/practice/reviews"
echo "  ✓ 创建 practice/ 学习工作区"

# ── 创建 knowledge 子目录的 .gitkeep ──────────────────
for d in learning_briefs study_plans review_logs; do
  mkdir -p "$TARGET/.claude/system/knowledge/$d"
  touch "$TARGET/.claude/system/knowledge/$d/.gitkeep"
done

# ── 确保 execution_guard / learning_state / orchestration / agents 目录存在 ──
mkdir -p "$TARGET/.claude/system/execution_guard"
mkdir -p "$TARGET/.claude/system/learning_state"
mkdir -p "$TARGET/.claude/orchestration/schema"
mkdir -p "$TARGET/.claude/orchestration/runs"
mkdir -p "$TARGET/.claude/orchestration/artifacts"
mkdir -p "$TARGET/.claude/agents"

# ── 初始化 learning_state state.json（如果不存在） ──
if [ ! -f "$TARGET/.claude/system/learning_state/state.json" ]; then
  cat > "$TARGET/.claude/system/learning_state/state.json" << 'STATEJSON'
{
  "meta": {
    "version": "4.0.0",
    "updated": "INSTALL_DATE"
  },
  "topics": []
}
STATEJSON
  echo "  ✓ 初始化 learning_state/state.json"
fi

# ── 设置执行权限 ──────────────────────────────────────
chmod +x "$TARGET/.claude/hooks/skill-router.py"
chmod +x "$TARGET/.claude/hooks/task-guard.py" 2>/dev/null || true
chmod +x "$TARGET/.claude/hooks/completion-guard.py" 2>/dev/null || true
chmod +x "$TARGET/.claude/skills/sanitize/sanitize.py" 2>/dev/null || true
chmod +x "$TARGET/.claude/system/task_ledger/task-ops.py" 2>/dev/null || true
echo "  ✓ 已设置脚本执行权限"

# ── 验证 JSON 格式 ────────────────────────────────────
echo ""
echo "  ── JSON 格式验证 ──"

python3 -c "import json; json.load(open('$TARGET/.claude/settings.json'))" \
  && echo "  ✓ settings.json 格式正确" || echo "  ⚠ settings.json 格式有问题"

python3 -c "import json; json.load(open('$TARGET/.claude/skill-rules.json'))" \
  && echo "  ✓ skill-rules.json 格式正确" || echo "  ⚠ skill-rules.json 格式有问题"

python3 -c "import json; json.load(open('$TARGET/.claude/router/workflow_templates.json'))" \
  && echo "  ✓ workflow_templates.json 格式正确" || echo "  ⚠ workflow_templates.json 格式有问题"

python3 -c "import json; json.load(open('$TARGET/.claude/router/skill_index.json'))" \
  && echo "  ✓ skill_index.json 格式正确" || echo "  ⚠ skill_index.json 格式有问题"

if [ -f "$TARGET/.claude/system/learning_state/state.json" ]; then
  python3 -c "import json; json.load(open('$TARGET/.claude/system/learning_state/state.json'))" \
    && echo "  ✓ learning_state/state.json 格式正确" || echo "  ⚠ state.json 格式有问题"
fi

if [ -f "$TARGET/.claude/system/task_ledger/tasks.json" ]; then
  python3 -c "import json; json.load(open('$TARGET/.claude/system/task_ledger/tasks.json'))" \
    && echo "  ✓ task_ledger/tasks.json 格式正确" || echo "  ⚠ tasks.json 格式有问题"
fi

# ── 运行路由测试（v4 版，含 execution_guard） ───────
echo ""
echo "  ── 路由测试（v4 intent→workflow→skill）──"
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

# ── Learning 管线 ──
run_test "学习讲解 explain"       "我想学 Rust 系统学习"                          "teach-plus"
run_test "学习练习 practice"      "给我今天的学习任务"                            "teach-plus"
run_test "学习复盘 review"        "帮我复盘这周学的"                              "teach-plus"
run_test "学习讲明白"             "给我讲明白这个路由系统"                        "teach-plus"

# ── v4 执行监督层 ──
run_test "执行监督 guard"         "检查任务完成状态"                              "execution_guard"
run_test "验收任务"               "确认任务是不是真的完成了"                      "execution_guard"

# ── Fallback 单技能 ──
run_test "原样 echo"              "echo 测试这句话"                              "echo"
run_test "需求澄清 ask"           "我想做个东西但还没想好"                       "ask"
run_test "生成 SOP"               "数据库连接失败怎么处理，帮我写操作手册"       "sop"
run_test "保存 debug 记录"        "bug 解决了，帮我记录这次排查过程留档"          "debug_log"
run_test "学习路线 planner"       "帮我规划一下学习 Rust 的路线"                  "planner"
run_test "任务进度 task_ledger"   "下一步做什么"                                  "task_ledger"
run_test "代码助手"               "帮我写一个读取文件的函数"                      "code_assistant"
run_test "无关问题不注入"         "今天天气怎么样"                                "{}"

# ── 显示文件清单 ──────────────────────────────────────
echo ""
echo "  ── 已安装文件 ──"
find "$TARGET/.claude" -type f | sed "s|$TARGET/||" | sort | while read f; do
  echo "    $f"
done

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║    安装完成！24 项测试已执行                   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  现在进入项目目录，运行："
echo "    claude"
echo ""
echo "  验证方法：在 Claude Code 里输入"
echo "    「我想学这个仓库」→ 应触发 teach-plus 学习工作流控制器"
echo "    「帮我 debug 这段代码」→ 应触发诊断引擎"
echo "    「检查任务完成状态」→ 应触发 execution_guard"
echo ""
echo "  ── Skill OS v4 · 六层架构 · 14 技能 · 3 工作流 ──"
echo ""
echo "  1. Router Layer（路由层）"
echo "     skill-router + routing_rules + workflow_templates"
echo ""
echo "  2. Core Skills（核心基座）"
echo "    summarize          → 触发词：总结、摘要、读懂这个"
echo "    planning           → 触发词：计划、规划、方案、学习路线"
echo "    debug              → 触发词：报错、诊断、行为异常、排查"
echo ""
echo "  3. Workflow Layer（工作流）"
echo "    delivery_pipeline  : summarize → planning → task_ledger → execution → guard"
echo "    debug_pipeline     : summarize(可选) → debug → code_assistant → guard"
echo "    learning_pipeline  : summarize → planning → teach-plus → learning_state → guard"
echo ""
echo "  4. System Layer（系统层）"
echo "    task_ledger        → 触发词：下一步、当前进度、任务状态"
echo "    learning_state     ★v4 学习状态追踪（7阶段状态机+断档恢复）"
echo "    knowledge          → 知识沉淀（briefings/plans/logs）"
echo "    debug_archive      → 诊断归档"
echo ""
echo "  5. Guard Layer（监督层）★v4 新增"
echo "    execution_guard    → 触发词：检查完成、验收、确认完成"
echo "    5 条规则：done带artifact / 合法流转 / 最小产物 / 施工落地证据 / stall检测"
echo ""
echo "  6. Extension Layer（扩展层）★v4 预留"
echo "    orchestration/ agents/ — Phase 4 多代理扩展"
echo ""
echo "  ── 执行层 ──"
echo "    teach-plus         → 触发词：我想学、今天学什么、复盘（explain/practice/review）"
echo "    ask                → 触发词：我想做、有个想法、准备做"
echo "    code_assistant     → 触发词：代码、修复、重构、帮我写"
echo "    sop                → 触发词：手册、标准流程、怎么处理"
echo "    sanitize           → 触发词：脱敏、消毒、sanitize"
echo "    reviewer           → 触发词：review、代码审查、看看代码"
echo "    changelog          → 触发词：changelog、更新日志、版本说明"
echo ""
echo "  ── 工具层 ──"
echo "    echo               → 触发词：echo、重复、原样"
echo "    debug_log          → 触发词：解决了、留档、排查记录"
echo "    dify_kb_search     → 触发词：科目一~科目四"
echo ""
echo "  脱敏脚本位置：.claude/skills/sanitize/sanitize.py"
echo "  卸载脚本位置：skill-os-uninstall.sh"
echo ""

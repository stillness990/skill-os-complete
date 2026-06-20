#!/bin/bash
# ══════════════════════════════════════════════════════
#  Claude Code Skill OS — 一键安装脚本
#  用法：在你的项目根目录下运行
#        bash /path/to/skill-os-complete/install.sh
# ══════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(pwd)"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     Claude Code Skill OS — 开始安装          ║"
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
# 如果已有 CLAUDE.md，追加而不是覆盖
if [ -f "$TARGET/CLAUDE.md" ]; then
  echo "" >> "$TARGET/CLAUDE.md"
  echo "---" >> "$TARGET/CLAUDE.md"
  cat "$SCRIPT_DIR/CLAUDE.md" >> "$TARGET/CLAUDE.md"
  echo "  ✓ 已追加到现有 CLAUDE.md"
else
  cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
  echo "  ✓ 新建 CLAUDE.md"
fi

# ── 设置执行权限 ──────────────────────────────────────
chmod +x "$TARGET/.claude/hooks/skill-router.py"
chmod +x "$TARGET/.claude/skills/sanitize/sanitize.py"
echo "  ✓ 已设置脚本执行权限"

# ── 验证 JSON 格式 ────────────────────────────────────
python3 -c "import json; json.load(open('$TARGET/.claude/settings.json'))" \
  && echo "  ✓ settings.json 格式正确"

python3 -c "import json; json.load(open('$TARGET/.claude/skill-rules.json'))" \
  && echo "  ✓ skill-rules.json 格式正确"

# ── 运行路由测试 ─────────────────────────────────────
echo ""
echo "  运行路由测试..."
echo ""

run_test() {
  local desc="$1"
  local prompt="$2"
  local expect="$3"

  RESULT=$(echo "{\"prompt\": \"$prompt\"}" \
    | CLAUDE_PROJECT_DIR="$TARGET" python3 "$TARGET/.claude/hooks/skill-router.py")

  if echo "$RESULT" | grep -q "$expect"; then
    echo "  ✓ $desc → $expect"
  else
    echo "  ✗ $desc → 期望 $expect，实际输出："
    echo "$RESULT"
    exit 1
  fi
}

run_test "原样 echo"              "echo 测试这句话"                              "echo"
run_test "需求澄清 ask"           "我想做个东西但还没想好"                       "ask"
run_test "诊断引擎 debug"         "帮我 debug 这段代码，报 KeyError"             "debug"
run_test "知识整理 summarize"     "总结一下这个仓库是做什么的"                    "summarize"
run_test "生成 SOP"               "数据库连接失败怎么处理，帮我写操作手册"       "sop"
run_test "保存 debug 记录"        "bug 解决了，帮我记录这次排查过程留档"          "debug_log"
run_test "项目脱敏"               "帮我对这个项目做脱敏处理"                      "sanitize"
run_test "代码计划 planner"       "给我一个计划，做一个用户登录系统"              "planner"
run_test "通用计划 planner"       "帮我规划一下学习 Rust 的路线"                  "planner"
run_test "代码审查 reviewer"      "帮我review一下这段代码有没有问题"              "reviewer"
run_test "生成更新日志 changelog" "生成这次的变更日志"                            "changelog"
run_test "任务进度 task_manager"  "下一步做什么"                                  "task_manager"
run_test "学习编排 teach-plus"    "我想学 Rust 系统学习"                          "teach-plus"
run_test "代码助手"               "帮我写一个读取文件的函数"                      "code_assistant"
run_test "无关问题不注入"         "今天天气怎么样"                                "{}"

# ── 显示文件清单 ──────────────────────────────────────
echo ""
echo "  已安装文件："
find "$TARGET/.claude" -type f | sed "s|$TARGET/||" | sort | while read f; do
  echo "    $f"
done

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     安装完成！15 项测试全部通过 ✓            ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  现在进入项目目录，运行："
echo "    claude"
echo ""
echo "  验证方法：在 Claude Code 里输入"
echo "    「帮我 debug 这段代码，一直报 KeyError」"
echo "  看到诊断引擎的结构化回答就成功了。"
echo ""
echo "  14 个可用技能："
echo "    ask              → 触发词：我想做、有个想法、准备做"
echo "    echo             → 触发词：echo、重复、原样"
echo "    summarize        → 触发词：总结、摘要、读懂这个、分析仓库"
echo "    planner          → 触发词：计划、规划、方案、学习路线（代码任务→Plan Mode，通用任务→模板）"
echo "    task_manager     → 触发词：下一步、当前进度、任务状态"
echo "    code_assistant   → 触发词：代码、修复、重构、帮我写"
echo "    debug            → 触发词：报错、诊断、行为异常、排查"
echo "    sop              → 触发词：手册、标准流程、怎么处理"
echo "    debug_log        → 触发词：解决了、留档、排查记录"
echo "    sanitize         → 触发词：脱敏、消毒、sanitize、安全发布"
echo "    reviewer         → 触发词：review、代码审查、看看代码"
echo "    changelog        → 触发词：changelog、更新日志、版本说明"
echo "    dify_kb_search   → 触发词：科目一、科目二、科目三、科目四"
echo "    teach-plus       → 触发词：我想学、学会、每日练习、教我"
echo ""
echo "  完整工作流："
echo "    ask → summarize → planner → task_manager → code_assistant"
echo "                                             → sop"
echo "                                    ↓"
echo "                               debug → debug_log"
echo "                                    ↓"
echo "                               reviewer → changelog"
echo ""
echo "  学习工作流："
echo "    summarize → planner → teach-plus"
echo ""
echo "  脱敏脚本位置：.claude/skills/sanitize/sanitize.py"
echo "  用法：python .claude/skills/sanitize/sanitize.py scan <项目>"

#!/usr/bin/env python3
"""
Claude Code Skill Router Hook
触发时机: 每次用户发送消息之前（UserPromptSubmit）
作用:     自动分析内容，注入对应技能指令，无需手动 /skill-name
"""

import json
import os
import re
import sys


# ── 1. 读取 Claude Code 传入的 prompt ────────────────────────────────────────
try:
    data = json.load(sys.stdin)
except Exception:
    print(json.dumps({}))
    sys.exit(0)

prompt = data.get("prompt", "")
if not prompt.strip():
    print(json.dumps({}))
    sys.exit(0)


# ── 2. 读取路由规则文件 ───────────────────────────────────────────────────────
project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
rules_path  = os.path.join(project_dir, ".claude", "skill-rules.json")

try:
    with open(rules_path, "r", encoding="utf-8") as f:
        rules = json.load(f)["skills"]
except Exception:
    print(json.dumps({}))
    sys.exit(0)


# ── 3. 打分：关键词 +2，正则匹配 +3，基础优先级兜底 ──────────────────────────
lower  = prompt.lower()
scores = {}

for skill, meta in rules.items():
    score = meta.get("priority", 0)
    for kw in meta.get("keywords", []):
        if kw.lower() in lower:
            score += 2
    for pat in meta.get("intentPatterns", []):
        if re.search(pat, lower):
            score += 3
    scores[skill] = score

best_skill = max(scores, key=scores.get)
base_only  = rules[best_skill].get("priority", 0)
has_hit    = scores[best_skill] > base_only


# ── 4. 构造注入内容，或静默退出 ──────────────────────────────────────────────
if has_hit:
    score_lines = "\n".join(
        f"  {'→' if s == best_skill else ' '} {s:<18} score={scores[s]}"
        for s, _ in sorted(scores.items(), key=lambda x: -x[1])
    )

    # 为 planner 技能生成更强力的注入指令（嵌入决策逻辑，减少模型自行判断空间）
    if best_skill == "planner":
        skill_instruction = (
            f"MANDATORY workflow — you MUST follow these steps:\n"
            f"1. Determine task type:\n"
            f"   - Code tasks (involving code, files, projects, config, deploy, API, DB) → call EnterPlanMode tool, explore codebase, write plan using planner templates, then ExitPlanMode\n"
            f"   - Non-code tasks (study plan, travel, architecture doc, business process) → output plan using planner templates directly, do NOT call EnterPlanMode\n"
            f"2. If unsure, ask the user to clarify before proceeding.\n"
            f"DO NOT skip this — you MUST use Skill tool to load `planner` first."
        )
    else:
        skill_instruction = f"请先用 Skill 工具加载 `{best_skill}`，再根据该技能的规范回答。"

    injection = (
        f"\n\n╔═ SKILL ROUTER ══════════════════════════╗\n"
        f"║  自动激活技能: {best_skill:<26}║\n"
        f"╚═════════════════════════════════════════╝\n"
        f"路由得分:\n{score_lines}\n\n"
        f"[指令] {skill_instruction}\n"
    )
    print(json.dumps({"prompt_injection": injection}))
else:
    print(json.dumps({}))

sys.exit(0)

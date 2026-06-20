#!/usr/bin/env python3
"""
Claude Code Skill Router Hook — Skill OS v3 (Phase 1)
触发时机: 每次用户发送消息之前（UserPromptSubmit）
作用:     intent → workflow → primary_skill / secondary_skills
升级:    从 "单技能最高分命中" 升级为最小 workflow router
兼容:    保留旧版单 skill fallback 机制
"""

import json
import os
import sys

# ── 确保可以 import router 模块 ────────────────────────────────
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDE_DIR = os.path.dirname(HOOK_DIR)
sys.path.insert(0, CLAUDE_DIR)

from router.routing_rules import build_router_decision


# ── 1. 读取 Claude Code 传入的 prompt ────────────────────────
try:
    data = json.load(sys.stdin)
except Exception:
    print(json.dumps({}))
    sys.exit(0)

prompt = data.get("prompt", "")
if not prompt.strip():
    print(json.dumps({}))
    sys.exit(0)


# ── 2. 路由决策 ─────────────────────────────────────────────
decision = build_router_decision(prompt)

if not decision["has_hit"]:
    print(json.dumps({}))
    sys.exit(0)


# ── 3. 构建注入内容 ──────────────────────────────────────────
best_single = decision["best_single_skill"]
scores = decision["scores"]

# 得分展示（保留旧版兼容）
score_lines = "\n".join(
    f"  {'→' if s == best_single else ' '} {s:<18} score={scores[s]}"
    for s, _ in sorted(scores.items(), key=lambda x: -x[1])
)

# ── 4. 根据是否有 intent/workflow 选择不同的注入格式 ─────────
if decision["intent"] and decision["workflow"]:
    # ── Workflow 模式注入 ──
    primary = decision["primary_skill"]
    secondary = decision["secondary_skills"]
    sec_str = ", ".join(secondary) if secondary else "无"

    # 为 planner/planning 生成 EnterPlanMode 指令
    if primary in ("planning", "planner"):
        primary_instruction = (
            f"MANDATORY workflow — you MUST follow these steps:\n"
            f"1. Determine task type:\n"
            f"   - Code tasks (involving code, files, projects, config, deploy, API, DB) → call EnterPlanMode tool, explore codebase, write plan using planning templates, then ExitPlanMode\n"
            f"   - Non-code tasks (study plan, travel, architecture doc, business process) → output plan using planning templates directly, do NOT call EnterPlanMode\n"
            f"2. If unsure, ask the user to clarify before proceeding.\n"
            f"DO NOT skip this — you MUST use Skill tool to load `{primary}` first."
        )
    elif primary == "debug":
        primary_instruction = (
            f"MANDATORY diagnosis workflow — you MUST follow these steps:\n"
            f"1. Confirm the problem phenomenon with the user (re-state in your own words)\n"
            f"2. Identify impact scope and severity\n"
            f"3. Provide minimal reproduction steps\n"
            f"4. Propose 1-3 hypotheses (ranked by likelihood, with reasons)\n"
            f"5. Design verification steps for each hypothesis\n"
            f"6. Determine root cause\n"
            f"7. Provide fix recommendations (delegate code changes to code_assistant if needed)\n"
            f"8. Provide regression checklist\n"
            f"DO NOT skip diagnosis — use Skill tool to load `debug` first."
        )
    elif primary == "teach-plus":
        primary_instruction = (
            f"MANDATORY learning workflow — you MUST follow these steps:\n"
            f"1. Analyze user intent to choose teach-plus mode:\n"
            f"   - explain: user wants to understand (讲明白/梳理/入门/是什么)\n"
            f"   - practice: user wants daily tasks (今天学什么/练习/学习单/训练)\n"
            f"   - review: user wants retrospective (复盘/本周/回顾/总结学习)\n"
            f"2. Load summarize/briefing if available as learning context\n"
            f"3. Load planning/learning output if available as study plan\n"
            f"4. Produce output following the selected mode's protocol\n"
            f"5. For practice mode: write learning tasks to task_ledger\n"
            f"6. For review mode: read task_ledger learning records as input\n"
            f"DO NOT skip the learning chain — use Skill tool to load `teach-plus` first."
        )
    else:
        primary_instruction = f"请先用 Skill 工具加载 `{primary}`，再根据该技能的规范回答。"

    injection = (
        f"\n╔══ SKILL OS v3 ROUTER ═══════════════════╗\n"
        f"║  Intent:  {decision['intent']:<30}║\n"
        f"║  Workflow: {decision['workflow']:<29}║\n"
        f"║  Primary:  {primary:<30}║\n"
        f"║  Secondary: {sec_str:<29}║\n"
        f"╠══════════════════════════════════════════╣\n"
        f"║  Reason: {decision['reason'][:36]:<36}║\n"
        f"╠══════════════════════════════════════════╣\n"
        f"║  Scores:                                ║\n"
        f"{score_lines}\n"
        f"╚══════════════════════════════════════════╝\n\n"
        f"[指令] {primary_instruction}\n"
    )
else:
    # ── Fallback：单 Skill 模式注入（兼容旧版） ──
    if best_single == "planner":
        skill_instruction = (
            f"MANDATORY workflow — you MUST follow these steps:\n"
            f"1. Determine task type:\n"
            f"   - Code tasks (involving code, files, projects, config, deploy, API, DB) → call EnterPlanMode tool, explore codebase, write plan using planner templates, then ExitPlanMode\n"
            f"   - Non-code tasks (study plan, travel, architecture doc, business process) → output plan using planner templates directly, do NOT call EnterPlanMode\n"
            f"2. If unsure, ask the user to clarify before proceeding.\n"
            f"DO NOT skip this — you MUST use Skill tool to load `planner` first."
        )
    else:
        skill_instruction = f"请先用 Skill 工具加载 `{best_single}`，再根据该技能的规范回答。"

    injection = (
        f"\n╔══ SKILL ROUTER (v1.5 fallback) ════════╗\n"
        f"║  自动激活技能: {best_single:<26}║\n"
        f"╚══════════════════════════════════════════╝\n"
        f"路由得分:\n{score_lines}\n\n"
        f"[指令] {skill_instruction}\n"
    )

print(json.dumps({"prompt_injection": injection}))
sys.exit(0)

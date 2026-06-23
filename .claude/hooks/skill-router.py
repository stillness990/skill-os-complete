#!/usr/bin/env python3
"""
Claude Code Skill Router Hook — Skill OS v5
触发时机: 每次用户发送消息之前（UserPromptSubmit）
路由策略: v5 WorkflowResolver 优先 → v4 双路径 fallback → 静默 {}
升级:    从 v4 单路由升级为 v5 多源融合 + v4 兜底
"""

import json
import os
import sys

# ══════════════════════════════════════════════════════════════
# Path constants (absolute, no env-var dependency)
# ══════════════════════════════════════════════════════════════

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))          # .claude/hooks
CLAUDE_DIR = os.path.dirname(HOOK_DIR)                          # .claude
V5_ORCH_DIR = os.path.join(CLAUDE_DIR, "orchestration")         # v5 编排层（live）
V4_PROJECT_ROUTER = os.path.join(CLAUDE_DIR, "skill-os-complete", ".claude", "router")  # v4 项目版 fallback
V4_GLOBAL_ROUTER = os.path.join(CLAUDE_DIR, "router")           # v4 全局版 fallback

# ── Runtime path injection (v5 orchestration) ──
# 将 CLAUDE_DIR 注入 sys.path，确保 `from orchestration.xxx` 能正确解析。
# v5 编排模块已部署到 .claude/orchestration/，不再依赖 skill-os-complete。
_V5_ORCH_INITED = False
if os.path.isdir(V5_ORCH_DIR):
    if CLAUDE_DIR not in sys.path:
        sys.path.insert(0, CLAUDE_DIR)
    _V5_ORCH_INITED = True
    print(f"[skill-router] v5 orch injected: V5_ORCH_DIR={V5_ORCH_DIR}", file=sys.stderr)
else:
    print(f"[skill-router] WARNING: V5_ORCH_DIR not found: {V5_ORCH_DIR}, will use v4 fallback only", file=sys.stderr)

# ══════════════════════════════════════════════════════════════
# Workflow → Primary Skill (from workflow_templates.json)
# ══════════════════════════════════════════════════════════════

WORKFLOW_PRIMARY = {
    "delivery_pipeline": "planning",
    "debug_pipeline": "debug",
    "learning_pipeline": "teach-plus",
}

WORKFLOW_SECONDARY = {
    "delivery_pipeline": ["summarize", "code_assistant", "reviewer", "changelog", "knowledge-asset"],
    "debug_pipeline": ["summarize", "code_assistant", "knowledge-asset"],
    "learning_pipeline": ["summarize", "planning", "ask", "task_ledger"],
}

INTENT_CN = {
    "project_delivery": "项目交付",
    "debug_issue": "故障诊断",
    "learn_topic": "学习",
}

# ══════════════════════════════════════════════════════════════
# Primary Skill Instructions (Chinese, v4-compatible)
# ══════════════════════════════════════════════════════════════

def _primary_instruction(primary: str) -> str:
    """为 primary skill 生成 MANDATORY 指令."""
    if primary in ("planning", "planner"):
        return (
            "MANDATORY workflow — you MUST follow these steps:\n"
            "1. Determine task type:\n"
            "   - Code tasks (involving code, files, projects, config, deploy, API, DB) → call EnterPlanMode tool, "
            "explore codebase, write plan using planning templates, then ExitPlanMode\n"
            "   - Non-code tasks (study plan, travel, architecture doc, business process) → output plan using "
            "planning templates directly, do NOT call EnterPlanMode\n"
            "2. If unsure, ask the user to clarify before proceeding.\n"
            "DO NOT skip this — you MUST use Skill tool to load `planning` first."
        )
    elif primary == "debug":
        return (
            "MANDATORY diagnosis workflow — you MUST follow these steps:\n"
            "1. Confirm the problem phenomenon with the user (re-state in your own words)\n"
            "2. Identify impact scope and severity\n"
            "3. Provide minimal reproduction steps\n"
            "4. Propose 1-3 hypotheses (ranked by likelihood, with reasons)\n"
            "5. Design verification steps for each hypothesis\n"
            "6. Determine root cause\n"
            "7. Provide fix recommendations (delegate code changes to code_assistant if needed)\n"
            "8. Provide regression checklist\n"
            "DO NOT skip diagnosis — use Skill tool to load `debug` first."
        )
    elif primary == "teach-plus":
        return (
            "MANDATORY learning workflow — you MUST follow these steps:\n"
            "1. Analyze user intent to choose teach-plus mode:\n"
            "   - explain: user wants to understand (讲明白/梳理/入门/是什么)\n"
            "   - practice: user wants daily tasks (今天学什么/练习/学习单/训练)\n"
            "   - review: user wants retrospective (复盘/本周/回顾/总结学习)\n"
            "2. Load summarize/briefing if available as learning context\n"
            "3. Load planning/learning output if available as study plan\n"
            "4. Produce output following the selected mode's protocol\n"
            "5. For practice mode: write learning tasks to task_ledger\n"
            "6. For review mode: read task_ledger learning records as input\n"
            "DO NOT skip the learning chain — use Skill tool to load `teach-plus` first."
        )
    else:
        return f"请先用 Skill 工具加载 `{primary}`，再根据该技能的规范回答。"


# ══════════════════════════════════════════════════════════════
# v5 Route: WorkflowResolver
# ══════════════════════════════════════════════════════════════

def _try_v5_resolve(prompt: str):
    """
    尝试 v5 多源融合路由。
    成功返回 prompt_injection 字符串，失败返回 None。
    """
    try:
        from orchestration.workflow_resolver import WorkflowResolver

        resolver = WorkflowResolver()
        result = resolver.resolve(prompt)

        rp = result.route_plan
        wf_name = rp.workflow.value if hasattr(rp.workflow, 'value') else str(rp.workflow)
        intent_name = rp.intent.value if hasattr(rp.intent, 'value') else str(rp.intent)
        confidence = rp.confidence

        # 置信度过低不触发
        if confidence < 0.25:
            print(f"[skill-router] v5 resolve: confidence={confidence:.2f} < 0.25, skipping", file=sys.stderr)
            return None

        # 从 route_plan.stages 提取 primary / secondary
        primary = WORKFLOW_PRIMARY.get(wf_name)
        if not primary:
            # 从 stages 中取第一个 required stage 的 skill
            for stage in rp.stages:
                if stage.required:
                    primary = stage.skill
                    break
        if not primary:
            print(f"[skill-router] v5 resolve: no primary skill found for workflow={wf_name}", file=sys.stderr)
            return None

        secondary = WORKFLOW_SECONDARY.get(wf_name, [])
        sec_str = ", ".join(secondary) if secondary else "无"

        # 构建注入
        intent_cn = INTENT_CN.get(intent_name, intent_name)
        route_source = rp.route_source if rp.route_source else result.fusion_method
        fusion_label = f"SKILL OS v5 ROUTER ({route_source})"

        # Stages 展示
        stages_lines = ""
        for s in rp.stages[:6]:
            mark = "✓" if s.required else "○"
            stages_lines += f"║    {mark} {s.phase:<20} → {s.skill}\n"

        primary_instruction = _primary_instruction(primary)

        injection = (
            f"\n╔══ {fusion_label} ═══════════════════╗\n"
            f"║  Intent:  {intent_cn:<30}║\n"
            f"║  Workflow: {wf_name:<29}║\n"
            f"║  Primary:  {primary:<30}║\n"
            f"║  Secondary: {sec_str:<29}║\n"
            f"║  Confidence: {confidence:.2f}{' ' * 19}║\n"
            f"╠══════════════════════════════════════════╣\n"
            f"║  Stages:                                ║\n"
            f"{stages_lines}"
            f"╠══════════════════════════════════════════╣\n"
            f"║  Fusion: {result.fusion_method:<31}║\n"
            f"║  Rule srcs: {result.rule_candidates}  Semantic srcs: {result.semantic_candidates}{' ' * (14 - len(str(result.semantic_candidates)))}║\n"
            f"╚══════════════════════════════════════════╝\n"
            f"中文提示：已识别为{intent_cn}类任务，将进入 {wf_name} 工作流，优先执行 {primary}。\n\n"
            f"[指令] {primary_instruction}\n"
        )

        print(f"[skill-router] v5 resolve OK: workflow={wf_name} intent={intent_name} confidence={confidence:.2f} fusion={result.fusion_method}", file=sys.stderr)
        return injection

    except ImportError as e:
        # v5 模块不可用，静默 fallback
        print(f"[skill-router] v5 ImportError: {e}", file=sys.stderr)
        return None
    except Exception as e:
        # resolve 过程出错，静默 fallback
        print(f"[skill-router] v5 Exception: {type(e).__name__}: {e}", file=sys.stderr)
        return None


# ══════════════════════════════════════════════════════════════
# v4 Fallback: 双路径 routing_rules
# ══════════════════════════════════════════════════════════════

def _try_v4_fallback(prompt: str):
    """
    v4 fallback — 双路径尝试。
    1. 优先项目路径（含 build_router_decision_with_semantic，语义兜底）
    2. 其次全局路径（仅 build_router_decision，基础关键词路由）
    两个都失败返回 None。
    """
    import importlib.util

    # ── 候选路径列表 ──
    candidates = [
        ("project", V4_PROJECT_ROUTER),
        ("global", V4_GLOBAL_ROUTER),
    ]

    for label, router_dir in candidates:
        routing_path = os.path.join(router_dir, "routing_rules.py")
        if not os.path.isfile(routing_path):
            print(f"[skill-router] v4 fallback: {label} routing_rules.py not found at {routing_path}", file=sys.stderr)
            continue

        try:
            # 用 importlib 隔离加载，避免命名冲突
            spec = importlib.util.spec_from_file_location(
                f"routing_rules_{label}", routing_path
            )
            if spec is None or spec.loader is None:
                continue

            mod = importlib.util.module_from_spec(spec)

            # 把 router 目录加入 sys.path（该模块内部用 Path(__file__).parent 定位资源文件）
            if router_dir not in sys.path:
                sys.path.insert(0, router_dir)

            spec.loader.exec_module(mod)

            # 优先使用带语义兜底的版本
            if hasattr(mod, "build_router_decision_with_semantic"):
                decision = mod.build_router_decision_with_semantic(prompt)
            elif hasattr(mod, "build_router_decision"):
                decision = mod.build_router_decision(prompt)
            else:
                continue

            if not decision.get("has_hit"):
                print(f"[skill-router] v4 fallback: {label} has_hit=False", file=sys.stderr)
                continue

            # 构建 v4 注入（保持现有中文风格）
            print(f"[skill-router] v4 fallback OK: source={label} best={decision.get('best_single_skill', '?')}", file=sys.stderr)
            return _build_v4_injection(decision, label)

        except Exception as e:
            print(f"[skill-router] v4 fallback {label} error: {type(e).__name__}: {e}", file=sys.stderr)
            continue

    return None


def _build_v4_injection(decision: dict, source_label: str) -> str:
    """用 v4 决策结果构建 prompt_injection（保持现有风格）。"""
    best_single = decision.get("best_single_skill", "")
    scores = decision.get("scores", {})
    semantic_used = decision.get("semantic_used", False)

    # 得分展示
    score_lines = "\n".join(
        f"  {'→' if s == best_single else ' '} {s:<18} score={scores[s]}"
        for s, _ in sorted(scores.items(), key=lambda x: -x[1])
    )

    if decision.get("intent") and decision.get("workflow"):
        # Workflow 模式
        primary = decision.get("primary_skill", best_single)
        secondary = decision.get("secondary_skills", [])
        sec_str = ", ".join(secondary) if secondary else "无"

        route_label = (
            "SKILL OS v4 ROUTER (语义兜底)" if semantic_used
            else f"SKILL OS v4 ROUTER ({source_label})"
        )

        intent_cn = INTENT_CN.get(decision["intent"], decision["intent"])
        primary_instruction = _primary_instruction(primary)

        injection = (
            f"\n╔══ {route_label} ═══════════════════╗\n"
            f"║  Intent:  {intent_cn:<30}║\n"
            f"║  Workflow: {decision['workflow']:<29}║\n"
            f"║  Primary:  {primary:<30}║\n"
            f"║  Secondary: {sec_str:<29}║\n"
            f"║  Reason: {decision.get('reason', '')[:36]:<36}║\n"
            f"╠══════════════════════════════════════════╣\n"
            f"║  Scores:                                ║\n"
            f"{score_lines}\n"
            f"╚══════════════════════════════════════════╝\n"
            f"中文提示：已识别为{intent_cn}类任务，将进入 {decision['workflow']} 工作流，优先执行 {primary}。\n\n"
            f"[指令] {primary_instruction}\n"
        )
    else:
        # 单 Skill 模式
        route_label = (
            "SKILL ROUTER (语义兜底)" if semantic_used
            else f"SKILL ROUTER ({source_label})"
        )
        skill_instruction = _primary_instruction(best_single)

        injection = (
            f"\n╔══ {route_label} ════════╗\n"
            f"║  自动激活技能: {best_single:<26}║\n"
            f"╚══════════════════════════════════════════╝\n"
            f"路由得分:\n{score_lines}\n\n"
            f"[指令] {skill_instruction}\n"
        )

    return injection


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════

def main():
    # 1. 读取 Claude Code 传入的 prompt
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        sys.exit(0)

    prompt = data.get("prompt", "")
    if not prompt.strip():
        print(json.dumps({}))
        sys.exit(0)

    # 2. v5 优先
    injection = _try_v5_resolve(prompt)

    # 3. v4 fallback
    if injection is None:
        print(f"[skill-router] v5 returned None, attempting v4 fallback...", file=sys.stderr)
        injection = _try_v4_fallback(prompt)

    # 4. 输出
    if injection:
        print(json.dumps({"prompt_injection": injection}))
    else:
        print(f"[skill-router] FINAL: no route matched, output empty", file=sys.stderr)
        print(json.dumps({}))

    sys.exit(0)


if __name__ == "__main__":
    main()

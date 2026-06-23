"""
Skill OS v4 — Routing Rules Module

从 "关键词→技能" 升级为 "输入→intent→workflow→primary_skill / secondary_skills"
v4 新增: execution_guard 监督层引用
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional


ROUTER_DIR = Path(__file__).parent
PROJECT_DIR = ROUTER_DIR.parent


def load_skill_rules():
    """加载旧的 skill-rules.json（保留兼容）。"""
    rules_path = PROJECT_DIR / "skill-rules.json"
    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)["skills"]


def load_skill_index():
    """加载技能索引。"""
    index_path = ROUTER_DIR / "skill_index.json"
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)["skills"]


def load_workflow_templates():
    """加载 workflow 模板。"""
    wf_path = ROUTER_DIR / "workflow_templates.json"
    with open(wf_path, "r", encoding="utf-8") as f:
        return json.load(f)["workflows"]


def score_skills(prompt: str, rules: dict) -> dict:
    """
    对 prompt 做关键词+正则打分（兼容旧逻辑）。
    返回 {skill_name: score}
    """
    lower = prompt.lower()
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
    return scores


def detect_intent(prompt: str, scores: dict, rules: dict) -> Optional[str]:
    """
    从打分结果中检测 intent。

    优先级：
    1. debug_issue — debug 类关键词得分最高
    2. learn_topic — teach-plus 类关键词得分最高
    3. project_delivery — planning/planner 类关键词得分最高
    4. None — 无法判定，回退到单 skill 模式
    """
    # 检查是否有任何技能被命中（score > base priority）
    hits = {
        name: score
        for name, score in scores.items()
        if score > rules[name].get("priority", 0)
    }
    if not hits:
        return None

    # Intent 判定：看对应的技能得分
    debug_skills = {"debug"}
    learn_skills = {"teach-plus"}
    plan_skills = {"planner", "planning", "summarize", "task_manager", "task_ledger"}

    debug_score = scores.get("debug", 0)
    learn_score = scores.get("teach-plus", 0)
    # 用 max 而不是 sum，避免 planning 系 5 个技能总分碾压单个 teach-plus
    plan_score = max(scores.get(s, 0) for s in plan_skills)

    # 如果 debug 被命中且得分最高 → debug_issue
    if debug_score > max(learn_score, plan_score) and debug_score > rules["debug"].get("priority", 0):
        return "debug_issue"

    # 如果 teach-plus 被命中且得分 ≥ plan_score → learn_topic
    if learn_score >= plan_score and learn_score > rules["teach-plus"].get("priority", 0):
        return "learn_topic"

    # 如果 planning/planner 被命中 → project_delivery
    if plan_score > max(learn_score, debug_score) and plan_score > rules.get("planner", {}).get("priority", 0):
        return "project_delivery"


def select_workflow(intent: str, workflows: dict) -> Optional[dict]:
    """根据 intent 选择 workflow 模板。"""
    intent_to_wf = {
        "project_delivery": "delivery_pipeline",
        "debug_issue": "debug_pipeline",
        "learn_topic": "learning_pipeline",
    }
    wf_name = intent_to_wf.get(intent)
    if wf_name:
        return workflows.get(wf_name)
    return None


def build_router_decision(prompt: str) -> dict:
    """
    完整的路由决策流程。

    返回：
    {
        "intent": "project_delivery" | "debug_issue" | "learn_topic" | null,
        "workflow": "delivery_pipeline" | ... | null,
        "primary_skill": "planning" | ... | null,
        "secondary_skills": [...],
        "reason": "...",
        "scores": {...},
        "best_single_skill": "xxx"  # 兼容旧逻辑
    }
    """
    rules = load_skill_rules()
    workflows = load_workflow_templates()
    skill_index = load_skill_index()

    scores = score_skills(prompt, rules)
    best_single = max(scores, key=scores.get)
    base_only = rules[best_single].get("priority", 0)
    has_hit = scores[best_single] > base_only

    result = {
        "intent": None,
        "workflow": None,
        "primary_skill": None,
        "secondary_skills": [],
        "reason": "",
        "scores": scores,
        "best_single_skill": best_single if has_hit else None,
        "has_hit": has_hit,
    }

    if not has_hit:
        result["reason"] = "No skill match — fallback to normal conversation"
        return result

    # 尝试检测 intent
    intent = detect_intent(prompt, scores, rules)
    if intent:
        result["intent"] = intent
        wf = select_workflow(intent, workflows)
        if wf:
            result["workflow"] = wf["name"]
            result["primary_skill"] = wf["primary_skill"]
            result["secondary_skills"] = wf.get("secondary_skills", [])
            result["reason"] = f"Intent detected: {intent} → workflow: {wf['name']} → primary: {wf['primary_skill']}"
        else:
            result["primary_skill"] = best_single
            result["reason"] = f"Intent {intent} detected but no workflow found, fallback to best skill: {best_single}"
    else:
        # 无法判定 intent → 回退到单 skill 模式
        result["primary_skill"] = best_single
        result["reason"] = f"Intent unclear, fallback to single-skill mode: {best_single}"

    return result


# ── Semantic fallback ──────────────────────────────────────
# 语义路由兜底：当关键词匹配无命中时，用 embedding 相似度检索候选 workflow。
# 依赖 routing_assets/semantic_router.py → Ollama nomic-embed-text。
# embedding 不可用时静默降级，不崩溃。

SEMANTIC_THRESHOLD = 0.75     # 语义置信度阈值，低于此值不触发
SEMANTIC_GAP_THRESHOLD = 0.08  # 最佳与次佳候选间距，低于此值视为歧义输入，不触发


def build_router_decision_with_semantic(prompt: str) -> dict:
    """
    增强版路由决策：关键词规则优先 → 无命中时语义兜底。

    双重过滤：
    1. 最佳候选 confidence >= SEMANTIC_THRESHOLD
    2. 最佳与次佳 confidence 差距 >= SEMANTIC_GAP_THRESHOLD
       （避免「今天天气怎么样」这种三个 workflow 挤在一起的歧义输入）

    与 build_router_decision 返回格式完全一致，
    额外增加 semantic_used / semantic_candidates 字段用于诊断。
    """
    # Step 1: 关键词规则匹配（现有逻辑）
    decision = build_router_decision(prompt)

    if decision["has_hit"]:
        decision["semantic_used"] = False
        return decision

    # Step 2: 语义兜底
    try:
        _routing_assets = PROJECT_DIR.parent / "routing_assets"
        if str(_routing_assets) not in sys.path:
            sys.path.insert(0, str(_routing_assets))

        from semantic_router import get_semantic_router  # type: ignore[import-not-found]

        sr = get_semantic_router()
        candidates, health = sr.get_candidates(prompt, top_k=3)

        # 语义不可用 → 保持原结果
        if health.degraded or not candidates:
            decision["reason"] = (
                f"No rule hit + semantic unavailable"
                + (f": {health.error}" if health.error else "")
            )
            decision["semantic_used"] = False
            return decision

        best = candidates[0]

        # 过滤 1：置信度检查
        if best.confidence < SEMANTIC_THRESHOLD:
            decision["reason"] = (
                f"No rule hit + semantic confidence too low "
                f"({best.confidence:.2f} < {SEMANTIC_THRESHOLD})"
            )
            decision["semantic_used"] = False
            decision["semantic_candidates"] = [c.to_dict() for c in candidates]
            return decision

        # 过滤 2：候选间距检查（防止歧义输入）
        if len(candidates) >= 2:
            gap = best.confidence - candidates[1].confidence
            if gap < SEMANTIC_GAP_THRESHOLD:
                decision["reason"] = (
                    f"No rule hit + semantic gap too small "
                    f"({gap:.3f} < {SEMANTIC_GAP_THRESHOLD}, "
                    f"best={best.workflow} vs 2nd={candidates[1].workflow})"
                )
                decision["semantic_used"] = False
                decision["semantic_candidates"] = [c.to_dict() for c in candidates]
                return decision

        # 映射 workflow → 决策字段
        wf_name = best.workflow
        workflows = load_workflow_templates()
        wf = workflows.get(wf_name)

        if not wf:
            decision["reason"] = (
                f"Semantic hit '{wf_name}' but workflow template not found"
            )
            decision["semantic_used"] = False
            return decision

        intent = wf.get("intent")
        primary = wf.get("primary_skill")
        secondary = wf.get("secondary_skills", [])

        # 更新 scores 以反映语义结果（用于注入展示）
        semantic_score = int(best.confidence * 10)
        decision["scores"]["semantic"] = semantic_score

        decision.update({
            "intent": intent,
            "workflow": wf_name,
            "primary_skill": primary,
            "secondary_skills": secondary,
            "best_single_skill": primary,
            "has_hit": True,
            "reason": (
                f"Semantic fallback: {wf_name} "
                f"(confidence={best.confidence:.2f}, sim={best.similarity_score:.3f}, "
                f"gap={gap:.3f})"
            ),
            "semantic_used": True,
            "semantic_candidates": [c.to_dict() for c in candidates],
        })
        return decision

    except ImportError as e:
        decision["reason"] = f"No rule hit + semantic import error: {e}"
        decision["semantic_used"] = False
        return decision
    except Exception as e:
        decision["reason"] = f"No rule hit + semantic error: {e}"
        decision["semantic_used"] = False
        return decision

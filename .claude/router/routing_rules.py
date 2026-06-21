"""
Skill OS v4 — Routing Rules Module

从 "关键词→技能" 升级为 "输入→intent→workflow→primary_skill / secondary_skills"
v4 新增: execution_guard 监督层引用
"""

import json
import os
import re
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

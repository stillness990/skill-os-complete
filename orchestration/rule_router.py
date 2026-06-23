"""
Rule Router — 规则路由引擎
Phase 3: 基于关键词+规则模式的路由，不依赖 embedding

职责：
- 接收 NormalizedInput + routing_assets (workflow_cards, skill_cards, route_examples)
- 用纯规则匹配输出 RoutePlan (Phase 2 的数据结构)
- 不依赖 embedding，不使用语义检索
- 返回 RoutePlan 候选列表（含置信度），供 workflow-resolver (Phase 4) 融合

不做：
- 不依赖 embedding
- 不做最终决策融合（resolver 的事）
- 不做执行（skill-router 的事）
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Phase 2 依赖
from .orchestration_types import Intent, Workflow, RouteSource
from .route_plan import RoutePlan, RouteStage, GuardPolicy, create_route_plan_from_template
from .prompt_normalizer import NormalizedInput

# ── 默认资源路径 ──
# rule_router 在 orchestration/ 中，asset 文件在 routing_assets/ 中

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "routing_assets"
_DEFAULT_WORKFLOW_CARDS = _ASSETS_DIR / "workflow_cards.json"
_DEFAULT_SKILL_CARDS = _ASSETS_DIR / "skill_cards.json"


# ── RuleMatch ─────────────────────────────────────────

@dataclass
class RuleMatch:
    """单次规则匹配结果"""
    workflow: Workflow
    intent: Intent
    confidence: float
    matched_keywords: list[str] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)
    source: RouteSource = RouteSource.RULE
    reasoning: str = ""


# ── RuleRouter ────────────────────────────────────────

class RuleRouter:
    """
    规则路由引擎。

    用法:
        router = RuleRouter()
        result = router.route(normalized_input)
        # result -> RoutePlan
    """

    def __init__(
        self,
        workflow_cards_path: Optional[Path] = None,
        skill_cards_path: Optional[Path] = None,
    ):
        self._wf_path = workflow_cards_path or _DEFAULT_WORKFLOW_CARDS
        self._sk_path = skill_cards_path or _DEFAULT_SKILL_CARDS
        self._workflow_cards = self._load_json(self._wf_path)
        self._skill_cards = self._load_json(self._sk_path)
        self._compiled_workflow_patterns = self._compile_workflow_patterns()

    @staticmethod
    def _load_json(path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _compile_workflow_patterns(self) -> list[tuple[str, list[re.Pattern]]]:
        """预编译所有 workflow 的触发正则"""
        compiled = []
        for wf in self._workflow_cards.get("workflows", []):
            patterns = []
            for p in wf.get("trigger_patterns", []):
                try:
                    patterns.append(re.compile(p, re.IGNORECASE))
                except re.error:
                    pass
            compiled.append((wf["name"], patterns))
        return compiled

    # ── 主路由入口 ──

    def route(self, normalized: NormalizedInput) -> RoutePlan:
        """
        对标准化输入执行规则路由，返回 RoutePlan。

        Fallback: 如果无法匹配任何 workflow，返回 unknown intent 的 fallback plan。
        """
        # Step 1: 尝试精确匹配 /command
        route_plan = self._try_slash_route(normalized)
        if route_plan:
            return route_plan

        # Step 2: 关键词+正则匹配 workflow
        matches = self._match_workflows(normalized)

        # Step 3: 选最佳匹配
        if matches:
            best = matches[0]
            return self._build_route_plan(best, normalized)

        # Step 4: 用 normalized primary_intent_hint 兜底
        if normalized.primary_intent_hint and normalized.primary_intent_hint != "unknown":
            return self._build_fallback_plan(normalized)

        # Step 5: 完全无法匹配 → unknown fallback
        return self._build_unknown_plan(normalized)

    # ── Slash command 路由 ──

    def _try_slash_route(self, normalized: NormalizedInput) -> Optional[RoutePlan]:
        """处理 /plan /debug /task /next 等 slash commands"""
        if not normalized.slash_commands:
            return None

        for cmd in normalized.slash_commands:
            if cmd == "/plan":
                return create_route_plan_from_template(
                    workflow=Workflow.DELIVERY,
                    intent=Intent.PROJECT_DELIVERY,
                    confidence=0.95,
                    normalized_input=normalized.normalized,
                    route_source="rule",
                )
            elif cmd == "/debug":
                return create_route_plan_from_template(
                    workflow=Workflow.DEBUG,
                    intent=Intent.DEBUG_ISSUE,
                    confidence=0.95,
                    normalized_input=normalized.normalized,
                    route_source="rule",
                )
            elif cmd in ("/task", "/next"):
                # /task 和 /next → 查 task_ledger，但路由走 delivery
                plan = create_route_plan_from_template(
                    workflow=Workflow.DELIVERY,
                    intent=Intent.PROJECT_DELIVERY,
                    confidence=0.85,
                    normalized_input=normalized.normalized,
                    route_source="rule",
                )
                # 只保留 track 阶段
                plan.stages = [s for s in plan.stages if s.skill == "task_ledger"]
                if not plan.stages:
                    # 如果模板里没 task_ledger stage，加一个
                    plan.stages = [
                        RouteStage(
                            stage_id="stg_000_track",
                            phase="track",
                            skill="task_ledger",
                            mode="auto",
                            required=True,
                            expected_output="任务状态",
                        )
                    ]
                return plan
            elif cmd == "/learn":
                return create_route_plan_from_template(
                    workflow=Workflow.LEARNING,
                    intent=Intent.LEARN_TOPIC,
                    confidence=0.95,
                    normalized_input=normalized.normalized,
                    route_source="rule",
                )
        return None

    # ── Workflow 匹配 ──

    def _match_workflows(self, normalized: NormalizedInput) -> list[RuleMatch]:
        """关键词+正则匹配所有 workflow，返回排序后的匹配列表"""
        matches = []
        text = normalized.normalized
        text_lower = text.lower()

        for wf in self._workflow_cards.get("workflows", []):
            score = 0
            matched_kw = []
            matched_pt = []

            # 中文关键词匹配
            for kw in wf.get("trigger_keywords", {}).get("zh", []):
                if kw in text:
                    score += 2
                    matched_kw.append(f"zh:{kw}")

            # 英文关键词匹配
            for kw in wf.get("trigger_keywords", {}).get("en", []):
                if kw.lower() in text_lower:
                    score += 2
                    matched_kw.append(f"en:{kw}")

            # 正则匹配
            for wf_name, patterns in self._compiled_workflow_patterns:
                if wf_name == wf["name"]:
                    for p in patterns:
                        if p.search(text):
                            score += 3
                            matched_pt.append(p.pattern)

            # 负向关键词扣分
            for nkw in wf.get("negative_keywords", []):
                if nkw in text:
                    score -= 4

            if score > 0:
                # 基础分 + priority 权重
                priority = wf.get("priority", 5)
                adjusted_score = score + (6 - priority)  # priority 1 → +5, priority 3 → +3

                # 归一化置信度
                confidence = min(adjusted_score / 15.0, 1.0)

                try:
                    workflow = Workflow(wf["name"])
                    intent = Intent(wf["intent"])
                except ValueError:
                    continue

                matches.append(RuleMatch(
                    workflow=workflow,
                    intent=intent,
                    confidence=confidence,
                    matched_keywords=matched_kw,
                    matched_patterns=matched_pt,
                    reasoning=f"keyword_score={score}, priority={priority}",
                ))

        # 按置信度降序
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches

    # ── RoutePlan 构建 ──

    def _build_route_plan(self, match: RuleMatch, normalized: NormalizedInput) -> RoutePlan:
        """从 RuleMatch 构建 RoutePlan"""
        plan = create_route_plan_from_template(
            workflow=match.workflow,
            intent=match.intent,
            confidence=match.confidence,
            normalized_input=normalized.normalized,
            route_source="rule",
        )
        return plan

    def _build_fallback_plan(self, normalized: NormalizedInput) -> RoutePlan:
        """根据 primary_intent_hint 构建 fallback plan"""
        try:
            intent = Intent(normalized.primary_intent_hint)
        except ValueError:
            return self._build_unknown_plan(normalized)

        # intent → workflow
        if intent == Intent.PROJECT_DELIVERY:
            wf = Workflow.DELIVERY
        elif intent == Intent.DEBUG_ISSUE:
            wf = Workflow.DEBUG
        elif intent == Intent.LEARN_TOPIC:
            wf = Workflow.LEARNING
        else:
            return self._build_unknown_plan(normalized)

        return create_route_plan_from_template(
            workflow=wf,
            intent=intent,
            confidence=0.5,
            normalized_input=normalized.normalized,
            route_source="rule",
        )

    def _build_unknown_plan(self, normalized: NormalizedInput) -> RoutePlan:
        """构建 unknown/fallback RoutePlan"""
        return RoutePlan(
            route_id="",
            workflow=Workflow.DELIVERY,
            intent=Intent.UNKNOWN,
            confidence=0.0,
            normalized_input=normalized.normalized,
            route_source="fallback",
            stages=[],
        )

    # ── 候选列表（供 Phase 4 resolver 使用）──

    def get_candidates(self, normalized: NormalizedInput) -> list[RuleMatch]:
        """返回所有候选匹配（不选最佳），供 resolver 融合"""
        return self._match_workflows(normalized)


# ── Singleton ─────────────────────────────────────────

_router_instance: Optional[RuleRouter] = None


def get_rule_router() -> RuleRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = RuleRouter()
    return _router_instance

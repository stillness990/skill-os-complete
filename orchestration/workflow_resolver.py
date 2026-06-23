"""
Workflow Resolver — 多源融合决策器
Phase 4: 融合 normalized input + rule candidates + semantic candidates + safe_mode → 唯一 RoutePlan

职责：
- 融合多种路由源（rule + semantic + fallback）
- 考虑 safe_mode 状态
- 输出唯一的、合法的 RoutePlan
- 不做执行（那是 skill-router 的事）

融合规则：
1. safe_mode active → 只用 rule candidates，semantic 被禁用
2. semantic available → rule + semantic 加权融合
3. semantic degraded → 只用 rule candidates
4. 无任何候选 → fallback RoutePlan (unknown intent)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Phase 2 types
from .orchestration_types import (
    Intent,
    Workflow,
    ExecutionStatus,
    SafeModeStatus,
    RouteSource,
)
from .route_plan import RoutePlan, RouteStage, GuardPolicy, create_route_plan_from_template
from .workflow_state import WorkflowState

# Phase 3 modules
from .prompt_normalizer import NormalizedInput, PromptNormalizer
from .rule_router import RuleRouter, RuleMatch

# Phase 4
from .semantic_router import SemanticRouter, SemanticCandidate, EmbeddingHealth


# ── Resolver Result ───────────────────────────────────

@dataclass
class ResolverResult:
    """resolver 融合决策结果"""
    route_plan: RoutePlan
    state: WorkflowState
    # 诊断信息
    rule_candidates: int = 0
    semantic_candidates: int = 0
    semantic_available: bool = False
    safe_mode_active: bool = False
    fusion_method: str = "unknown"  # "rule_only" | "semantic_only" | "fusion" | "fallback"

    def to_dict(self) -> dict:
        return {
            "route_plan": self.route_plan.to_dict(),
            "state": self.state.to_dict(),
            "rule_candidates": self.rule_candidates,
            "semantic_candidates": self.semantic_candidates,
            "semantic_available": self.semantic_available,
            "safe_mode_active": self.safe_mode_active,
            "fusion_method": self.fusion_method,
        }


# ── Workflow Resolver ─────────────────────────────────

class WorkflowResolver:
    """
    多源融合决策器。

    用法:
        resolver = WorkflowResolver()
        result = resolver.resolve("读取项目并评估功能，再给升级方案")
        # result.route_plan → RoutePlan for delivery_pipeline
    """

    def __init__(
        self,
        normalizer: Optional[PromptNormalizer] = None,
        rule_router: Optional[RuleRouter] = None,
        semantic_router: Optional[SemanticRouter] = None,
        state: Optional[WorkflowState] = None,
    ):
        self._normalizer = normalizer or PromptNormalizer()
        self._rule_router = rule_router or RuleRouter()
        self._semantic_router = semantic_router or SemanticRouter()
        self._state = state or WorkflowState()

    # ── 主入口 ──

    def resolve(self, raw_input: str) -> ResolverResult:
        """
        对用户输入执行完整融合决策，返回唯一 RoutePlan。

        Args:
            raw_input: 原始用户输入

        Returns:
            ResolverResult with RoutePlan + diagnostic info
        """
        # Step 1: Normalize
        normalized = self._normalizer.normalize(raw_input)

        # Step 2: Check SAFE MODE
        safe_mode_active = self._state.is_in_safe_mode

        # Step 3: Get rule candidates
        rule_candidates = self._rule_router.get_candidates(normalized)

        # Step 4: Get semantic candidates (if available and not safe mode)
        semantic_candidates: list[SemanticCandidate] = []
        semantic_available = False
        semantic_health: Optional[EmbeddingHealth] = None

        if not safe_mode_active:
            semantic_candidates, semantic_health = self._semantic_router.get_candidates(
                normalized.normalized
            )
            semantic_available = (
                semantic_health is not None
                and semantic_health.available
                and len(semantic_candidates) > 0
            )
        else:
            # SAFE MODE: semantic-router 被禁用
            semantic_available = False

        # Step 5: Fusion → unique RoutePlan
        if safe_mode_active:
            # SAFE MODE: 仅用 rule candidates
            route_plan = self._fuse_rule_only(normalized, rule_candidates)
            fusion_method = "rule_only_safe_mode"
        elif semantic_available:
            # 正常模式: rule + semantic 融合
            route_plan = self._fuse_combined(
                normalized, rule_candidates, semantic_candidates
            )
            fusion_method = "fusion"
        elif semantic_health and semantic_health.degraded:
            # Semantic degraded: rule only
            route_plan = self._fuse_rule_only(normalized, rule_candidates)
            fusion_method = "rule_only_degraded"
        else:
            # Semantic unavailable: rule only
            route_plan = self._fuse_rule_only(normalized, rule_candidates)
            fusion_method = "rule_only"

        # Step 6: Update state
        self._state.start_route(route_plan.route_id, route_plan.workflow)
        if safe_mode_active:
            self._state.mark_degraded("SAFE MODE active — semantic disabled")
        elif not semantic_available:
            self._state.mark_degraded("Semantic router unavailable")

        return ResolverResult(
            route_plan=route_plan,
            state=self._state,
            rule_candidates=len(rule_candidates),
            semantic_candidates=len(semantic_candidates),
            semantic_available=semantic_available,
            safe_mode_active=safe_mode_active,
            fusion_method=fusion_method,
        )

    # ── Fusion strategies ─────────────────────────────

    def _fuse_rule_only(
        self,
        normalized: NormalizedInput,
        rule_candidates: list[RuleMatch],
    ) -> RoutePlan:
        """仅用 rule candidates"""
        if rule_candidates:
            best = rule_candidates[0]
            return create_route_plan_from_template(
                workflow=best.workflow,
                intent=best.intent,
                confidence=best.confidence * 0.9,  # 略降置信度（无 semantic 验证）
                normalized_input=normalized.normalized,
                route_source="rule",
            )
        # Fallback: 用 normalized hint
        return self._build_fallback_plan(normalized)

    def _fuse_combined(
        self,
        normalized: NormalizedInput,
        rule_candidates: list[RuleMatch],
        semantic_candidates: list[SemanticCandidate],
    ) -> RoutePlan:
        """
        Rule + Semantic 加权融合。

        算法:
        1. 计算每个 workflow 的组合分数
           score = rule_weight * rule_score + semantic_weight * semantic_score
        2. 选最高分 workflow
        3. 置信度 = max(rule_best.confidence, semantic_best.confidence)
        """
        RULE_WEIGHT = 0.6
        SEMANTIC_WEIGHT = 0.4

        # Build scores per workflow
        scores: dict[str, float] = {}
        sources: dict[str, list[str]] = {}

        # Rule scores (normalized to 0~1)
        for rm in rule_candidates:
            wf = rm.workflow.value
            scores[wf] = scores.get(wf, 0) + rm.confidence * RULE_WEIGHT
            sources.setdefault(wf, []).append("rule")

        # Semantic scores
        for sc in semantic_candidates:
            wf = sc.workflow
            scores[wf] = scores.get(wf, 0) + sc.confidence * SEMANTIC_WEIGHT
            sources.setdefault(wf, []).append("semantic")

        if not scores:
            return self._build_fallback_plan(normalized)

        # Best workflow
        best_wf = max(scores, key=scores.get)
        confidence = min(scores[best_wf], 1.0)

        try:
            workflow = Workflow(best_wf)
        except ValueError:
            return self._build_fallback_plan(normalized)

        # Intent from workflow
        intent = Intent.PROJECT_DELIVERY
        if workflow == Workflow.DEBUG:
            intent = Intent.DEBUG_ISSUE
        elif workflow == Workflow.LEARNING:
            intent = Intent.LEARN_TOPIC

        route_source = "+".join(sources.get(best_wf, ["rule"]))

        plan = create_route_plan_from_template(
            workflow=workflow,
            intent=intent,
            confidence=confidence,
            normalized_input=normalized.normalized,
            route_source=route_source,
        )

        # 如果 semantic 高度确定且 rule 不确定，提升 confidence
        sc_best = next((sc for sc in semantic_candidates if sc.workflow == best_wf), None)
        if sc_best and sc_best.similarity_score > 0.7 and confidence < 0.8:
            plan.confidence = min(confidence + 0.1, 1.0)

        return plan

    def _build_fallback_plan(self, normalized: NormalizedInput) -> RoutePlan:
        """构建 fallback RoutePlan"""
        if normalized.primary_intent_hint and normalized.primary_intent_hint != "unknown":
            try:
                intent = Intent(normalized.primary_intent_hint)
            except ValueError:
                intent = Intent.UNKNOWN
            wf = Workflow.DELIVERY
            if intent == Intent.DEBUG_ISSUE:
                wf = Workflow.DEBUG
            elif intent == Intent.LEARN_TOPIC:
                wf = Workflow.LEARNING
            return create_route_plan_from_template(
                workflow=wf,
                intent=intent,
                confidence=0.3,
                normalized_input=normalized.normalized,
                route_source="fallback",
            )

        return RoutePlan(
            route_id="",
            workflow=Workflow.DELIVERY,
            intent=Intent.UNKNOWN,
            confidence=0.0,
            normalized_input=normalized.normalized,
            route_source="fallback",
            stages=[],
        )

    # ── SAFE MODE integration ─────────────────────────

    def set_safe_mode(self, active: bool, reason: str = "") -> None:
        """切换 SAFE MODE"""
        if active:
            self._state.enter_safe_mode(reason)
        else:
            self._state.exit_safe_mode()

    @property
    def is_safe_mode(self) -> bool:
        return self._state.is_in_safe_mode

    @property
    def state(self) -> WorkflowState:
        return self._state


# ── Singleton ─────────────────────────────────────────

_resolver_instance: Optional[WorkflowResolver] = None


def get_workflow_resolver() -> WorkflowResolver:
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = WorkflowResolver()
    return _resolver_instance

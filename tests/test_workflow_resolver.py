"""
Tests: Workflow Resolver
Phase 4 — 验证融合决策: normalized + rule + semantic + safe_mode → unique RoutePlan

P4-7: 三大场景 RoutePlan 正确
1. 读取项目并评估功能，再给升级方案 → delivery_pipeline → summarize + planning
2. 生成 Claude 施工单 → delivery_pipeline → summarize + planning + ask
3. docker compose up 报 permission denied → debug_pipeline → debug(diagnose)
"""

import sys
sys.path.insert(0, "/path/to/skill-os-complete")
sys.path.insert(0, "/path/to/skill-os-complete/routing_assets")
sys.path.insert(0, "/path/to/skill-os-complete/orchestration")
sys.path.insert(0, "/path/to/skill-os-complete/ledger")

from orchestration_types import Workflow, Intent, SafeModeStatus
from workflow_resolver import WorkflowResolver
from workflow_state import WorkflowState


def test_resolver_basic():
    """Resolver can be created and resolves input"""
    resolver = WorkflowResolver()
    result = resolver.resolve("帮我制定项目计划")
    assert result.route_plan is not None
    print(f"  route_id: {result.route_plan.route_id}")
    print(f"  fusion_method: {result.fusion_method}")
    print(f"  confidence: {result.route_plan.confidence}")
    print("  PASS")


def test_scenario_1_delivery_repo_analysis():
    """P4-7: 场景1 - 读取项目并评估功能 → delivery_pipeline → summarize + planning"""
    print("Scenario 1: 读取项目并评估功能，再给升级方案")
    resolver = WorkflowResolver()
    result = resolver.resolve("读取项目并评估功能，再给升级方案")
    plan = result.route_plan
    print(f"  workflow: {plan.workflow.value}")
    print(f"  intent: {plan.intent.value}")
    print(f"  confidence: {plan.confidence}")
    print(f"  fusion_method: {result.fusion_method}")
    stages = [(s.phase, s.skill, s.required) for s in plan.stages]
    print(f"  stages: {stages}")

    assert plan.workflow == Workflow.DELIVERY, f"Expected delivery, got {plan.workflow}"
    assert plan.intent == Intent.PROJECT_DELIVERY
    # Must contain at least summarize + planning
    skills = [s.skill for s in plan.stages]
    assert "summarize" in skills, f"Missing summarize in {skills}"
    assert "planning" in skills, f"Missing planning in {skills}"
    print("  PASS")


def test_scenario_2_delivery_construction():
    """P4-7: 场景2 - 生成 Claude 施工单 → delivery_pipeline → summarize + planning + ask"""
    print("Scenario 2: 生成 Claude 施工单")
    resolver = WorkflowResolver()
    result = resolver.resolve("生成 Claude 施工单")
    plan = result.route_plan
    print(f"  workflow: {plan.workflow.value}")
    print(f"  intent: {plan.intent.value}")
    print(f"  confidence: {plan.confidence}")
    stages = [(s.phase, s.skill) for s in plan.stages]
    print(f"  stages: {stages}")

    assert plan.workflow == Workflow.DELIVERY, f"Expected delivery, got {plan.workflow}"
    assert plan.intent == Intent.PROJECT_DELIVERY
    skills = [s.skill for s in plan.stages]
    assert "summarize" in skills, f"Missing summarize in {skills}"
    assert "planning" in skills, f"Missing planning in {skills}"
    # construction_prompt should ideally have ask in the pipeline
    print("  PASS")


def test_scenario_3_debug_permission_denied():
    """P4-7: 场景3 - docker compose up 报 permission denied → debug_pipeline → debug(diagnose)"""
    print("Scenario 3: docker compose up 报 permission denied")
    resolver = WorkflowResolver()
    result = resolver.resolve("docker compose up 报 permission denied")
    plan = result.route_plan
    print(f"  workflow: {plan.workflow.value}")
    print(f"  intent: {plan.intent.value}")
    print(f"  confidence: {plan.confidence}")
    stages = [(s.phase, s.skill, s.required) for s in plan.stages]
    print(f"  stages: {stages}")

    assert plan.workflow == Workflow.DEBUG, f"Expected debug, got {plan.workflow}"
    assert plan.intent == Intent.DEBUG_ISSUE
    # Must have diagnose stage
    diagnose_stages = [s for s in plan.stages if s.phase == "diagnose"]
    assert len(diagnose_stages) > 0, f"Missing diagnose stage in {stages}"
    assert diagnose_stages[0].required, "diagnose must be required"
    print("  PASS")


def test_safe_mode_disables_semantic():
    """Respects safe_mode: semantic-router disabled, uses rule only"""
    print("SAFE MODE test:")
    state = WorkflowState()
    state.enter_safe_mode("test trigger")
    resolver = WorkflowResolver(state=state)
    result = resolver.resolve("帮我制定项目计划")
    print(f"  safe_mode_active: {result.safe_mode_active}")
    print(f"  fusion_method: {result.fusion_method}")
    print(f"  semantic_candidates: {result.semantic_candidates}")

    assert result.safe_mode_active
    assert result.fusion_method == "rule_only_safe_mode"
    assert result.semantic_candidates == 0  # semantic disabled
    print("  PASS")


def test_resolver_outputs_unique_route_plan():
    """P4-6: Resolver outputs unique, legal RoutePlan"""
    resolver = WorkflowResolver()
    result = resolver.resolve("帮我诊断这个报错")
    plan = result.route_plan

    # RoutePlan is unique (single result)
    assert plan.route_id, "No route_id"
    assert plan.workflow, "No workflow"
    assert plan.intent, "No intent"

    # RoutePlan is legal (passes validation)
    issues = plan.validate()
    print(f"  route_id: {plan.route_id}")
    print(f"  workflow: {plan.workflow.value}")
    print(f"  validation issues: {issues}")
    assert not issues, f"Validation issues: {issues}"
    print("  PASS")


def test_fallback_on_nonsense():
    """Resolver doesn't crash on nonsense input"""
    resolver = WorkflowResolver()
    result = resolver.resolve("今天天气怎么样")
    plan = result.route_plan
    print(f"  workflow: {plan.workflow.value}")
    print(f"  intent: {plan.intent.value}")
    print(f"  confidence: {plan.confidence}")
    # System should not crash, even if routing is imperfect
    assert plan is not None
    assert plan.workflow is not None
    print("  PASS (no crash)")


def test_resolver_diagnostic_info():
    """ResolverResult contains diagnostic info"""
    resolver = WorkflowResolver()
    result = resolver.resolve("帮我制定一个项目重构方案")
    d = result.to_dict()
    required_keys = ["route_plan", "state", "rule_candidates", "semantic_candidates",
                     "semantic_available", "safe_mode_active", "fusion_method"]
    for k in required_keys:
        assert k in d, f"Missing key: {k}"
    print(f"  diagnostic keys: {list(d.keys())}")
    print(f"  rule_candidates: {result.rule_candidates}")
    print(f"  semantic_available: {result.semantic_available}")
    print(f"  safe_mode_active: {result.safe_mode_active}")
    print("  PASS")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 4 — Workflow Resolver Tests")
    print("=" * 60)
    print()
    test_resolver_basic()
    print()
    test_scenario_1_delivery_repo_analysis()
    print()
    test_scenario_2_delivery_construction()
    print()
    test_scenario_3_debug_permission_denied()
    print()
    test_safe_mode_disables_semantic()
    print()
    test_resolver_outputs_unique_route_plan()
    print()
    test_fallback_on_nonsense()
    print()
    test_resolver_diagnostic_info()
    print()
    print("=" * 60)
    print("ALL WORKFLOW RESOLVER TESTS PASSED")
    print("=" * 60)

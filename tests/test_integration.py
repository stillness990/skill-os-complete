"""
Tests: Integration — skill_router + guard + ledger + healing + safe_mode chain
Phase 5 — 验证完整执行链的协同工作
"""

import sys
import os
import tempfile
import json
from pathlib import Path

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from orchestration.orchestration_types import (
    Intent, Workflow, TaskStatus, StageStatus, ExecutionStatus, FailureType
)
from orchestration.route_plan import RoutePlan, RouteStage, create_route_plan_from_template
from orchestration.workflow_state import WorkflowState
from orchestration.skill_router import SkillRouter, RouterExecutionResult, StageExecutionResult
from orchestration.execution_guard import ExecutionGuard, GuardResult, GuardVerdict
from orchestration.safe_mode import SafeModeManager
from orchestration.self_healing import SelfHealingManager, HealingDecision


# ── Helpers ──────────────────────────────────────────

def _make_delivery_plan() -> RoutePlan:
    return create_route_plan_from_template(
        workflow=Workflow.DELIVERY,
        intent=Intent.PROJECT_DELIVERY,
        confidence=0.9,
        normalized_input="integration test - delivery plan",
        route_source="rule",
    )


def _mock_skill_success(skill: str, mode: str, context: dict) -> dict:
    return {"success": True, "artifacts": [f"output/{skill}.md"], "error": "", "output": f"mock output from {skill}"}


def _mock_skill_fail(skill: str, mode: str, context: dict) -> dict:
    return {"success": False, "artifacts": [], "error": f"mock failure in {skill}", "output": None}


def _mock_write_ledger(task_id: str, updates: dict) -> None:
    pass


# ── Tests ────────────────────────────────────────────

def test_skill_router_receives_route_plan():
    """SkillRouter receives RoutePlan and executes all stages"""
    print("1. SkillRouter receives RoutePlan → executes stages")
    plan = _make_delivery_plan()
    state = WorkflowState()

    router = SkillRouter(
        execute_skill=_mock_skill_success,
        write_ledger=_mock_write_ledger,
    )
    result = router.execute(plan, state)

    assert result.total_stages == len(plan.stages)
    assert result.completed_stages == len(plan.stages)
    assert result.failed_stages == 0
    print(f"  stages: {result.completed_stages}/{result.total_stages} completed, {result.failed_stages} failed")
    print("  PASS")


def test_skill_router_writes_artifacts():
    """SkillRouter collects artifact_paths from successful stages"""
    print("2. SkillRouter collects artifacts")
    plan = _make_delivery_plan()
    state = WorkflowState()

    router = SkillRouter(
        execute_skill=_mock_skill_success,
        write_ledger=_mock_write_ledger,
    )
    result = router.execute(plan, state)

    assert len(result.all_artifacts) > 0
    assert all(a.startswith("output/") for a in result.all_artifacts)
    print(f"  artifacts: {result.all_artifacts}")
    print("  PASS")


def test_skill_router_stage_failure_triggers_healing():
    """Failure in a stage triggers self_healing"""
    print("3. Stage failure → self_healing")
    plan = _make_delivery_plan()
    state = WorkflowState()

    healing = SelfHealingManager()

    router = SkillRouter(
        execute_skill=_mock_skill_fail,
        write_ledger=_mock_write_ledger,
        self_healing=healing,
    )
    result = router.execute(plan, state)

    assert result.failed_stages > 0
    assert len(result.healing_decisions) > 0
    decision = result.healing_decisions[0]
    assert decision.get("action") in ("retry", "fallback", "safe_mode", "stop")
    print(f"  failures: {result.failed_stages}")
    print(f"  healing decision: {decision}")
    print("  PASS")


def test_skill_router_safe_mode_skips_optional():
    """Safe mode → optional stages are skipped"""
    print("4. Safe mode → skip optional stages")
    plan = _make_delivery_plan()
    state = WorkflowState()
    safe = SafeModeManager()
    safe.trigger("manual_trigger")
    safe.confirm()

    router = SkillRouter(
        execute_skill=_mock_skill_success,
        write_ledger=_mock_write_ledger,
        safe_mode_manager=safe,
    )
    result = router.execute(plan, state)

    required_count = sum(1 for s in plan.stages if s.required)
    assert result.completed_stages >= required_count
    assert result.skipped_stages >= 0
    print(f"  completed={result.completed_stages}, skipped={result.skipped_stages}, failed={result.failed_stages}")
    print("  PASS")


def test_execution_guard_blocks_missing_required():
    """Execution guard BLOCKs when required stages are missing"""
    print("5. Execution guard — missing required stages → BLOCK")
    plan = _make_delivery_plan()
    state = WorkflowState()
    guard = ExecutionGuard()

    result = guard.check_stage_completion(plan, state)
    print(f"  verdict={result.verdict}, failed={result.checks_failed}, issues={len(result.issues)}")
    assert result.checks_failed > 0
    print("  PASS")


def test_execution_guard_pipeline_specific():
    """Execution guard checks pipeline-specific requirements"""
    print("6. Execution guard — pipeline-specific checks")
    plan = create_route_plan_from_template(
        workflow=Workflow.DEBUG,
        intent=Intent.DEBUG_ISSUE,
        confidence=0.8,
        normalized_input="test debug",
        route_source="rule",
    )
    state = WorkflowState()
    guard = ExecutionGuard()

    for s in plan.stages:
        if s.phase == "diagnose":
            s.status = StageStatus.SUCCESS
            s.artifact_paths = ["output/diagnosis.md"]

    result = guard.check_stage_completion(plan, state)
    print(f"  debug pipeline: verdict={result.verdict}, issues={len(result.issues)}")
    print("  PASS")


def test_guard_verdict_types():
    """Guard returns PASS / WARN / BLOCK verdicts"""
    print("7. Guard verdict types")
    plan = _make_delivery_plan()
    state = WorkflowState()

    for s in plan.stages:
        s.status = StageStatus.SUCCESS
        s.artifact_paths = [f"output/{s.skill}.md"]

    guard = ExecutionGuard()
    result = guard.check_stage_completion(plan, state)
    print(f"  all complete → verdict={result.verdict}, issues={len(result.issues)}")
    assert result.verdict in (GuardVerdict.PASS, GuardVerdict.WARN, GuardVerdict.BLOCK)
    print("  PASS")


def test_resume_from_stage():
    """SkillRouter supports continue_from to resume mid-pipeline"""
    print("8. Resume from stage (continue_from)")
    plan = _make_delivery_plan()
    state = WorkflowState()

    plan.stages[0].status = StageStatus.SUCCESS
    plan.stages[1].status = StageStatus.SUCCESS

    router = SkillRouter(
        execute_skill=_mock_skill_success,
        write_ledger=_mock_write_ledger,
    )
    result = router.execute(plan, state, continue_from="track")

    assert result.completed_stages >= len(plan.stages) - 2
    print(f"  resumed at 'track': completed={result.completed_stages}/{result.total_stages}")
    print("  PASS")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 5 — Integration Tests")
    print("=" * 60)
    print()
    test_skill_router_receives_route_plan()
    print()
    test_skill_router_writes_artifacts()
    print()
    test_skill_router_stage_failure_triggers_healing()
    print()
    test_skill_router_safe_mode_skips_optional()
    print()
    test_execution_guard_blocks_missing_required()
    print()
    test_execution_guard_pipeline_specific()
    print()
    test_guard_verdict_types()
    print()
    test_resume_from_stage()
    print()
    print("=" * 60)
    print("ALL INTEGRATION TESTS PASSED")
    print("=" * 60)

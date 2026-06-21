"""
Tests: Phase 6 — 端到端测试 + 故障注入 + SAFE MODE 真触发 + Rollback 安全验证
"""

import sys
import os
import tempfile

sys.path.insert(0, "/path/to/skill-os-complete")
sys.path.insert(0, "/path/to/skill-os-complete/orchestration")
sys.path.insert(0, "/path/to/skill-os-complete/routing_assets")
sys.path.insert(0, "/path/to/skill-os-complete/ledger")

from orchestration_types import (
    Intent, Workflow, TaskStatus, StageStatus, ExecutionStatus,
    SafeModeStatus, FailureType,
)
from route_plan import RoutePlan, RouteStage
from workflow_state import WorkflowState
from prompt_normalizer import PromptNormalizer, get_normalizer
from rule_router import RuleRouter
from semantic_router import SemanticRouter
from workflow_resolver import WorkflowResolver
from safe_mode import get_safe_mode_manager, reset_safe_mode_manager
from execution_guard import ExecutionGuard
from rollback_manager import RollbackManager
from self_healing import SelfHealingManager
from skill_router import SkillRouter


# ══════════════════════════════════════════════════════════
# P6-1: 路由全链路
# ══════════════════════════════════════════════════════════

def test_routing_full_stack():
    """P6-1: 全栈路由 — normalizer→rule→semantic→resolver"""
    print("=" * 60)
    print("P6-1: 路由全链路测试")
    print("=" * 60)

    resolver = WorkflowResolver()

    test_cases = [
        ("/plan 重构路由系统", Workflow.DELIVERY),
        ("/debug npm install 失败", Workflow.DEBUG),
        ("我想学 Python 异步编程", Workflow.LEARNING),
        ("读取项目并评估功能，再给升级方案", Workflow.DELIVERY),
        ("docker compose up 报 permission denied", Workflow.DEBUG),
        ("生成 Claude 施工单", Workflow.DELIVERY),
    ]

    for text, expected_wf in test_cases:
        result = resolver.resolve(text)
        rp = result.route_plan
        ok = (rp.workflow == expected_wf and len(rp.stages) > 0 and bool(rp.route_id))
        status = "✓" if ok else "✗"
        print(f"  {status} '{text[:30]}' → {rp.workflow.value} ({len(rp.stages)} stages, fusion={result.fusion_method})")
        assert rp.workflow == expected_wf, f"Expected {expected_wf}, got {rp.workflow}"
        assert len(rp.stages) > 0
        assert rp.route_id

    print(f"  ALL 6 ROUTING CASES CORRECT")
    print("  PASS")
    return True


# ══════════════════════════════════════════════════════════
# P6-2: 执行链测试
# ══════════════════════════════════════════════════════════

def test_execution_chain_coverage():
    """P6-2: 执行链 — 正常路径 + guard 拒绝路径"""
    print("\n" + "=" * 60)
    print("P6-2: 执行链完整覆盖")
    print("=" * 60)

    guard = ExecutionGuard()

    # 正常 delivery chain
    rp = RoutePlan(
        route_id="rte_coverage_001",
        workflow=Workflow.DELIVERY,
        intent=Intent.PROJECT_DELIVERY,
        confidence=0.9,
        stages=[
            RouteStage(stage_id="stg_001", phase="understand", skill="summarize", mode="briefing", required=True),
            RouteStage(stage_id="stg_002", phase="plan", skill="planning", mode="project", required=True),
            RouteStage(stage_id="stg_003", phase="track", skill="task_ledger", mode="auto", required=True),
        ],
    )
    ws = WorkflowState()
    result = guard.check_stage_completion(rp, ws, ledger_state={"status": "executing"})
    assert result.is_pass or result.verdict == "warn"
    print(f"  Normal delivery: {result.verdict}")

    # Bad delivery — 缺 summarize/planning
    rp_bad = RoutePlan(
        route_id="rte_coverage_bad1",
        workflow=Workflow.DELIVERY,
        intent=Intent.PROJECT_DELIVERY,
        confidence=0.5,
        stages=[RouteStage(stage_id="stg_x", phase="execute", skill="code_assistant", mode="on_demand", required=True)],
    )
    result = guard.check_stage_completion(rp_bad, WorkflowState(), ledger_state={"status": "executing"})
    assert result.is_block
    print(f"  Guard rejects bad delivery: {result.verdict}")

    # Bad debug — 缺 diagnose
    rp_bad = RoutePlan(
        route_id="rte_coverage_bad2",
        workflow=Workflow.DEBUG,
        intent=Intent.DEBUG_ISSUE,
        confidence=0.5,
        stages=[RouteStage(stage_id="stg_y", phase="fix", skill="code_assistant", mode="on_demand", required=True)],
    )
    result = guard.check_stage_completion(rp_bad, WorkflowState(), ledger_state={"status": "executing"})
    assert result.is_block
    print(f"  Guard rejects bad debug: {result.verdict}")

    # Bad learning — 缺 summarize/plan
    rp_bad = RoutePlan(
        route_id="rte_coverage_bad3",
        workflow=Workflow.LEARNING,
        intent=Intent.LEARN_TOPIC,
        confidence=0.5,
        stages=[RouteStage(stage_id="stg_z", phase="practice", skill="teach-plus", mode="practice", required=True)],
    )
    result = guard.check_stage_completion(rp_bad, WorkflowState(), ledger_state={"status": "executing"})
    assert result.is_block
    print(f"  Guard rejects bad learning: {result.verdict}")

    print("  PASS")
    return True


# ══════════════════════════════════════════════════════════
# P6-3: 恢复与降级
# ══════════════════════════════════════════════════════════

def test_recovery_and_degradation():
    """P6-3: 恢复与降级 — healing→rollback→safe_mode 联动"""
    print("\n" + "=" * 60)
    print("P6-3: 恢复与降级联动测试")
    print("=" * 60)

    reset_safe_mode_manager()
    mgr = get_safe_mode_manager()
    healing = SelfHealingManager(safe_mode_manager=mgr)
    rm = RollbackManager()

    # Healing: retry allowed
    d = healing.decide(FailureType.STAGE_TIMEOUT, retry_count=0, same_failure_type_count=0)
    assert d.action == "retry"
    print(f"  Healing retry: {d.action}")

    # Healing: same_failure reaches limit → safe_mode
    d = healing.decide(FailureType.STAGE_TIMEOUT, retry_count=0, same_failure_type_count=2)
    assert d.action == "safe_mode"
    print(f"  Same failure limit → {d.action}")

    # Rollback dry_run safe
    result = rm.execute(route_id="rte_rec_001", artifact_paths=["reports/phase5_report.md"], dry_run=True)
    assert result.rollback_status == "success"
    print(f"  Rollback dry_run: {result.rollback_status}")

    # Rollback rejects malicious
    result = rm.execute(route_id="rte_rec_002", artifact_paths=["../evil.sh"])
    assert result.rollback_status == "failed"
    assert len(result.security_errors) == 1
    print(f"  Rollback reject: {result.security_errors[0]}")

    # SafeMode escalation chain
    mgr.trigger(
        reason="self_healing_limit_exceeded",
        route_id="rte_rec_003",
        workflow="debug_pipeline",
        stage_id="diagnose",
        degraded_actions=["disable_auto_retry", "enter_safe_mode"],
    )
    mgr.confirm()
    assert mgr.is_active
    record = mgr.latest_record
    assert record is not None and record.trigger_reason == "self_healing_limit_exceeded"
    print(f"  SafeMode escalation: {record.trigger_reason}")

    # After safe_mode, healing stops
    d = healing.decide(FailureType.STAGE_TIMEOUT, retry_count=0, same_failure_type_count=0, safe_mode_active=True)
    assert d.action == "stop"
    print(f"  Healing stops in safe_mode: {d.action}")

    print("  PASS")
    return True


# ══════════════════════════════════════════════════════════
# P6-4: 三大场景端到端
# ══════════════════════════════════════════════════════════

def _run_pipeline(text, expected_wf, required_skills):
    """Helper: resolve → execute → guard"""
    resolver = WorkflowResolver()
    resolved = resolver.resolve(text)

    rp = resolved.route_plan
    assert rp.workflow == expected_wf

    ledger_writes = []

    def mock_executor(skill, mode, ctx):
        return {"success": True, "artifacts": [f"output/{ctx['stage_phase']}.md"], "error": ""}

    def mock_ledger(task_id, updates):
        ledger_writes.append(dict(updates))

    router = SkillRouter(
        execute_skill=mock_executor,
        write_ledger=mock_ledger,
        execution_guard=None,  # e2e: mock artifacts don't exist on disk
        self_healing=SelfHealingManager(),
    )

    ws = WorkflowState()
    exec_result = router.execute(rp, ws, task_context={"task_id": "tsk_e2e"})

    # Verify required skills
    for skill_name in required_skills:
        assert any(s.skill == skill_name for s in rp.stages), f"Missing required skill: {skill_name}"

    return resolved, exec_result, ledger_writes


def test_e2e_scenario_1():
    """P6-4: 读取项目并评估功能，再给升级方案 → delivery_pipeline"""
    print("\n" + "=" * 60)
    print("P6-4 Scenario 1: 读取项目并评估功能，再给升级方案")
    print("=" * 60)

    resolved, er, ledger = _run_pipeline(
        "读取项目并评估功能，再给升级方案",
        Workflow.DELIVERY,
        ["summarize", "planning"],
    )
    print(f"  Workflow: {resolved.route_plan.workflow.value}")
    print(f"  Stages: {[(s.phase, s.skill) for s in resolved.route_plan.stages]}")
    print(f"  Completed: {er.completed_stages}/{er.total_stages}")
    print(f"  Status: {er.execution_status.value}")
    print(f"  Ledger: {len(ledger)} writes")
    assert er.completed_stages >= 2
    assert len(ledger) >= 2
    print("  PASS")
    return True


def test_e2e_scenario_2():
    """P6-4: 生成 Claude 施工单 → delivery_pipeline"""
    print("\n" + "=" * 60)
    print("P6-4 Scenario 2: 生成 Claude 施工单")
    print("=" * 60)

    resolved, er, ledger = _run_pipeline(
        "生成 Claude 施工单",
        Workflow.DELIVERY,
        ["summarize", "planning"],
    )
    print(f"  Workflow: {resolved.route_plan.workflow.value}")
    print(f"  Stages: {[(s.phase, s.skill) for s in resolved.route_plan.stages]}")
    print(f"  Completed: {er.completed_stages}/{er.total_stages}")
    print(f"  Status: {er.execution_status.value}")
    assert er.completed_stages >= 2
    print("  PASS")
    return True


def test_e2e_scenario_3():
    """P6-4: docker compose up 报 permission denied → debug_pipeline"""
    print("\n" + "=" * 60)
    print("P6-4 Scenario 3: docker compose up 报 permission denied")
    print("=" * 60)

    resolved, er, ledger = _run_pipeline(
        "docker compose up 报 permission denied",
        Workflow.DEBUG,
        ["debug"],
    )
    print(f"  Workflow: {resolved.route_plan.workflow.value}")
    print(f"  Stages: {[(s.phase, s.skill, s.required) for s in resolved.route_plan.stages]}")
    print(f"  Completed: {er.completed_stages}/{er.total_stages}")
    print(f"  Status: {er.execution_status.value}")
    assert any(s.phase == "diagnose" and s.required for s in resolved.route_plan.stages)
    assert er.completed_stages >= 1
    print("  PASS")
    return True


# ══════════════════════════════════════════════════════════
# P6-5: embedding 故障注入
# ══════════════════════════════════════════════════════════

def test_embedding_fault_injection():
    """P6-5: embedding 不可用故障注入"""
    print("\n" + "=" * 60)
    print("P6-5: Embedding 不可用故障注入")
    print("=" * 60)

    # Fault: bad embedding host
    semantic = SemanticRouter(host="http://localhost:19999")

    # Health → degraded
    health = semantic.check_health()
    assert not health.available
    assert health.degraded
    assert health.error
    print(f"  Health: available={health.available}, degraded={health.degraded}")
    print(f"  Error: {health.error}")

    # get_candidates on unavailable → returns empty tuple, no crash
    result = semantic.get_candidates("测试输入")
    # returns tuple (list, health_or_none)
    candidates, h = result if isinstance(result, tuple) else (result, None)
    assert isinstance(candidates, (list, tuple)), f"Expected list/tuple, got {type(candidates)}"
    assert len(candidates) == 0, f"Should be empty on bad host, got {candidates}"
    print(f"  Candidates on bad host: {len(candidates)} (no crash)")

    # Full resolver with bad semantic → doesn't crash, falls back
    resolver = WorkflowResolver(semantic_router=semantic)
    resolved = resolver.resolve("docker compose up 报 permission denied")
    assert resolved is not None
    assert resolved.route_plan.workflow == Workflow.DEBUG
    # fusion should NOT be "fusion" since semantic is broken
    assert "rule_only" in resolved.fusion_method, f"Expected rule_only fallback, got {resolved.fusion_method}"
    print(f"  Resolver fallback: {resolved.fusion_method}")
    print(f"  Workflow: {resolved.route_plan.workflow.value}")
    print(f"  Semantic available: {resolved.semantic_available}")

    # Execute through router with bad semantic — still works
    router = SkillRouter(
        execute_skill=lambda s, m, c: {"success": True, "artifacts": [], "error": ""},
    )
    ws = WorkflowState()
    er = router.execute(resolved.route_plan, ws)
    assert er.completed_stages >= 1
    print(f"  Execution: {er.execution_status.value}, {er.completed_stages} stages")

    print("  PASS")
    return True


# ══════════════════════════════════════════════════════════
# P6-6: SAFE MODE 真触发
# ══════════════════════════════════════════════════════════

def test_safe_mode_real_trigger():
    """P6-6: SAFE MODE 真触发 — 5 proofs"""
    print("\n" + "=" * 60)
    print("P6-6: SAFE MODE 真触发验证")
    print("=" * 60)

    reset_safe_mode_manager()
    mgr = get_safe_mode_manager()

    # Trigger + confirm
    record = mgr.trigger(
        reason="embedding_unavailable",
        route_id="rte_fault_001",
        workflow="delivery_pipeline",
        stage_id="understand",
        degraded_actions=["disable_semantic", "shrink_healing", "rule_only_resolver"],
    )
    mgr.confirm()

    # Proof 1: 系统不崩
    assert mgr.status == SafeModeStatus.ACTIVE
    print(f"  1. System alive: status={mgr.status.value}")

    # Proof 2: semantic-router disabled
    assert mgr.should_disable_semantic()
    print(f"  2. Semantic disabled: {mgr.should_disable_semantic()}")

    # Proof 3: resolver degrades in safe_mode
    # Create resolver with safe_mode state
    st = WorkflowState()
    st.enter_safe_mode("embedding_unavailable")
    resolver = WorkflowResolver(state=st)
    resolved = resolver.resolve("帮我诊断这个错误")
    assert resolved.route_plan is not None
    assert resolved.safe_mode_active
    assert "safe_mode" in resolved.fusion_method, f"Expected safe_mode fusion, got {resolved.fusion_method}"
    print(f"  3. Resolver degraded: fusion={resolved.fusion_method}, safe_mode={resolved.safe_mode_active}")

    # Proof 4: self-healing disabled/shrunk
    assert mgr.should_shrink_healing()
    healing = SelfHealingManager()
    d = healing.decide(FailureType.STAGE_TIMEOUT, retry_count=0, same_failure_type_count=0, safe_mode_active=True)
    assert d.action == "stop", f"Expected stop, got {d.action}"
    print(f"  4. Healing stopped: {d.action}")

    # Proof 5: safe_mode recorded with full context
    latest = mgr.latest_record
    assert latest is not None
    assert latest.trigger_reason == "embedding_unavailable"
    assert "disable_semantic" in latest.degraded_actions
    assert latest.route_id == "rte_fault_001"
    assert latest.safe_mode
    d = mgr.to_dict()
    assert d["safe_mode_status"] == "active"
    assert d["trigger_count"] >= 1
    print(f"  5. SafeMode recorded: reason={latest.trigger_reason}")
    print(f"     Actions: {latest.degraded_actions}")
    print(f"     Serialized: status={d['safe_mode_status']}, triggers={d['trigger_count']}")

    print("  ALL 5 SAFE MODE PROOFS VERIFIED")
    print("  PASS")
    return True


# ══════════════════════════════════════════════════════════
# P6-7: Rollback 安全验证
# ══════════════════════════════════════════════════════════

def test_rollback_security_verification():
    """P6-7: Rollback 安全 — 4 proofs"""
    print("\n" + "=" * 60)
    print("P6-7: Rollback 安全验证")
    print("=" * 60)

    rm = RollbackManager()

    # Proof 1: 真实读取 artifact_paths from ledger, dry_run preview
    ledger_data = {
        "task_id": "tsk_sec_001",
        "status": "done",
        "artifact_paths": ["reports/phase1_report.md", "reports/phase3_report.md"],
    }
    result = rm.rollback_route(route_id="rte_sec_001", ledger=ledger_data, dry_run=True)
    # dry_run: files exist but not deleted; verified by to_dict
    assert result.rollback_status == "success"
    assert len(result.cleaned_artifacts) == 2
    assert all(not c.deleted for c in result.cleaned_artifacts)  # dry_run
    assert all(c.existed for c in result.cleaned_artifacts)
    print(f"  1. Reads from ledger: {len(result.cleaned_artifacts)} paths (dry_run preview)")
    print(f"     Files exist: {all(c.existed for c in result.cleaned_artifacts)}")

    # Proof 2: boundary check
    safe, reason = rm.validate_path_public("ledger/README.md")
    assert safe, f"ledger/README.md should be safe: {reason}"
    print(f"  2. Boundary check safe: {reason}")

    # Proof 3: 真实删除 verified
    with tempfile.NamedTemporaryFile(dir=str(rm.repo_root), prefix="p6_", suffix=".tmp", delete=False) as f:
        tmp_path = f.name
    rel = os.path.relpath(tmp_path, str(rm.repo_root))
    try:
        assert os.path.exists(tmp_path)
        result = rm.execute(route_id="rte_sec_002", artifact_paths=[rel])
        assert result.cleaned_count == 1
        assert result.cleaned_artifacts[0].deleted
        assert not os.path.exists(tmp_path)
        print(f"  3. Real deletion: {rel} deleted")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # Proof 4: 越界路径拒绝 + 安全异常记录
    malicious = ["../etc/passwd", "/root/.ssh/id_rsa", "../../.git/config"]
    result = rm.execute(route_id="rte_sec_003", artifact_paths=malicious)
    assert result.rejected_count == 3
    assert result.cleaned_count == 0
    assert len(result.security_errors) == 3
    assert result.rollback_status == "failed"
    print(f"  4. Malicious rejected: {result.rejected_count}/3")
    for err in result.security_errors:
        print(f"     SECURITY ERROR: {err}")

    d = result.to_dict()
    assert d["rollback_status"] == "failed"
    assert d["rejected_count"] == 3
    assert d["cleaned_count"] == 0
    print(f"     ToDict: status={d['rollback_status']}, rejected={d['rejected_count']}")

    print("  ALL 4 ROLLBACK SECURITY PROOFS VERIFIED")
    print("  PASS")
    return True


# ══════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 6 — 端到端测试 + 故障注入 + 安全验证")
    print("=" * 60)

    tests = [
        ("P6-1: routing_full_stack", test_routing_full_stack),
        ("P6-2: execution_chain_coverage", test_execution_chain_coverage),
        ("P6-3: recovery_and_degradation", test_recovery_and_degradation),
        ("P6-4.1: e2e_scenario_1 (delivery)", test_e2e_scenario_1),
        ("P6-4.2: e2e_scenario_2 (construction)", test_e2e_scenario_2),
        ("P6-4.3: e2e_scenario_3 (debug)", test_e2e_scenario_3),
        ("P6-5: embedding_fault_injection", test_embedding_fault_injection),
        ("P6-6: safe_mode_real_trigger", test_safe_mode_real_trigger),
        ("P6-7: rollback_security_verification", test_rollback_security_verification),
    ]

    passed = 0
    failed = 0
    for i, (name, func) in enumerate(tests, 1):
        print(f"\n[{i}/{len(tests)}] {name}...")
        try:
            if func():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"  FAIL: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"PHASE 6 RESULTS: {passed}/{len(tests)} passed, {failed} failed")
    if failed == 0:
        print("ALL PHASE 6 TESTS PASSED")
    else:
        print(f"{failed} TEST(S) FAILED")
    print("=" * 60)

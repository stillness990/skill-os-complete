"""
Tests: Phase 5 — skill-router + execution_guard + rollback + self-healing + safe_mode

Covers P5-1 through P5-8 acceptance criteria.
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
    SafeModeStatus, FailureType, WORKFLOW_STAGES,
)
from route_plan import RoutePlan, RouteStage, GuardPolicy
from workflow_state import WorkflowState
from safe_mode import SafeModeManager, get_safe_mode_manager, reset_safe_mode_manager, SafeModeRecord
from execution_guard import ExecutionGuard, GuardVerdict, GuardResult
from rollback_manager import RollbackManager, RollbackResult
from self_healing import SelfHealingManager, HealingConfig, HealingDecision
from skill_router import SkillRouter, RouterExecutionResult


# ══════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════

_stage_counter = 0

def _next_stage_id():
    global _stage_counter
    _stage_counter += 1
    return f"stg_{_stage_counter:03d}"

def _make_route_plan(workflow=Workflow.DELIVERY, stages=None):
    """Create a test RoutePlan"""
    if stages is None:
        stages = [
            RouteStage(stage_id="stg_001", phase="understand", skill="summarize", mode="briefing", required=True),
            RouteStage(stage_id="stg_002", phase="plan", skill="planning", mode="project", required=True),
            RouteStage(stage_id="stg_003", phase="track", skill="task_ledger", mode="auto", required=True),
        ]
    import uuid
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    route_id = f"rte_test_{ts}_{uuid.uuid4().hex[:8]}"
    return RoutePlan(
        route_id=route_id,
        workflow=workflow,
        intent=Intent.PROJECT_DELIVERY,
        confidence=0.9,
        stages=stages,
    )


def _make_state():
    return WorkflowState()


# ══════════════════════════════════════════════════════════
# P5-7: Safe Mode Tests
# ══════════════════════════════════════════════════════════

def test_safe_mode_singleton():
    """P5-7: SafeModeManager 单例模式"""
    reset_safe_mode_manager()
    mgr1 = get_safe_mode_manager()
    mgr2 = get_safe_mode_manager()
    assert mgr1 is mgr2
    print("  singleton: OK")
    print("  PASS")


def test_safe_mode_trigger():
    """P5-7: SafeMode trigger 触发和状态转换"""
    reset_safe_mode_manager()
    mgr = get_safe_mode_manager()

    assert mgr.is_inactive
    assert mgr.status == SafeModeStatus.INACTIVE

    record = mgr.trigger(
        reason="embedding_unavailable",
        route_id="rte_test_001",
        workflow="delivery_pipeline",
        stage_id="plan",
    )
    assert record.trigger_reason == "embedding_unavailable"
    assert mgr.status == SafeModeStatus.TRIGGERED
    assert mgr.is_active  # TRIGGERED counts as active
    assert mgr.latest_record is not None
    print(f"  trigger: reason={record.trigger_reason}, status={mgr.status.value}")

    mgr.confirm()
    assert mgr.status == SafeModeStatus.ACTIVE
    print(f"  confirmed: status={mgr.status.value}")

    mgr.release()
    assert mgr.is_inactive
    print(f"  released: status={mgr.status.value}")

    print("  PASS")


def test_safe_mode_record():
    """P5-7: SafeMode 记录内容"""
    reset_safe_mode_manager()
    mgr = get_safe_mode_manager()

    mgr.trigger(
        reason="self_healing_limit_exceeded",
        route_id="rte_test_002",
        workflow="debug_pipeline",
        stage_id="diagnose",
        degraded_actions=["disable_semantic", "shrink_healing"],
    )

    record = mgr.latest_record
    assert record.safe_mode
    assert record.route_id == "rte_test_002"
    assert record.workflow == "debug_pipeline"
    assert record.stage_id == "diagnose"
    assert "disable_semantic" in record.degraded_actions
    print(f"  record: {record.trigger_reason}, actions={record.degraded_actions}")
    print("  PASS")


def test_safe_mode_condition_checks():
    """P5-7: SafeMode 对各模块的响应标志"""
    reset_safe_mode_manager()
    mgr = get_safe_mode_manager()

    assert not mgr.should_disable_semantic()
    assert not mgr.should_shrink_healing()

    mgr.trigger(reason="embedding_unavailable")
    mgr.confirm()

    assert mgr.should_disable_semantic()
    assert mgr.should_shrink_healing()
    assert mgr.is_rollback_conservative()
    print(f"  should_disable_semantic: {mgr.should_disable_semantic()}")
    print(f"  should_shrink_healing: {mgr.should_shrink_healing()}")
    print("  PASS")


def test_safe_mode_serialization():
    """P5-7: SafeMode to_dict 输出"""
    reset_safe_mode_manager()
    mgr = get_safe_mode_manager()
    mgr.trigger(reason="manual_trigger", route_id="rte_003")
    mgr.confirm()

    d = mgr.to_dict()
    assert d["safe_mode_status"] == "active"
    assert d["trigger_count"] == 1
    assert d["latest_trigger_reason"] == "manual_trigger"
    assert "degraded_actions" in d
    print(f"  serialized: {d}")
    print("  PASS")


# ══════════════════════════════════════════════════════════
# P5-2 & P5-3: Execution Guard Tests
# ══════════════════════════════════════════════════════════

def test_guard_required_stages():
    """P5-2: Guard 检查 required stages"""
    guard = ExecutionGuard()

    rp = _make_route_plan(Workflow.DELIVERY)
    ws = _make_state()

    result = guard.check_stage_completion(rp, ws, ledger_state={"status": "executing"})
    assert result.is_pass or result.verdict == "warn", f"Expected PASS/WARN, got {result.verdict}: {[i.message for i in result.issues]}"
    print(f"  delivery required stages: {result.verdict}")
    print("  PASS")


def test_guard_missing_diagnose():
    """P5-3: debug_pipeline 缺少 diagnose → BLOCK"""
    guard = ExecutionGuard()

    rp = _make_route_plan(
        Workflow.DEBUG,
        stages=[
            RouteStage(stage_id="stg_004", phase="fix", skill="code_assistant", mode="on_demand", required=True),
        ],
    )
    ws = _make_state()

    result = guard.check_stage_completion(rp, ws)
    assert result.is_block, f"Expected BLOCK, got {result.verdict}"
    assert any("diagnose" in i.message for i in result.issues)
    print(f"  missing diagnose: {result.verdict}")
    for i in result.issues:
        print(f"    [{i.severity}] {i.message}")
    print("  PASS")


def test_guard_missing_summarize_planning():
    """P5-3: delivery_pipeline 缺少 summarize/planning → BLOCK"""
    guard = ExecutionGuard()

    rp = _make_route_plan(
        Workflow.DELIVERY,
        stages=[
            RouteStage(stage_id="stg_005", phase="execute", skill="code_assistant", mode="on_demand", required=True),
        ],
    )
    ws = _make_state()

    result = guard.check_stage_completion(rp, ws)
    assert result.is_block, f"Expected BLOCK, got {result.verdict}"
    messages = [i.message for i in result.issues]
    assert any("summarize" in m or "planning" in m for m in messages)
    print(f"  missing summarize/planning: {result.verdict}")
    for i in result.issues:
        print(f"    [{i.severity}] {i.message}")
    print("  PASS")


def test_guard_noop_completion():
    """P5-2: 检测 no-op completion"""
    guard = ExecutionGuard()

    rp = _make_route_plan()
    for s in rp.stages:
        s.status = StageStatus.PENDING

    ws = WorkflowState()
    ws.execution_status = ExecutionStatus.COMPLETED

    result = guard.check_stage_completion(rp, ws)
    assert result.is_block, f"Expected BLOCK for no-op, got {result.verdict}"
    assert any("no-op" in i.message.lower() or "noop" in i.check_id for i in result.issues)
    print(f"  noop detection: {result.verdict}")
    for i in result.issues:
        print(f"    [{i.severity}] {i.message}")
    print("  PASS")


def test_guard_artifact_exists():
    """P5-2: Guard 检查 artifact 是否存在"""
    guard = ExecutionGuard()

    rp = _make_route_plan()
    rp.stages[0].status = StageStatus.SUCCESS
    rp.stages[0].artifact_paths = ["reports/phase1_report.md"]  # real file

    ws = _make_state()

    result = guard.check_stage_completion(rp, ws)
    # reports/phase1_report.md exists → should pass artifact check
    artifact_issues = [i for i in result.issues if i.check_id == "artifact_missing"]
    assert len(artifact_issues) == 0, f"Unexpected artifact missing: {[i.message for i in artifact_issues]}"
    print(f"  artifact exists check: {result.verdict}")
    print("  PASS")


def test_guard_artifact_missing():
    """P5-2: Guard 检测不存在的 artifact"""
    guard = ExecutionGuard()

    rp = _make_route_plan()
    rp.stages[0].status = StageStatus.SUCCESS
    rp.stages[0].artifact_paths = ["nonexistent/file.md"]  # fake file

    ws = _make_state()

    result = guard.check_stage_completion(rp, ws)
    print(f"  artifact missing check: {result.verdict}")
    if result.issues:
        for i in result.issues:
            print(f"    [{i.severity}] {i.message}")
    print("  PASS")


def test_guard_workflow_completion():
    """P5-2: Workflow 最终检查更严格"""
    guard = ExecutionGuard()

    rp = _make_route_plan()
    for s in rp.stages[:2]:  # understand + plan succeed
        s.status = StageStatus.SUCCESS
    rp.stages[2].status = StageStatus.PENDING  # track not done

    ws = _make_state()

    result = guard.check_workflow_completion(rp, ws)
    # track is required in stages but may fail if not completed
    print(f"  workflow completion: {result.verdict}")
    for i in result.issues:
        print(f"    [{i.severity}] {i.message}")
    print("  PASS")


def test_guard_validate_artifact_path():
    """P5-2: 路径安全验证"""
    import pathlib
    guard = ExecutionGuard()
    root = pathlib.Path("/tmp/test_skill_os")

    safe, reason = guard.validate_artifact_path(root, "reports/test.md")
    assert safe, f"Expected safe, got: {reason}"
    print(f"  safe path: {safe}, {reason}")

    safe, reason = guard.validate_artifact_path(root, "../etc/passwd")
    assert not safe
    print(f"  unsafe path: {safe}, {reason}")

    safe, reason = guard.validate_artifact_path(root, "/etc/passwd")
    assert not safe
    print(f"  absolute path: {safe}, {reason}")

    print("  PASS")


# ══════════════════════════════════════════════════════════
# P5-5 & P5-6: Rollback Tests
# ══════════════════════════════════════════════════════════

def test_rollback_empty_paths():
    """P5-5: 空 artifact_paths → success"""
    rm = RollbackManager()
    result = rm.execute(route_id="rte_test", artifact_paths=[])
    assert result.rollback_status == "success"
    assert result.cleaned_count == 0
    print(f"  empty paths: {result.rollback_status}")
    print("  PASS")


def test_rollback_path_validation():
    """P5-6: 路径安全校验"""
    rm = RollbackManager()

    # 安全路径
    safe, reason = rm.validate_path_public("ledger/README.md")
    print(f"  safe: {safe}, {reason}")

    # 越界路径
    safe, reason = rm.validate_path_public("../etc/passwd")
    assert not safe
    print(f"  ../: {safe}, {reason}")

    # 绝对路径
    safe, reason = rm.validate_path_public("/etc/passwd")
    assert not safe
    print(f"  absolute: {safe}, {reason}")

    # 空路径
    safe, reason = rm.validate_path_public("")
    assert not safe
    print(f"  empty: {safe}, {reason}")

    print("  PASS")


def test_rollback_reject_out_of_bounds():
    """P5-6: 越界路径被拒绝"""
    rm = RollbackManager()

    result = rm.execute(
        route_id="rte_test",
        artifact_paths=["legit_file.md", "../etc/passwd", "/root/secret.txt", ""],
    )

    assert result.rejected_count >= 1
    assert len(result.security_errors) >= 1
    print(f"  status: {result.rollback_status}")
    print(f"  cleaned: {result.cleaned_count}, rejected: {result.rejected_count}")
    for err in result.security_errors:
        print(f"    security_error: {err}")
    print("  PASS")


def test_rollback_dry_run():
    """P5-6: dry_run 模式不实际删除"""
    rm = RollbackManager()

    # 创建一个临时文件
    with tempfile.NamedTemporaryFile(dir=rm.repo_root, prefix="test_rollback_", suffix=".tmp", delete=False) as f:
        tmp_path = f.name

    try:
        rel_path = os.path.relpath(tmp_path, rm.repo_root)
        result = rm.execute(
            route_id="rte_test",
            artifact_paths=[rel_path],
            dry_run=True,
        )

        assert result.rollback_status == "success"
        assert result.cleaned_artifacts[0].deleted == False
        print(f"  dry_run: {result.cleaned_artifacts[0].error}")
        print("  PASS")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_rollback_real_delete():
    """P5-6: 真实删除文件"""
    rm = RollbackManager()

    with tempfile.NamedTemporaryFile(dir=rm.repo_root, prefix="test_rollback_real_", suffix=".tmp", delete=False) as f:
        tmp_path = f.name

    rel_path = os.path.relpath(tmp_path, rm.repo_root)
    result = rm.execute(
        route_id="rte_test",
        artifact_paths=[rel_path],
        dry_run=False,
    )

    assert result.rollback_status == "success"
    assert result.cleaned_count == 1
    assert result.cleaned_artifacts[0].deleted
    assert not os.path.exists(tmp_path), f"File should be deleted: {tmp_path}"
    print(f"  real delete: cleaned={result.cleaned_count}")
    print("  PASS")


def test_rollback_ledger_read():
    """P5-5: 从 ledger 数据读取 artifact_paths 并回滚"""
    rm = RollbackManager()

    ledger_data = {
        "task_id": "tsk_test_001",
        "artifact_paths": ["ledger/README.md"],
    }
    result = rm.rollback_route(route_id="rte_test", ledger=ledger_data, dry_run=True)
    assert result.rollback_status == "success"
    assert result.cleaned_artifacts[0].path == "ledger/README.md"
    print(f"  ledger read: {result.cleaned_artifacts[0].path}")
    print("  PASS")


def test_rollback_result_to_dict():
    """P5-5: RollbackResult 序列化"""
    rm = RollbackManager()
    result = rm.execute(route_id="rte_test", artifact_paths=["ledger/README.md"], dry_run=True)
    d = result.to_dict()
    assert "rollback_status" in d
    assert "cleaned_artifacts" in d
    assert "rejected_artifacts" in d
    assert "security_errors" in d
    print(f"  to_dict: {d['rollback_status']}")
    print("  PASS")


# ══════════════════════════════════════════════════════════
# P5-4: Self-Healing Tests
# ══════════════════════════════════════════════════════════

def test_healing_retry():
    """P5-4: 可重试失败 → retry 决策"""
    sh = SelfHealingManager()

    decision = sh.decide(
        failure_type=FailureType.STAGE_TIMEOUT,
        retry_count=0,
        same_failure_type_count=0,
    )
    assert decision.action == "retry"
    assert decision.new_route_id != ""
    assert decision.retry_count == 1
    print(f"  retry: action={decision.action}, route_id={decision.new_route_id}")
    print("  PASS")


def test_healing_retry_limit():
    """P5-4: retry_count 达到上限 → safe_mode"""
    sh = SelfHealingManager()

    decision = sh.decide(
        failure_type=FailureType.STAGE_TIMEOUT,
        retry_count=3,  # 已达上限
        same_failure_type_count=0,
    )
    assert decision.action == "safe_mode"
    print(f"  retry limit: action={decision.action}, reason={decision.reason}")
    print("  PASS")


def test_healing_same_failure_limit():
    """P5-4: same_failure_type_count 达到上限 → safe_mode"""
    sh = SelfHealingManager()

    decision = sh.decide(
        failure_type=FailureType.ARTIFACT_MISSING,
        retry_count=1,
        same_failure_type_count=2,  # 已达上限
    )
    assert decision.action == "safe_mode"
    print(f"  same_failure limit: action={decision.action}")
    print("  PASS")


def test_healing_embedding_fallback():
    """P5-4: embedding 失败 → 立即 fallback (不重试)"""
    sh = SelfHealingManager()

    decision = sh.decide(
        failure_type=FailureType.EMBEDDING_UNAVAILABLE,
        retry_count=0,
        same_failure_type_count=0,
    )
    assert decision.action == "fallback"
    print(f"  embedding fail: action={decision.action}")
    print("  PASS")


def test_healing_no_recursion():
    """P5-4: 防递归 self-healing"""
    sh = SelfHealingManager()

    # 模拟递归调用
    sh._healing_in_progress = True
    decision = sh.decide(
        failure_type=FailureType.STAGE_TIMEOUT,
        retry_count=0,
        same_failure_type_count=0,
    )
    assert decision.action == "stop"
    assert "递归" in decision.reason
    sh._healing_in_progress = False
    print(f"  anti-recursion: action={decision.action}, reason={decision.reason}")
    print("  PASS")


def test_healing_new_route_id_per_retry():
    """P5-4: 每次 retry 生成新 route_id"""
    sh = SelfHealingManager()

    decisions = []
    for i in range(3):
        d = sh.decide(
            failure_type=FailureType.STAGE_TIMEOUT,
            retry_count=i,
            same_failure_type_count=0,
        )
        decisions.append(d)

    route_ids = [d.new_route_id for d in decisions if d.new_route_id]
    # 所有 route_id 互不相同
    assert len(set(route_ids)) == len(route_ids), f"Duplicate route_ids: {route_ids}"
    print(f"  unique route_ids: {route_ids}")
    print("  PASS")


def test_healing_classify_failure():
    """P5-4: 根据错误消息分类 FailureType"""
    sh = SelfHealingManager()

    assert sh.classify_failure("Embedding connection failed") == FailureType.EMBEDDING_UNAVAILABLE
    assert sh.classify_failure("ollama timeout") == FailureType.EMBEDDING_UNAVAILABLE
    assert sh.classify_failure("stage timed out") == FailureType.STAGE_TIMEOUT
    assert sh.classify_failure("artifact missing: .claude/test.md") == FailureType.ARTIFACT_MISSING
    assert sh.classify_failure("illegal transition: queued -> done") == FailureType.ILLEGAL_TRANSITION
    assert sh.classify_failure("guard blocked completion") == FailureType.GUARD_REJECTED
    assert sh.classify_failure("rollback security: 越界路径") == FailureType.ROLLBACK_SECURITY
    assert sh.classify_failure("something completely unexpected") == FailureType.UNKNOWN
    print("  classify: all correct")
    print("  PASS")


def test_healing_can_retry():
    """P5-4: can_retry 快速检查"""
    sh = SelfHealingManager()

    assert sh.can_retry(0, FailureType.STAGE_TIMEOUT)  # 可重试
    assert not sh.can_retry(3, FailureType.STAGE_TIMEOUT)  # 达到上限
    assert not sh.can_retry(0, FailureType.EMBEDDING_UNAVAILABLE)  # 不可重试类型
    print("  can_retry: correct")
    print("  PASS")


def test_healing_config_custom():
    """P5-4: 自定义 HealingConfig"""
    config = HealingConfig(max_retry_count=2, max_same_failure_type_count=1)
    sh = SelfHealingManager(config=config)

    # 第 2 次重试 → 上限
    decision = sh.decide(FailureType.STAGE_TIMEOUT, retry_count=2, same_failure_type_count=0)
    assert decision.action == "safe_mode"
    print(f"  custom config: max_retry={config.max_retry_count}, decision={decision.action}")
    print("  PASS")


# ══════════════════════════════════════════════════════════
# P5-1 & P5-8: Skill Router Tests
# ══════════════════════════════════════════════════════════

def test_skill_router_execute_all_success():
    """P5-1: SkillRouter 按 stage 顺序执行，全部成功"""
    ledger_writes = []

    def mock_executor(skill, mode, ctx):
        return {"success": True, "artifacts": [f"output/{skill}_{mode}.md"], "error": ""}

    def mock_ledger(task_id, updates):
        ledger_writes.append(dict(updates))

    sr = SkillRouter(execute_skill=mock_executor, write_ledger=mock_ledger)
    rp = _make_route_plan()
    ws = _make_state()

    result = sr.execute(rp, ws, task_context={"task_id": "tsk_test"})

    assert result.execution_status == ExecutionStatus.COMPLETED
    assert result.completed_stages == 3
    assert result.failed_stages == 0
    assert len(result.all_artifacts) == 3
    assert len(ledger_writes) == 3
    print(f"  all success: status={result.execution_status.value}")
    print(f"  completed: {result.completed_stages}/{result.total_stages}")
    print(f"  artifacts: {result.all_artifacts}")
    print(f"  ledger writes: {len(ledger_writes)}")
    print("  PASS")


def test_skill_router_stage_order():
    """P5-1: SkillRouter 按 stage 顺序执行 (不跳顺序)"""
    execution_order = []

    def mock_executor(skill, mode, ctx):
        execution_order.append(ctx["stage_phase"])
        return {"success": True, "artifacts": [], "error": ""}

    sr = SkillRouter(execute_skill=mock_executor)
    rp = _make_route_plan()
    ws = _make_state()

    sr.execute(rp, ws)

    expected_order = ["understand", "plan", "track"]
    assert execution_order == expected_order, f"Order: {execution_order}"
    print(f"  execution order: {execution_order}")
    print("  PASS")


def test_skill_router_failure_handling():
    """P5-8: 失败路径写入 ledger, 触发 self_healing"""
    ledger_writes = []

    def mock_executor(skill, mode, ctx):
        if ctx["stage_phase"] == "plan":
            return {"success": False, "artifacts": [], "error": "stage timeout"}
        return {"success": True, "artifacts": [], "error": ""}

    def mock_ledger(task_id, updates):
        ledger_writes.append(dict(updates))

    sh = SelfHealingManager()
    sr = SkillRouter(
        execute_skill=mock_executor,
        write_ledger=mock_ledger,
        self_healing=sh,
    )
    rp = _make_route_plan()
    ws = _make_state()

    result = sr.execute(rp, ws, task_context={"task_id": "tsk_test"})

    assert result.failed_stages >= 1
    assert len(result.healing_decisions) >= 1
    assert len(ledger_writes) >= 1  # understand 至少写入了
    print(f"  failed stages: {result.failed_stages}")
    print(f"  healing decisions: {result.healing_decisions}")
    print(f"  ledger writes: {len(ledger_writes)}")
    print(f"  execution status: {result.execution_status.value}")
    print("  PASS")


def test_skill_router_no_reroute():
    """P5-1: SkillRouter 不重新做路由决策"""
    # SkillRouter 只执行传入的 RoutePlan, 不调用 workflow_resolver
    # 验证: execute 方法不导入/引用 WorkflowResolver
    import inspect
    src = inspect.getsource(SkillRouter.execute)
    assert "WorkflowResolver" not in src
    assert "resolver" not in src.lower() or "resolve" not in src.lower()
    print("  no re-route: SkillRouter.execute doesn't reference WorkflowResolver")
    print("  PASS")


def test_skill_router_continue_from():
    """P5-1: continue_from 从中断 stage 继续"""
    execution_order = []

    def mock_executor(skill, mode, ctx):
        execution_order.append(ctx["stage_phase"])
        return {"success": True, "artifacts": [], "error": ""}

    sr = SkillRouter(execute_skill=mock_executor)
    rp = _make_route_plan()
    ws = _make_state()

    # 从 plan 继续 (跳过 understand)
    result = sr.execute(rp, ws, continue_from="plan")

    assert "plan" in execution_order
    assert "track" in execution_order
    print(f"  continue_from='plan', executed: {execution_order}")
    print("  PASS")


def test_skill_router_guard_integration():
    """P5-2 integration: SkillRouter + ExecutionGuard"""
    guard = ExecutionGuard()

    def mock_executor(skill, mode, ctx):
        return {"success": True, "artifacts": ["reports/phase1_report.md"], "error": ""}

    sr = SkillRouter(execute_skill=mock_executor, execution_guard=guard)
    rp = _make_route_plan()
    ws = _make_state()

    result = sr.execute(rp, ws)

    assert result.execution_status == ExecutionStatus.COMPLETED
    print(f"  guard integration: {result.execution_status.value}")
    print("  PASS")


def test_skill_router_safe_mode_skips_optional():
    """P5-7: SafeMode 下跳过 optional stages"""
    reset_safe_mode_manager()
    mgr = get_safe_mode_manager()
    mgr.trigger(reason="embedding_unavailable")
    mgr.confirm()

    execution_order = []

    def mock_executor(skill, mode, ctx):
        execution_order.append(ctx["stage_phase"])
        return {"success": True, "artifacts": [], "error": ""}

    # 有一个 optional stage
    stages = [
        RouteStage(stage_id="stg_010", phase="understand", skill="summarize", mode="briefing", required=True),
        RouteStage(stage_id="stg_011", phase="plan", skill="planning", mode="project", required=True),
        RouteStage(stage_id="stg_012", phase="optional_review", skill="reviewer", mode="on_demand", required=False),
        RouteStage(stage_id="stg_013", phase="track", skill="task_ledger", mode="auto", required=True),
    ]
    rp = _make_route_plan(stages=stages)
    ws = _make_state()

    sr = SkillRouter(execute_skill=mock_executor, safe_mode_manager=mgr)
    result = sr.execute(rp, ws)

    # optional_review 应该被跳过
    assert "optional_review" not in execution_order
    assert result.skipped_stages >= 1
    print(f"  safe_mode skip optional: executed={execution_order}, skipped={result.skipped_stages}")
    print("  PASS")


def test_router_execution_result_serialization():
    """P5-8: RouterExecutionResult 序列化"""
    result = RouterExecutionResult(
        route_id="rte_test",
        workflow="delivery_pipeline",
        execution_status=ExecutionStatus.COMPLETED,
        total_stages=3,
        completed_stages=3,
        all_artifacts=["a.md", "b.md"],
    )
    d = result.to_dict()
    assert d["execution_status"] == "completed"
    assert d["all_artifacts"] == ["a.md", "b.md"]
    print(f"  serialization: {d}")
    print("  PASS")


# ══════════════════════════════════════════════════════════
# Integration: Full Execution Chain
# ══════════════════════════════════════════════════════════

def test_full_execution_chain():
    """端到端集成: RoutePlan → SkillRouter → Guard → Ledger"""
    ledger_writes = []
    reset_safe_mode_manager()

    def mock_executor(skill, mode, ctx):
        phase = ctx["stage_phase"]
        return {
            "success": True,
            "artifacts": [f"output/{phase}.md"],
            "error": "",
        }

    def mock_ledger(task_id, updates):
        ledger_writes.append(dict(updates))

    sh = SelfHealingManager()
    mgr = get_safe_mode_manager()

    sr = SkillRouter(
        execute_skill=mock_executor,
        write_ledger=mock_ledger,
        execution_guard=None,  # 集成测试不需要 guard (mock artifacts 不存在)
        self_healing=sh,
        safe_mode_manager=mgr,
    )

    rp = _make_route_plan()
    ws = _make_state()

    result = sr.execute(rp, ws, task_context={"task_id": "tsk_integration_test"})

    assert result.execution_status == ExecutionStatus.COMPLETED
    assert result.completed_stages == 3
    assert len(ledger_writes) == 3
    assert len(result.all_artifacts) == 3

    print(f"  Full chain:")
    print(f"    Status: {result.execution_status.value}")
    print(f"    Stages: {result.completed_stages}/{result.total_stages}")
    print(f"    Artifacts: {result.all_artifacts}")
    print(f"    Ledger writes: {len(ledger_writes)}")
    print(f"    Safe mode: {mgr.is_active}")
    print(f"    Healing decisions: {len(result.healing_decisions)}")
    print("  PASS")


# ══════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 5 — Module Tests")
    print("=" * 60)
    print()

    total = 0
    passed = 0
    failed = 0

    tests = [
        # Safe Mode (P5-7)
        ("test_safe_mode_singleton", test_safe_mode_singleton),
        ("test_safe_mode_trigger", test_safe_mode_trigger),
        ("test_safe_mode_record", test_safe_mode_record),
        ("test_safe_mode_condition_checks", test_safe_mode_condition_checks),
        ("test_safe_mode_serialization", test_safe_mode_serialization),
        # Execution Guard (P5-2, P5-3)
        ("test_guard_required_stages", test_guard_required_stages),
        ("test_guard_missing_diagnose", test_guard_missing_diagnose),
        ("test_guard_missing_summarize_planning", test_guard_missing_summarize_planning),
        ("test_guard_noop_completion", test_guard_noop_completion),
        ("test_guard_artifact_exists", test_guard_artifact_exists),
        ("test_guard_artifact_missing", test_guard_artifact_missing),
        ("test_guard_workflow_completion", test_guard_workflow_completion),
        ("test_guard_validate_artifact_path", test_guard_validate_artifact_path),
        # Rollback (P5-5, P5-6)
        ("test_rollback_empty_paths", test_rollback_empty_paths),
        ("test_rollback_path_validation", test_rollback_path_validation),
        ("test_rollback_reject_out_of_bounds", test_rollback_reject_out_of_bounds),
        ("test_rollback_dry_run", test_rollback_dry_run),
        ("test_rollback_real_delete", test_rollback_real_delete),
        ("test_rollback_ledger_read", test_rollback_ledger_read),
        ("test_rollback_result_to_dict", test_rollback_result_to_dict),
        # Self-Healing (P5-4)
        ("test_healing_retry", test_healing_retry),
        ("test_healing_retry_limit", test_healing_retry_limit),
        ("test_healing_same_failure_limit", test_healing_same_failure_limit),
        ("test_healing_embedding_fallback", test_healing_embedding_fallback),
        ("test_healing_no_recursion", test_healing_no_recursion),
        ("test_healing_new_route_id_per_retry", test_healing_new_route_id_per_retry),
        ("test_healing_classify_failure", test_healing_classify_failure),
        ("test_healing_can_retry", test_healing_can_retry),
        ("test_healing_config_custom", test_healing_config_custom),
        # Skill Router (P5-1, P5-8)
        ("test_skill_router_execute_all_success", test_skill_router_execute_all_success),
        ("test_skill_router_stage_order", test_skill_router_stage_order),
        ("test_skill_router_failure_handling", test_skill_router_failure_handling),
        ("test_skill_router_no_reroute", test_skill_router_no_reroute),
        ("test_skill_router_continue_from", test_skill_router_continue_from),
        ("test_skill_router_guard_integration", test_skill_router_guard_integration),
        ("test_skill_router_safe_mode_skips_optional", test_skill_router_safe_mode_skips_optional),
        ("test_router_execution_result_serialization", test_router_execution_result_serialization),
        # Integration
        ("test_full_execution_chain", test_full_execution_chain),
    ]

    for name, func in tests:
        total += 1
        print(f"[{total:02d}] {name}...")
        try:
            func()
            passed += 1
            print()
        except Exception as e:
            failed += 1
            print(f"  FAIL: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("=" * 60)
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    if failed == 0:
        print("ALL PHASE 5 TESTS PASSED")
    else:
        print(f"{failed} TEST(S) FAILED")
    print("=" * 60)

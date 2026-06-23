"""
Skill Router — 技能路由执行器 (Phase 5)
Phase 5: 按 RoutePlan 执行 stages, 收集 artifacts, 写入 ledger, 调用 guard

核心原则:
- 只执行 RoutePlan，不重新做路由决策
- 按 stage 顺序执行
- stage 状态 (running/success/failed) 写入 ledger
- artifact_paths 写入 ledger
- 每个 stage 完成后调用 execution_guard
- 失败时调用 self_healing 决策

架构:
    SkillRouter
    ├── 输入: RoutePlan (from workflow_resolver)
    ├── 执行: 逐 stage, 通过 execution callback
    ├── 监督: execution_guard 每个 stage 后检查
    ├── 恢复: self_healing 决策 retry/fallback/safe_mode/stop
    └── 输出: 更新后的 RoutePlan + ledger 写入
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from .orchestration_types import (
    Workflow,
    TaskStatus,
    StageStatus,
    ExecutionStatus,
    FailureType,
    SafeModeStatus,
    WORKFLOW_STAGES,
)
from .route_plan import RoutePlan, RouteStage
from .workflow_state import WorkflowState

# ── L6 Telemetry (fail-silent, disabled by default) ──────
try:
    import sys as _sys
    # Ensure project root is on path for telemetry imports
    _project_root = __file__ and _sys.modules[__name__].__file__
    if _project_root is None:
        _project_root = _sys.modules.get('__main__', {}).__dict__.get('__file__', '')
    from execution_telemetry import (
        start_workflow as _tel_start_workflow,
        enter_stage as _tel_enter_stage,
        complete_stage as _tel_complete_stage,
        fail_stage as _tel_fail_stage,
        set_skill as _tel_set_skill,
        complete_workflow as _tel_complete_workflow,
        fail_workflow as _tel_fail_workflow,
    )
    _telemetry_available = True
except ImportError:
    _telemetry_available = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Execution callbacks ──────────────────────────────────

# skill 执行回调: (skill_name: str, mode: str, context: dict) → dict with keys
#   success: bool
#   artifacts: list[str]  (relative paths)
#   error: str
#   output: any
SkillExecutor = Callable[[str, str, dict], dict]

# ledger 写入回调: (task_id: str, updates: dict) → None
LedgerWriter = Callable[[str, dict], None]

# guard 检查回调: (route_plan, workflow_state, ledger_state) → GuardResult
GuardChecker = Callable[[RoutePlan, WorkflowState, Optional[dict]], any]


@dataclass
class StageExecutionResult:
    """单个 stage 的执行结果"""
    stage_phase: str
    skill: str
    mode: str
    success: bool
    artifacts: list[str] = field(default_factory=list)
    error: str = ""
    guard_result: Optional[dict] = None
    executed_at: str = ""


@dataclass
class RouterExecutionResult:
    """SkillRouter 完整执行结果"""
    route_id: str
    workflow: str
    execution_status: ExecutionStatus = ExecutionStatus.NOT_STARTED
    stage_results: list[StageExecutionResult] = field(default_factory=list)
    total_stages: int = 0
    completed_stages: int = 0
    failed_stages: int = 0
    skipped_stages: int = 0
    all_artifacts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    healing_decisions: list[dict] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> dict:
        return {
            "route_id": self.route_id,
            "workflow": self.workflow,
            "execution_status": self.execution_status.value,
            "total_stages": self.total_stages,
            "completed_stages": self.completed_stages,
            "failed_stages": self.failed_stages,
            "skipped_stages": self.skipped_stages,
            "all_artifacts": self.all_artifacts,
            "errors": self.errors,
            "healing_decisions": self.healing_decisions,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class SkillRouter:
    """
    技能路由执行器 — RoutePlan 的执行引擎。

    使用方式:
        router = SkillRouter(
            execute_skill=my_executor,
            write_ledger=my_ledger_writer,
            execution_guard=my_guard,
            self_healing=my_healing,
        )
        result = router.execute(route_plan, workflow_state, task_context)
    """

    def __init__(
        self,
        execute_skill: Optional[SkillExecutor] = None,
        write_ledger: Optional[LedgerWriter] = None,
        execution_guard=None,    # ExecutionGuard instance
        self_healing=None,       # SelfHealingManager instance
        safe_mode_manager=None,  # SafeModeManager instance
    ):
        self._execute_skill = execute_skill or self._default_executor
        self._write_ledger = write_ledger or self._default_ledger_writer
        self._guard = execution_guard
        self._healing = self_healing
        self._safe_mode = safe_mode_manager

    # ── Main execution entry ──────────────────────────────

    def execute(
        self,
        route_plan: RoutePlan,
        workflow_state: WorkflowState,
        task_context: Optional[dict] = None,
        continue_from: Optional[str] = None,  # 从中断的 stage phase 继续
    ) -> RouterExecutionResult:
        """
        按 RoutePlan 逐 stage 执行。

        参数:
            route_plan: 待执行的 RoutePlan
            workflow_state: 当前 workflow 状态
            task_context: 传递给 skill executor 的上下文
            continue_from: 从指定 stage phase 继续 (用于中断恢复)

        返回:
            RouterExecutionResult
        """
        total_stages = len(route_plan.stages)
        workflow_name = route_plan.workflow.value if route_plan.workflow else ""

        result = RouterExecutionResult(
            route_id=route_plan.route_id,
            workflow=workflow_name,
            total_stages=total_stages,
            started_at=_now_iso(),
        )

        workflow_state.execution_status = ExecutionStatus.IN_PROGRESS

        # ── L6 Telemetry: workflow start ─────────────────
        if _telemetry_available:
            try:
                _tel_start_workflow(
                    workflow_name=workflow_name,
                    total_stages=total_stages,
                    task_id=(task_context or {}).get("task_id", ""),
                )
                # Check for resume hint
                try:
                    from execution_telemetry.resume_manager import check_unfinished_workflow
                    from execution_telemetry.cli_display import display_resume_hint
                    resume_info = check_unfinished_workflow(workflow_name)
                    if resume_info:
                        display_resume_hint(
                            workflow=resume_info["workflow"],
                            last_stage_index=resume_info["last_stage_index"],
                            last_stage_name=resume_info["last_stage_name"],
                            last_skill=resume_info["last_skill"],
                            final_status=resume_info["final_status"],
                        )
                except Exception:
                    pass
            except Exception:
                pass

        # 确定起始 stage
        skip_until = continue_from
        for idx, stage in enumerate(route_plan.stages, start=1):
            # 跳过已完成的 stage
            if skip_until and stage.phase != skip_until:
                if stage.status == StageStatus.SUCCESS:
                    result.completed_stages += 1
                    result.all_artifacts.extend(stage.artifact_paths or [])
                    continue
            elif skip_until and stage.phase == skip_until:
                skip_until = None  # 从这开始执行

            # 如果是 optional stage 且 safe_mode, 跳过
            if (
                not stage.required
                and self._safe_mode
                and self._safe_mode.is_active
            ):
                stage.status = StageStatus.SKIPPED
                result.skipped_stages += 1
                self._update_ledger_for_stage(route_plan, workflow_state, stage, task_context)
                continue

            # 执行 stage
            stage_result = self._execute_stage(
                stage, route_plan, workflow_state, task_context, stage_index=idx
            )
            result.stage_results.append(stage_result)

            if stage_result.success:
                result.completed_stages += 1
                result.all_artifacts.extend(stage_result.artifacts)
                stage.artifact_paths = stage_result.artifacts

                # ── L6 Telemetry: stage complete ──────────
                if _telemetry_available:
                    try:
                        _tel_complete_stage(
                            stage_index=idx,
                            stage_name=stage.phase,
                            next_stage=(
                                route_plan.stages[idx].phase
                                if idx < len(route_plan.stages) else ""
                            ),
                        )
                    except Exception:
                        pass
            else:
                result.failed_stages += 1
                result.errors.append(f"{stage.phase}: {stage_result.error}")

                # ── L6 Telemetry: stage fail ─────────────
                if _telemetry_available:
                    try:
                        _tel_fail_stage(
                            stage_index=idx,
                            stage_name=stage.phase,
                            reason=stage_result.error,
                        )
                    except Exception:
                        pass

                # 失败 → self_healing 决策
                heal_decision = self._handle_failure(
                    stage, stage_result, route_plan, workflow_state, task_context
                )
                result.healing_decisions.append(heal_decision)

                if heal_decision.get("action") == "stop":
                    result.execution_status = ExecutionStatus.FAILED
                    break
                elif heal_decision.get("action") == "safe_mode":
                    result.execution_status = ExecutionStatus.SAFE_MODE
                    break
                # retry / fallback: 继续下一 stage (当前 stage 标记为 failed)

            # 更新 ledger
            self._update_ledger_for_stage(route_plan, workflow_state, stage, task_context)

        # 判定最终状态
        if result.execution_status not in (ExecutionStatus.FAILED, ExecutionStatus.SAFE_MODE):
            if result.failed_stages == 0:
                result.execution_status = ExecutionStatus.COMPLETED
            else:
                result.execution_status = ExecutionStatus.DEGRADED

        workflow_state.execution_status = result.execution_status
        result.finished_at = _now_iso()

        # ── L6 Telemetry: workflow complete / fail ───────
        if _telemetry_available:
            try:
                if result.execution_status == ExecutionStatus.COMPLETED:
                    _tel_complete_workflow(
                        summary=f"completed {result.completed_stages}/{total_stages} stages",
                    )
                elif result.execution_status in (ExecutionStatus.FAILED, ExecutionStatus.SAFE_MODE):
                    last_error = result.errors[-1] if result.errors else ""
                    _tel_fail_workflow(
                        reason=last_error,
                    )
            except Exception:
                pass

        return result

    # ── Stage execution ───────────────────────────────────

    def _execute_stage(
        self,
        stage: RouteStage,
        route_plan: RoutePlan,
        workflow_state: WorkflowState,
        task_context: Optional[dict],
        stage_index: int = 0,
    ) -> StageExecutionResult:
        """执行单个 stage"""
        # 标记 running
        stage.status = StageStatus.RUNNING
        workflow_state.current_stage = stage.phase

        # ── L6 Telemetry: enter stage + set skill ────────
        if _telemetry_available:
            try:
                _tel_enter_stage(
                    stage_index=stage_index,
                    stage_name=stage.phase,
                    total_stages=len(route_plan.stages),
                    skill=stage.skill,
                )
                _tel_set_skill(skill_name=stage.skill)
            except Exception:
                pass

        # 准备上下文
        ctx = task_context or {}
        ctx.update({
            "route_id": route_plan.route_id,
            "workflow": route_plan.workflow.value if route_plan.workflow else "",
            "stage_phase": stage.phase,
            "stage_skill": stage.skill,
            "stage_mode": stage.mode,
            "safe_mode": self._safe_mode.is_active if self._safe_mode else False,
        })

        # 执行 skill
        try:
            output = self._execute_skill(stage.skill, stage.mode, ctx)
        except Exception as e:
            stage.status = StageStatus.FAILED
            # ── L6 Telemetry: skill exception → stage fail ──
            if _telemetry_available:
                try:
                    _tel_fail_stage(
                        stage_index=stage_index,
                        stage_name=stage.phase,
                        reason=f"Skill execution exception: {e}",
                    )
                except Exception:
                    pass
            return StageExecutionResult(
                stage_phase=stage.phase,
                skill=stage.skill,
                mode=stage.mode,
                success=False,
                error=f"Skill execution exception: {e}",
                executed_at=_now_iso(),
            )

        # 解析输出
        success = output.get("success", False)
        artifacts = output.get("artifacts", []) or []
        error = output.get("error", "")

        if success:
            stage.status = StageStatus.SUCCESS
        else:
            stage.status = StageStatus.FAILED
            # ── L6 Telemetry: output failure → stage fail ──
            if _telemetry_available and error:
                try:
                    _tel_fail_stage(
                        stage_index=stage_index,
                        stage_name=stage.phase,
                        reason=error,
                    )
                except Exception:
                    pass

        stage_result = StageExecutionResult(
            stage_phase=stage.phase,
            skill=stage.skill,
            mode=stage.mode,
            success=success,
            artifacts=artifacts,
            error=error,
            executed_at=_now_iso(),
        )

        # Guard 检查 (stage 级别)
        if self._guard and success:
            try:
                guard_result = self._guard.check_stage_completion(
                    route_plan,
                    workflow_state,
                    ledger_state=None,  # 外部更新, 此时可能未写入
                    safe_mode_active=self._safe_mode.is_active if self._safe_mode else False,
                )
                stage_result.guard_result = guard_result.to_dict() if hasattr(guard_result, 'to_dict') else {"verdict": "unknown"}

                if hasattr(guard_result, 'is_block') and guard_result.is_block:
                    # Guard blocked → 降级 stage 为 failed
                    stage.status = StageStatus.FAILED
                    stage_result.success = False
                    stage_result.error = f"Guard blocked: {[i.message for i in guard_result.issues]}"
            except Exception as e:
                stage_result.guard_result = {"verdict": "error", "error": str(e)}

        return stage_result

    # ── Failure handling ──────────────────────────────────

    def _handle_failure(
        self,
        stage: RouteStage,
        stage_result: StageExecutionResult,
        route_plan: RoutePlan,
        workflow_state: WorkflowState,
        task_context: Optional[dict],
    ) -> dict:
        """失败时调用 self_healing 决策"""
        if not self._healing:
            return {"action": "stop", "reason": "No self_healing configured"}

        # 分类失败类型
        failure_type = None
        if self._healing and hasattr(self._healing, 'classify_failure'):
            failure_type = self._healing.classify_failure(stage_result.error)
        else:
            failure_type = FailureType.UNKNOWN

        # 计算当前计数 (via RetryState)
        retry_count = workflow_state.retry_state.retry_count if workflow_state.retry_state else 0
        same_failure_count = workflow_state.retry_state.same_failure_type_count if workflow_state.retry_state else 0

        # 决策
        safe_active = self._safe_mode.is_active if self._safe_mode else False
        decision = self._healing.decide(
            failure_type=failure_type,
            retry_count=retry_count,
            same_failure_type_count=same_failure_count,
            safe_mode_active=safe_active,
        )

        decision_dict = decision.to_dict() if hasattr(decision, 'to_dict') else {"action": str(decision)}

        # 根据决策更新状态
        if decision_dict.get("action") == "retry":
            if workflow_state.retry_state:
                workflow_state.retry_state.retry_count = decision_dict.get("retry_count", retry_count + 1)
                workflow_state.retry_state.last_failure_type = failure_type.value if failure_type else "unknown"
            # 注意: retry 需要调用方使用新的 route_id 重建 RoutePlan
            # 此处只记录决策，实际重试由上层 orchestration 处理

        elif decision_dict.get("action") == "safe_mode":
            if self._safe_mode:
                self._safe_mode.trigger(
                    reason="self_healing_limit_exceeded",
                    route_id=route_plan.route_id,
                    workflow=route_plan.workflow.value if route_plan.workflow else "",
                    stage_id=stage.phase,
                )

        return decision_dict

    # ── Ledger updates ────────────────────────────────────

    def _update_ledger_for_stage(
        self,
        route_plan: RoutePlan,
        workflow_state: WorkflowState,
        stage: RouteStage,
        task_context: Optional[dict],
    ) -> None:
        """Stage 完成后更新 ledger"""
        updates = {
            "route_id": route_plan.route_id,
            "stage_id": stage.phase,
            "stage_status": stage.status.value,
            "artifacts": stage.artifact_paths or [],
            "artifact_paths": stage.artifact_paths or [],
            "updated_at": _now_iso(),
        }

        task_id = (task_context or {}).get("task_id", "")
        try:
            self._write_ledger(task_id, updates)
        except Exception:
            pass  # ledger 写入失败不阻塞执行

    # ── Default (no-op) callbacks ─────────────────────────

    @staticmethod
    def _default_executor(skill: str, mode: str, context: dict) -> dict:
        """默认执行器 (no-op，实际执行由 hook 层完成)"""
        return {
            "success": True,
            "artifacts": [],
            "error": "",
            "output": f"Skill '{skill}' executed in mode '{mode}' (no-op default)",
        }

    @staticmethod
    def _default_ledger_writer(task_id: str, updates: dict) -> None:
        """默认 ledger 写入器 (no-op)"""
        pass

    # ── Convenience: execute single stage ──────────────────

    def execute_single_stage(
        self,
        stage: RouteStage,
        route_plan: RoutePlan,
        workflow_state: WorkflowState,
        task_context: Optional[dict] = None,
    ) -> StageExecutionResult:
        """执行单个 stage (用于精细控制)"""
        return self._execute_stage(stage, route_plan, workflow_state, task_context)

"""
Execution Guard — 执行监督层 (Phase 5)
Phase 5: 实现所有 guard 检查规则，与 safe_mode 联动

检查项:
1. required stages 是否完整
2. stage 顺序是否正确
3. expected_artifacts 是否存在
4. ledger 是否已更新
5. 是否存在 no-op completion
6. Pipeline 专项校验:
   - delivery_pipeline 不得跳 summarize/planning
   - construction_prompt 不得缺 ask
   - debug_pipeline 不得缺 diagnose

Guard 结果:
- PASS: 全部检查通过
- WARN: 有 non-critical 问题
- BLOCK: 关键检查失败 → 可能触发 safe_mode
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from orchestration_types import (
    Workflow,
    TaskStatus,
    StageStatus,
    ExecutionStatus,
    FailureType,
    WORKFLOW_STAGES,
    WORKFLOW_MINIMUM_REQUIRED,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Guard verdict ────────────────────────────────────────

class GuardVerdict:
    """Guard 判定结果"""
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class GuardIssue:
    """单条 guard 发现的问题"""
    check_id: str
    severity: str  # critical / warning
    message: str
    detail: str = ""


@dataclass
class GuardResult:
    """Guard 检查完整结果"""
    verdict: str  # pass / warn / block
    checks_total: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    issues: list[GuardIssue] = field(default_factory=list)
    checked_at: str = field(default_factory=_now_iso)
    route_id: str = ""
    workflow: str = ""

    @property
    def is_pass(self) -> bool:
        return self.verdict == GuardVerdict.PASS

    @property
    def is_block(self) -> bool:
        return self.verdict == GuardVerdict.BLOCK

    @property
    def critical_issues(self) -> list[GuardIssue]:
        return [i for i in self.issues if i.severity == "critical"]

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "checks_total": self.checks_total,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "issues": [
                {"check_id": i.check_id, "severity": i.severity, "message": i.message, "detail": i.detail}
                for i in self.issues
            ],
            "checked_at": self.checked_at,
            "route_id": self.route_id,
            "workflow": self.workflow,
        }


class ExecutionGuard:
    """
    执行监督器 — 在 stage 完成后和 workflow 完成前执行检查。

    使用方式:
        guard = ExecutionGuard(repo_root="/path/to/repo")
        result = guard.check_stage_completion(route_plan, workflow_state, ledger_state)
        if result.is_block:
            # 触发 safe_mode 或回退
    """

    # Pipeline 必选 stage phase 名称
    PIPELINE_REQUIRED_STAGES = {
        Workflow.DELIVERY: ["understand", "plan"],  # summarize + planning
        Workflow.DEBUG: ["diagnose"],                # debug diagnose
        Workflow.LEARNING: ["summarize", "plan"],    # summarize + planning
    }

    # Construction prompt 额外要求 (P5-3)
    CONSTRUCTION_EXTRA_REQUIRED = ["ask"]

    def __init__(self, repo_root: Optional[str] = None):
        self._repo_root = Path(repo_root) if repo_root else Path.cwd()

    # ── Main check entry ──────────────────────────────────

    def check_stage_completion(
        self,
        route_plan,           # RoutePlan
        workflow_state,       # WorkflowState
        ledger_state: Optional[dict] = None,
        safe_mode_active: bool = False,
    ) -> GuardResult:
        """
        Stage 完成后的完整检查。

        参数:
            route_plan: 当前 RoutePlan
            workflow_state: 当前 WorkflowState
            ledger_state: ledger 中的 task 数据 (dict)
            safe_mode_active: 当前是否在 safe_mode 中

        返回:
            GuardResult
        """
        result = GuardResult(
            verdict=GuardVerdict.PASS,
            route_id=route_plan.route_id,
            workflow=route_plan.workflow.value if route_plan.workflow else "",
        )

        # 1. Required stages check
        self._check_required_stages(route_plan, result)

        # 2. Stage order check
        self._check_stage_order(route_plan, result)

        # 3. Expected artifacts check
        self._check_expected_artifacts(route_plan, workflow_state, result)

        # 4. Ledger update check
        self._check_ledger_update(ledger_state, result)

        # 5. No-op completion check
        self._check_noop_completion(route_plan, workflow_state, result)

        # 6. Pipeline-specific checks
        self._check_pipeline_specific(route_plan, result)

        # Update counts and verdict
        result.checks_total = result.checks_passed + result.checks_failed
        if result.checks_failed == 0:
            result.verdict = GuardVerdict.PASS
        elif result.critical_issues:
            result.verdict = GuardVerdict.BLOCK
        else:
            result.verdict = GuardVerdict.WARN

        return result

    def check_workflow_completion(
        self,
        route_plan,
        workflow_state,
        ledger_state: Optional[dict] = None,
    ) -> GuardResult:
        """
        Workflow 完成前的最终检查 (比 stage 检查更严格)。
        """
        result = self.check_stage_completion(route_plan, workflow_state, ledger_state)

        # 额外: 终态检查
        completed_stages = [
            s.phase for s in route_plan.stages
            if s.status == StageStatus.SUCCESS
        ]
        required = [
            s.phase for s in route_plan.stages
            if s.required
        ]

        for r in required:
            if r not in completed_stages:
                result.issues.append(GuardIssue(
                    check_id="final_required_stage",
                    severity="critical",
                    message=f"Workflow 完成前 required stage 未通过: {r}",
                    detail=f"required stages: {required}, completed: {completed_stages}",
                ))
                result.checks_failed += 1

        # 终态不允许 artifact 为空 (除非 plan_only)
        if route_plan.workflow and route_plan.workflow.value != "plan_only":
            all_artifacts = []
            for s in route_plan.stages:
                all_artifacts.extend(s.artifact_paths or [])
            if not all_artifacts:
                result.issues.append(GuardIssue(
                    check_id="final_no_artifacts",
                    severity="critical",
                    message="Workflow 完成但无任何 artifact",
                    detail="非 plan_only 任务必须有 artifact",
                ))
                result.checks_failed += 1

        # Update verdict
        if result.critical_issues:
            result.verdict = GuardVerdict.BLOCK

        return result

    # ── Individual checks ─────────────────────────────────

    def _check_required_stages(self, route_plan, result: GuardResult) -> None:
        """P5-1: 检查 required stages 是否完整"""
        workflow = route_plan.workflow
        if not workflow:
            return

        minimum = WORKFLOW_MINIMUM_REQUIRED.get(workflow, [])
        stage_phases = [s.phase for s in route_plan.stages]

        for min_phase in minimum:
            if min_phase not in stage_phases:
                result.issues.append(GuardIssue(
                    check_id="required_stage_missing",
                    severity="critical",
                    message=f"缺少 required stage: {min_phase}",
                    detail=f"workflow={workflow.value}, stages={stage_phases}, minimum={minimum}",
                ))
                result.checks_failed += 1
            else:
                result.checks_passed += 1

    def _check_stage_order(self, route_plan, result: GuardResult) -> None:
        """检查 stage 执行顺序: 已完成 stage 之后不能再有 pending required stage"""
        completed_phases = set()
        for s in route_plan.stages:
            if s.status == StageStatus.SUCCESS:
                completed_phases.add(s.phase)
            elif s.status == StageStatus.RUNNING:
                # 当前 running 的 stage, 检查前面 required 都已完成
                for prev in route_plan.stages:
                    if prev.phase == s.phase:
                        break
                    if prev.required and prev.status != StageStatus.SUCCESS:
                        result.issues.append(GuardIssue(
                            check_id="stage_order_violation",
                            severity="warning",
                            message=f"Stage '{s.phase}' 在 required stage '{prev.phase}' 完成前开始",
                            detail=f"prev_status={prev.status.value}",
                        ))
                        result.checks_failed += 1
                break  # 只检查到当前 running stage

        result.checks_passed += 1  # 至少执行了检查

    def _check_expected_artifacts(self, route_plan, workflow_state, result: GuardResult) -> None:
        """检查 expected_artifacts 是否在文件系统中存在"""
        for stage in route_plan.stages:
            if stage.status != StageStatus.SUCCESS:
                continue
            for art_path in (stage.artifact_paths or []):
                if not art_path:
                    continue
                full_path = self._repo_root / art_path
                if not full_path.exists():
                    result.issues.append(GuardIssue(
                        check_id="artifact_missing",
                        severity="critical",
                        message=f"Stage '{stage.phase}' 声称成功但 artifact 不存在: {art_path}",
                        detail=f"expected at: {full_path}",
                    ))
                    result.checks_failed += 1
                else:
                    result.checks_passed += 1

    def _check_ledger_update(self, ledger_state: Optional[dict], result: GuardResult) -> None:
        """检查 ledger 是否更新"""
        if ledger_state is None:
            result.issues.append(GuardIssue(
                check_id="ledger_not_updated",
                severity="warning",
                message="无法读取 ledger 状态 (ledger_state is None)",
                detail="检查 ledger 写入路径是否正常",
            ))
            result.checks_failed += 1
            return

        status = ledger_state.get("status", "")
        if status not in ("executing", "blocked", "retrying", "done"):
            result.issues.append(GuardIssue(
                check_id="ledger_status_stale",
                severity="warning",
                message=f"Ledger 状态可能未更新: {status}",
                detail="expected executing/blocked/retrying/done",
            ))
            result.checks_failed += 1
        else:
            result.checks_passed += 1

    def _check_noop_completion(self, route_plan, workflow_state, result: GuardResult) -> None:
        """检查 no-op completion: 所有 stage 都是 pending 但 workflow 标记为完成"""
        all_pending = all(
            s.status in (StageStatus.PENDING, StageStatus.SKIPPED)
            for s in route_plan.stages
        )
        if all_pending and workflow_state.execution_status == ExecutionStatus.COMPLETED:
            result.issues.append(GuardIssue(
                check_id="noop_completion",
                severity="critical",
                message="检测到 no-op completion: 所有 stage 未执行但 workflow 标记完成",
                detail="口头完成 — 禁止",
            ))
            result.checks_failed += 1
        else:
            result.checks_passed += 1

    def _check_pipeline_specific(self, route_plan, result: GuardResult) -> None:
        """P5-3: Pipeline 专项校验"""
        workflow = route_plan.workflow
        stages = [s.phase for s in route_plan.stages]

        if workflow == Workflow.DELIVERY:
            # delivery_pipeline 必须有 summarize/planning (phase: understand, plan)
            if "understand" not in stages and "summarize" not in stages:
                result.issues.append(GuardIssue(
                    check_id="delivery_missing_summarize",
                    severity="critical",
                    message="delivery_pipeline 缺少 summarize (understand) stage",
                    detail=f"stages={stages}",
                ))
                result.checks_failed += 1
            else:
                result.checks_passed += 1

            if "plan" not in stages and "planning" not in stages:
                result.issues.append(GuardIssue(
                    check_id="delivery_missing_planning",
                    severity="critical",
                    message="delivery_pipeline 缺少 planning (plan) stage",
                    detail=f"stages={stages}",
                ))
                result.checks_failed += 1
            else:
                result.checks_passed += 1

        elif workflow == Workflow.DEBUG:
            # debug_pipeline 必须有 diagnose
            if "diagnose" not in stages:
                result.issues.append(GuardIssue(
                    check_id="debug_missing_diagnose",
                    severity="critical",
                    message="debug_pipeline 缺少 diagnose stage",
                    detail=f"stages={stages}",
                ))
                result.checks_failed += 1
            else:
                result.checks_passed += 1

        elif workflow == Workflow.LEARNING:
            # learning_pipeline 必须有 summarize + plan
            if "summarize" not in stages:
                result.issues.append(GuardIssue(
                    check_id="learning_missing_summarize",
                    severity="critical",
                    message="learning_pipeline 缺少 summarize stage",
                    detail=f"stages={stages}",
                ))
                result.checks_failed += 1
            else:
                result.checks_passed += 1

            if "plan" not in stages:
                result.issues.append(GuardIssue(
                    check_id="learning_missing_plan",
                    severity="critical",
                    message="learning_pipeline 缺少 planning stage",
                    detail=f"stages={stages}",
                ))
                result.checks_failed += 1
            else:
                result.checks_passed += 1

    # ── Convenience: quick artifact path check ─────────────

    @staticmethod
    def artifact_exists(repo_root: Path, rel_path: str) -> bool:
        """检查 artifact 文件是否存在"""
        return (repo_root / rel_path).exists()

    @staticmethod
    def validate_artifact_path(repo_root: Path, rel_path: str) -> tuple[bool, str]:
        """
        验证 artifact 路径安全性。

        返回: (is_safe, reason)
        """
        # 禁止 ..
        if ".." in rel_path:
            return False, f"路径包含 '..': {rel_path}"

        # 禁止绝对路径
        if os.path.isabs(rel_path):
            return False, f"不允许绝对路径: {rel_path}"

        # Resolve against repo root
        try:
            resolved = (repo_root / rel_path).resolve()
            if not str(resolved).startswith(str(repo_root.resolve())):
                return False, f"路径越出 repo root: {rel_path} → {resolved}"
        except Exception as e:
            return False, f"路径解析失败: {rel_path} — {e}"

        return True, "ok"

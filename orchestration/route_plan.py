"""
RoutePlan — 核心路由计划数据结构
Phase 2: 固定系统"怎么描述工作流"

RoutePlan 是整个编排系统的核心数据结构：
- workflow-resolver 输出 RoutePlan
- skill-router 按 RoutePlan 执行
- execution_guard 按 RoutePlan 检查

只做数据结构 + 验证，不做路由决策（那是 Phase 4 的事）。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from orchestration_types import (
    Intent,
    Workflow,
    StageStatus,
    ExecutionStatus,
    SafeModeStatus,
)


def _new_route_id() -> str:
    """生成唯一 route_id"""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"rte_{ts}_{short_uuid}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── GuardPolicy ────────────────────────────────────────

@dataclass
class GuardPolicy:
    """
    RoutePlan 关联的 guard 策略。
    定义该 route 需要什么检查、多严格。
    """
    # 必检项
    check_required_stages: bool = True
    check_stage_order: bool = True
    check_expected_artifacts: bool = True
    check_ledger_updated: bool = True
    check_no_op_completion: bool = True

    # Pipeline 专项
    enforce_delivery_plan: bool = True       # delivery 不得跳 summarize/planning
    enforce_construction_ask: bool = True    # construction prompt 不得缺 ask
    enforce_debug_diagnose: bool = True      # debug 不得缺 diagnose

    # 宽松度
    allow_partial_artifacts: bool = False
    skip_optional_stages: bool = True

    def to_dict(self) -> dict:
        return {
            "check_required_stages": self.check_required_stages,
            "check_stage_order": self.check_stage_order,
            "check_expected_artifacts": self.check_expected_artifacts,
            "check_ledger_updated": self.check_ledger_updated,
            "check_no_op_completion": self.check_no_op_completion,
            "enforce_delivery_plan": self.enforce_delivery_plan,
            "enforce_construction_ask": self.enforce_construction_ask,
            "enforce_debug_diagnose": self.enforce_debug_diagnose,
            "allow_partial_artifacts": self.allow_partial_artifacts,
            "skip_optional_stages": self.skip_optional_stages,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GuardPolicy":
        return cls(
            check_required_stages=d.get("check_required_stages", True),
            check_stage_order=d.get("check_stage_order", True),
            check_expected_artifacts=d.get("check_expected_artifacts", True),
            check_ledger_updated=d.get("check_ledger_updated", True),
            check_no_op_completion=d.get("check_no_op_completion", True),
            enforce_delivery_plan=d.get("enforce_delivery_plan", True),
            enforce_construction_ask=d.get("enforce_construction_ask", True),
            enforce_debug_diagnose=d.get("enforce_debug_diagnose", True),
            allow_partial_artifacts=d.get("allow_partial_artifacts", False),
            skip_optional_stages=d.get("skip_optional_stages", True),
        )

    @classmethod
    def strict(cls) -> "GuardPolicy":
        """严格模式 — 所有检查全开"""
        return cls()

    @classmethod
    def lenient(cls) -> "GuardPolicy":
        """宽松模式 — SAFE MODE 下使用"""
        return cls(
            check_expected_artifacts=False,
            enforce_delivery_plan=False,
            enforce_construction_ask=False,
            enforce_debug_diagnose=False,
            allow_partial_artifacts=True,
        )

    @classmethod
    def safe_mode_policy(cls) -> "GuardPolicy":
        """SAFE MODE 策略 — 最宽松，仅检查基本结构"""
        return cls(
            check_required_stages=True,
            check_stage_order=False,
            check_expected_artifacts=False,
            check_ledger_updated=False,
            check_no_op_completion=False,
            enforce_delivery_plan=False,
            enforce_construction_ask=False,
            enforce_debug_diagnose=False,
            allow_partial_artifacts=True,
        )


# ── RouteStage ─────────────────────────────────────────

@dataclass
class RouteStage:
    """
    RoutePlan 中的一个执行阶段。
    对应 workflow 中一个 phase → skill 的映射。
    """
    stage_id: str                            # 唯一 stage ID，如 "stg_001_understand"
    phase: str                               # 阶段名，如 "understand", "plan", "diagnose"
    skill: str                               # 技能名，如 "summarize", "planning", "debug"
    mode: str                                # 技能模式，如 "briefing", "project", "full"
    required: bool = True                    # 是否必须执行
    status: StageStatus = StageStatus.PENDING
    expected_output: str = ""                # 预期产出描述
    artifact_paths: list[str] = field(default_factory=list)  # 产物路径（repo-root 相对路径）

    # 执行追踪
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

    def mark_running(self):
        self.status = StageStatus.RUNNING
        self.started_at = _now_iso()

    def mark_success(self, artifacts: Optional[list[str]] = None):
        self.status = StageStatus.SUCCESS
        self.completed_at = _now_iso()
        if artifacts:
            self.artifact_paths = artifacts

    def mark_failed(self, error: str):
        self.status = StageStatus.FAILED
        self.completed_at = _now_iso()
        self.error_message = error

    def mark_skipped(self, reason: str = ""):
        self.status = StageStatus.SKIPPED
        self.error_message = reason

    def to_dict(self) -> dict:
        return {
            "stage_id": self.stage_id,
            "phase": self.phase,
            "skill": self.skill,
            "mode": self.mode,
            "required": self.required,
            "status": self.status.value,
            "expected_output": self.expected_output,
            "artifact_paths": self.artifact_paths,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RouteStage":
        return cls(
            stage_id=d["stage_id"],
            phase=d["phase"],
            skill=d["skill"],
            mode=d.get("mode", "default"),
            required=d.get("required", True),
            status=StageStatus(d.get("status", "pending")),
            expected_output=d.get("expected_output", ""),
            artifact_paths=d.get("artifact_paths", []),
            started_at=d.get("started_at"),
            completed_at=d.get("completed_at"),
            error_message=d.get("error_message"),
        )


# ── RoutePlan ──────────────────────────────────────────

@dataclass
class RoutePlan:
    """
    一次完整的路由决策 + 执行计划。

    职责边界：
    - workflow-resolver 负责创建和填充 RoutePlan
    - skill-router 负责按 RoutePlan.stages 顺序执行
    - execution_guard 负责验证 RoutePlan 的执行结果

    RoutePlan 一旦创建，禁止 skill-router 重新路由。
    """
    route_id: str                            # 唯一 route ID
    workflow: Workflow                       # 工作流
    intent: Intent                           # 用户意图
    confidence: float                        # 置信度 0.0 ~ 1.0
    stages: list[RouteStage] = field(default_factory=list)
    guard_policy: GuardPolicy = field(default_factory=GuardPolicy)

    # 元信息
    normalized_input: str = ""               # 标准化后的用户输入
    safe_mode: SafeModeStatus = SafeModeStatus.INACTIVE
    retry_count: int = 0
    route_source: str = ""                   # "rule" | "semantic" | "fallback" | "resolver"

    # 汇总产物（所有 stage 的 artifact_paths 汇聚）
    expected_artifacts: list[str] = field(default_factory=list)
    collected_artifacts: list[str] = field(default_factory=list)

    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def __post_init__(self):
        if not self.route_id:
            self.route_id = _new_route_id()

    # ── Stage 操作 ──

    @property
    def current_stage_index(self) -> int:
        """返回第一个未完成的 stage 索引，-1 表示全部完成"""
        for i, s in enumerate(self.stages):
            if s.status in (StageStatus.PENDING, StageStatus.RUNNING):
                return i
        return -1

    @property
    def current_stage(self) -> Optional[RouteStage]:
        idx = self.current_stage_index
        if idx >= 0:
            return self.stages[idx]
        return None

    @property
    def required_stages(self) -> list[RouteStage]:
        return [s for s in self.stages if s.required]

    @property
    def completed_required_stages(self) -> list[RouteStage]:
        return [s for s in self.required_stages if s.status == StageStatus.SUCCESS]

    @property
    def all_required_completed(self) -> bool:
        return len(self.completed_required_stages) == len(self.required_stages)

    @property
    def any_failed(self) -> bool:
        return any(s.status == StageStatus.FAILED for s in self.stages)

    def get_stage_by_phase(self, phase: str) -> Optional[RouteStage]:
        for s in self.stages:
            if s.phase == phase:
                return s
        return None

    def collect_artifacts(self) -> list[str]:
        """收集所有 stage 的 artifact_paths"""
        artifacts = []
        for s in self.stages:
            artifacts.extend(s.artifact_paths)
        self.collected_artifacts = artifacts
        return artifacts

    # ── 验证 ──

    def validate(self) -> list[str]:
        """验证 RoutePlan 结构完整性，返回问题列表"""
        issues = []

        if not self.route_id:
            issues.append("route_id 缺失")
        if not self.stages:
            issues.append("stages 为空")
        if self.confidence < 0 or self.confidence > 1:
            issues.append(f"confidence 越界: {self.confidence}")

        # 检查必选 stages
        required_phases = set()
        for s in self.stages:
            if s.required:
                required_phases.add(s.phase)

        # delivery 必须包含 summarize + planning
        if self.workflow == Workflow.DELIVERY and self.guard_policy.enforce_delivery_plan:
            if "understand" not in required_phases and "summarize" not in required_phases:
                # 检查是否有 summarize 阶段的 phase
                has_summarize = any(
                    s.skill == "summarize" and s.required for s in self.stages
                )
                if not has_summarize:
                    issues.append("delivery_pipeline 缺少 summarize 阶段")

            has_planning = any(
                s.skill == "planning" and s.required for s in self.stages
            )
            if not has_planning:
                issues.append("delivery_pipeline 缺少 planning 阶段")

        # debug 必须包含 diagnose
        if self.workflow == Workflow.DEBUG and self.guard_policy.enforce_debug_diagnose:
            has_diagnose = any(s.phase == "diagnose" and s.required for s in self.stages)
            if not has_diagnose:
                issues.append("debug_pipeline 缺少 diagnose 阶段")

        return issues

    # ── 序列化 ──

    def to_dict(self) -> dict:
        return {
            "route_id": self.route_id,
            "workflow": self.workflow.value,
            "intent": self.intent.value,
            "confidence": self.confidence,
            "stages": [s.to_dict() for s in self.stages],
            "guard_policy": self.guard_policy.to_dict(),
            "normalized_input": self.normalized_input,
            "safe_mode": self.safe_mode.value,
            "retry_count": self.retry_count,
            "route_source": self.route_source,
            "expected_artifacts": self.expected_artifacts,
            "collected_artifacts": self.collected_artifacts,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RoutePlan":
        return cls(
            route_id=d["route_id"],
            workflow=Workflow(d["workflow"]),
            intent=Intent(d["intent"]),
            confidence=d.get("confidence", 0.0),
            stages=[RouteStage.from_dict(s) for s in d.get("stages", [])],
            guard_policy=GuardPolicy.from_dict(d.get("guard_policy", {})),
            normalized_input=d.get("normalized_input", ""),
            safe_mode=SafeModeStatus(d.get("safe_mode", "inactive")),
            retry_count=d.get("retry_count", 0),
            route_source=d.get("route_source", ""),
            expected_artifacts=d.get("expected_artifacts", []),
            collected_artifacts=d.get("collected_artifacts", []),
            created_at=d.get("created_at", _now_iso()),
            updated_at=d.get("updated_at", _now_iso()),
        )


# ── Factory helpers ─────────────────────────────────────

def create_route_plan(
    workflow: Workflow,
    intent: Intent,
    confidence: float,
    stages_data: list[dict],
    normalized_input: str = "",
    route_source: str = "",
) -> RoutePlan:
    """从 workflow 模板数据创建 RoutePlan"""
    stages = []
    for i, sd in enumerate(stages_data):
        stage = RouteStage(
            stage_id=f"stg_{i:03d}_{sd.get('phase', 'unknown')}",
            phase=sd.get("phase", ""),
            skill=sd.get("skill", ""),
            mode=sd.get("mode", "default"),
            required=sd.get("required", True),
            expected_output=sd.get("output", ""),
        )
        stages.append(stage)

    return RoutePlan(
        route_id="",
        workflow=workflow,
        intent=intent,
        confidence=confidence,
        stages=stages,
        normalized_input=normalized_input,
        route_source=route_source,
        expected_artifacts=[s.expected_output for s in stages if s.expected_output],
    )


def create_route_plan_from_template(
    workflow: Workflow,
    intent: Intent,
    confidence: float,
    normalized_input: str = "",
    route_source: str = "",
) -> RoutePlan:
    """
    从 WORKFLOW_STAGES 模板创建 RoutePlan。
    仅用于 Phase 2 测试和 rule-router 的快速创建。
    """
    from orchestration_types import WORKFLOW_STAGES

    template_stages = WORKFLOW_STAGES.get(workflow, [])
    return create_route_plan(
        workflow=workflow,
        intent=intent,
        confidence=confidence,
        stages_data=template_stages,
        normalized_input=normalized_input,
        route_source=route_source,
    )

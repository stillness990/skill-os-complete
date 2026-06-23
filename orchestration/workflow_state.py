"""
WorkflowState — workflow 运行时状态追踪
Phase 2: 固定系统"怎么追踪执行进度"

WorkflowState 是 workflow-resolver 和 skill-router 之间的共享运行时状态：
- resolver 创建初始 WorkflowState
- skill-router 在执行每个 stage 后更新 WorkflowState
- execution_guard 读取 WorkflowState 进行检查

只做数据结构 + 序列化，不做执行逻辑（Phase 5）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .orchestration_types import (
    Intent,
    Workflow,
    StageStatus,
    ExecutionStatus,
    SafeModeStatus,
    FailureType,
    RouteSource,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RetryState:
    """重试状态"""
    retry_count: int = 0
    max_retries: int = 3
    same_failure_type_count: int = 0
    max_same_failure: int = 2
    last_failure_type: Optional[FailureType] = None
    last_failure_at: Optional[str] = None
    retry_route_ids: list[str] = field(default_factory=list)

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def can_retry_same_type(self) -> bool:
        return self.same_failure_type_count < self.max_same_failure

    def record_failure(self, failure_type: FailureType) -> None:
        """记录一次失败"""
        self.retry_count += 1
        self.last_failure_at = _now_iso()
        if self.last_failure_type == failure_type:
            self.same_failure_type_count += 1
        else:
            self.last_failure_type = failure_type
            self.same_failure_type_count = 1

    def is_embedding_fail(self) -> bool:
        """检查是否为 embedding 故障"""
        return self.last_failure_type == FailureType.EMBEDDING_UNAVAILABLE

    def should_immediate_fallback(self) -> bool:
        """embedding 故障 → 立即 fallback"""
        return self.is_embedding_fail()

    def to_dict(self) -> dict:
        return {
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "same_failure_type_count": self.same_failure_type_count,
            "max_same_failure": self.max_same_failure,
            "last_failure_type": self.last_failure_type.value if self.last_failure_type else None,
            "last_failure_at": self.last_failure_at,
            "retry_route_ids": self.retry_route_ids,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RetryState":
        ft = d.get("last_failure_type")
        return cls(
            retry_count=d.get("retry_count", 0),
            max_retries=d.get("max_retries", 3),
            same_failure_type_count=d.get("same_failure_type_count", 0),
            max_same_failure=d.get("max_same_failure", 2),
            last_failure_type=FailureType(ft) if ft else None,
            last_failure_at=d.get("last_failure_at"),
            retry_route_ids=d.get("retry_route_ids", []),
        )


@dataclass
class WorkflowState:
    """
    Workflow 级别的运行时状态。
    跟踪当前执行到哪个 route 的哪个 stage、整体执行状态、SAFE MODE 等。
    """
    # 核心追踪
    current_route_id: Optional[str] = None
    current_workflow: Optional[Workflow] = None
    current_stage_index: int = 0
    execution_status: ExecutionStatus = ExecutionStatus.NOT_STARTED

    # SAFE MODE
    safe_mode: SafeModeStatus = SafeModeStatus.INACTIVE
    safe_mode_trigger_reason: str = ""
    safe_mode_semantic_disabled: bool = False
    safe_mode_self_healing_disabled: bool = False

    # 降级
    degraded: bool = False
    degraded_reason: str = ""
    fallback_used: bool = False

    # 重试
    retry_state: RetryState = field(default_factory=RetryState)

    # Route 历史
    route_history: list[dict] = field(default_factory=list)  # 历史 route 摘要

    # 时间戳
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    # ── 状态操作 ──

    def start_route(self, route_id: str, workflow: Workflow) -> None:
        self.current_route_id = route_id
        self.current_workflow = workflow
        self.current_stage_index = 0
        self.execution_status = ExecutionStatus.IN_PROGRESS
        self.updated_at = _now_iso()

    def advance_stage(self) -> None:
        self.current_stage_index += 1
        self.updated_at = _now_iso()

    def complete(self) -> None:
        self.execution_status = ExecutionStatus.COMPLETED
        self.updated_at = _now_iso()

    def fail(self, reason: str = "") -> None:
        self.execution_status = ExecutionStatus.FAILED
        self.degraded_reason = reason
        self.updated_at = _now_iso()

    def enter_safe_mode(self, trigger_reason: str) -> None:
        """进入 SAFE MODE"""
        self.safe_mode = SafeModeStatus.ACTIVE
        self.safe_mode_trigger_reason = trigger_reason
        self.safe_mode_semantic_disabled = True
        self.safe_mode_self_healing_disabled = True
        self.degraded = True
        self.updated_at = _now_iso()

    def exit_safe_mode(self) -> None:
        """退出 SAFE MODE"""
        self.safe_mode = SafeModeStatus.INACTIVE
        self.safe_mode_semantic_disabled = False
        self.safe_mode_self_healing_disabled = False
        self.degraded = False
        self.updated_at = _now_iso()

    def mark_degraded(self, reason: str) -> None:
        """标记降级运行（如 semantic 不可用）"""
        self.degraded = True
        self.degraded_reason = reason
        self.updated_at = _now_iso()

    def record_route_completion(self, route_summary: dict) -> None:
        """记录完成的 route 到历史"""
        self.route_history.append(route_summary)
        self.updated_at = _now_iso()

    def record_failure(self, failure_type: FailureType, route_id: Optional[str] = None) -> None:
        """记录失败并更新重试状态"""
        self.retry_state.record_failure(failure_type)
        if route_id:
            self.retry_state.retry_route_ids.append(route_id)
        self.updated_at = _now_iso()

    # ── 查询 ──

    @property
    def is_in_safe_mode(self) -> bool:
        return self.safe_mode == SafeModeStatus.ACTIVE

    @property
    def is_degraded(self) -> bool:
        return self.degraded

    @property
    def can_retry(self) -> bool:
        if self.is_in_safe_mode:
            return False  # SAFE MODE 下禁止自愈
        return self.retry_state.can_retry()

    @property
    def needs_fallback(self) -> bool:
        """是否需要降级到 fallback 路由"""
        return self.retry_state.should_immediate_fallback() or self.degraded

    # ── 序列化 ──

    def to_dict(self) -> dict:
        return {
            "current_route_id": self.current_route_id,
            "current_workflow": self.current_workflow.value if self.current_workflow else None,
            "current_stage_index": self.current_stage_index,
            "execution_status": self.execution_status.value,
            "safe_mode": self.safe_mode.value,
            "safe_mode_trigger_reason": self.safe_mode_trigger_reason,
            "safe_mode_semantic_disabled": self.safe_mode_semantic_disabled,
            "safe_mode_self_healing_disabled": self.safe_mode_self_healing_disabled,
            "degraded": self.degraded,
            "degraded_reason": self.degraded_reason,
            "fallback_used": self.fallback_used,
            "retry_state": self.retry_state.to_dict(),
            "route_history": self.route_history,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowState":
        wf = d.get("current_workflow")
        return cls(
            current_route_id=d.get("current_route_id"),
            current_workflow=Workflow(wf) if wf else None,
            current_stage_index=d.get("current_stage_index", 0),
            execution_status=ExecutionStatus(d.get("execution_status", "not_started")),
            safe_mode=SafeModeStatus(d.get("safe_mode", "inactive")),
            safe_mode_trigger_reason=d.get("safe_mode_trigger_reason", ""),
            safe_mode_semantic_disabled=d.get("safe_mode_semantic_disabled", False),
            safe_mode_self_healing_disabled=d.get("safe_mode_self_healing_disabled", False),
            degraded=d.get("degraded", False),
            degraded_reason=d.get("degraded_reason", ""),
            fallback_used=d.get("fallback_used", False),
            retry_state=RetryState.from_dict(d.get("retry_state", {})),
            route_history=d.get("route_history", []),
            created_at=d.get("created_at", _now_iso()),
            updated_at=d.get("updated_at", _now_iso()),
        )


# ── 快速工厂 ──

def create_initial_state() -> WorkflowState:
    """创建初始 WorkflowState"""
    return WorkflowState()

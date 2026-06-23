"""
Ledger Schema — Python 版任务账本数据结构定义
Phase 2: 升级 ledger schema 支持 route/stage/artifact/retry/safe_mode

与 .claude/system/task_ledger/schema.md 保持一致，并提供：
- Python dataclass 定义
- artifact_paths 安全规则验证
- v1 → v4 数据迁移
- 序列化/反序列化
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from orchestration.orchestration_types import (
    TaskStatus,
    TaskType,
    Workflow,
    FailureType,
    SafeModeStatus,
    normalize_v1_status,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── ArtifactRefs ──────────────────────────────────────

@dataclass
class ArtifactRefs:
    """结构化 artifact 引用（供 execution_guard 检查）"""
    plan_ref: Optional[str] = None
    implementation_ref: Optional[str] = None
    debug_report_ref: Optional[str] = None
    fix_ref: Optional[str] = None
    study_plan_ref: Optional[str] = None
    practice_log_ref: Optional[str] = None
    review_log_ref: Optional[str] = None
    changed_files: list[str] = field(default_factory=list)
    changelog_ref: Optional[str] = None
    review_ref: Optional[str] = None
    result_summary: str = ""

    def has_any(self) -> bool:
        """是否有任何 artifact 引用"""
        return bool(
            self.plan_ref or self.implementation_ref or self.debug_report_ref
            or self.fix_ref or self.study_plan_ref or self.practice_log_ref
            or self.review_log_ref or self.changed_files or self.changelog_ref
            or self.review_ref or len(self.result_summary) >= 10
        )

    def to_dict(self) -> dict:
        return {
            "plan_ref": self.plan_ref,
            "implementation_ref": self.implementation_ref,
            "debug_report_ref": self.debug_report_ref,
            "fix_ref": self.fix_ref,
            "study_plan_ref": self.study_plan_ref,
            "practice_log_ref": self.practice_log_ref,
            "review_log_ref": self.review_log_ref,
            "changed_files": self.changed_files,
            "changelog_ref": self.changelog_ref,
            "review_ref": self.review_ref,
            "result_summary": self.result_summary,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ArtifactRefs":
        return cls(
            plan_ref=d.get("plan_ref"),
            implementation_ref=d.get("implementation_ref"),
            debug_report_ref=d.get("debug_report_ref"),
            fix_ref=d.get("fix_ref"),
            study_plan_ref=d.get("study_plan_ref"),
            practice_log_ref=d.get("practice_log_ref"),
            review_log_ref=d.get("review_log_ref"),
            changed_files=d.get("changed_files", []),
            changelog_ref=d.get("changelog_ref"),
            review_ref=d.get("review_ref"),
            result_summary=d.get("result_summary", ""),
        )


# ── GuardStatus ───────────────────────────────────────

@dataclass
class GuardStatus:
    """监督状态（v4 新增）"""
    last_check_at: Optional[str] = None
    stall_detected: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "last_check_at": self.last_check_at,
            "stall_detected": self.stall_detected,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GuardStatus":
        return cls(
            last_check_at=d.get("last_check_at"),
            stall_detected=d.get("stall_detected", False),
            warnings=d.get("warnings", []),
        )


# ── TaskEntry ─────────────────────────────────────────

@dataclass
class TaskEntry:
    """
    v4 任务条目。

    字段覆盖：
    - task_id, title, task_type, workflow, intent
    - status (v4 8 状态)
    - route_id, stage_id, stage_status
    - expected_artifacts, artifact_paths
    - artifact_refs, guard_status
    - retry_count, same_failure_type_count, failure_type
    - next_action, safe_mode
    - created_at, updated_at
    """
    task_id: str
    title: str
    task_type: TaskType = TaskType.DELIVERY
    workflow: Optional[Workflow] = None
    intent: str = ""
    status: TaskStatus = TaskStatus.QUEUED
    source: str = "manual"

    # v4 扩展：route/stage 关联
    route_id: str = ""
    stage_id: str = ""
    stage_status: str = ""

    # Artifacts
    artifacts: list[str] = field(default_factory=list)
    expected_artifacts: list[str] = field(default_factory=list)
    artifact_paths: list[str] = field(default_factory=list)
    artifact_refs: ArtifactRefs = field(default_factory=ArtifactRefs)

    # Guard
    guard_status: GuardStatus = field(default_factory=GuardStatus)

    # Retry / Failure
    retry_count: int = 0
    same_failure_type_count: int = 0
    failure_type: Optional[FailureType] = None
    next_action: str = ""

    # SAFE MODE
    safe_mode: bool = False
    safe_mode_reason: str = ""

    # 学习扩展
    study_mode: str = ""
    topic: str = ""
    source_plan: str = ""
    stage: str = ""
    estimated_minutes: int = 0
    actual_minutes: int = 0

    # 时间戳
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        d = {
            "task_id": self.task_id,
            "title": self.title,
            "task_type": self.task_type.value,
            "workflow": self.workflow.value if self.workflow else None,
            "intent": self.intent,
            "status": self.status.value,
            "source": self.source,
            # v4 route/stage
            "route_id": self.route_id,
            "stage_id": self.stage_id,
            "stage_status": self.stage_status,
            # artifacts
            "artifacts": self.artifacts,
            "expected_artifacts": self.expected_artifacts,
            "artifact_paths": self.artifact_paths,
            "artifact_refs": self.artifact_refs.to_dict(),
            "guard_status": self.guard_status.to_dict(),
            # retry/failure
            "retry_count": self.retry_count,
            "same_failure_type_count": self.same_failure_type_count,
            "failure_type": self.failure_type.value if self.failure_type else None,
            "next_action": self.next_action,
            # safe_mode
            "safe_mode": self.safe_mode,
            "safe_mode_reason": self.safe_mode_reason,
            # timestamps
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        # 学习字段（仅 learning 类型写入）
        if self.task_type == TaskType.LEARNING:
            d.update({
                "study_mode": self.study_mode,
                "topic": self.topic,
                "source_plan": self.source_plan,
                "stage": self.stage,
                "estimated_minutes": self.estimated_minutes,
                "actual_minutes": self.actual_minutes,
            })
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TaskEntry":
        wf = d.get("workflow")
        ft = d.get("failure_type")
        return cls(
            task_id=d["task_id"],
            title=d["title"],
            task_type=TaskType(d.get("task_type", "delivery")),
            workflow=Workflow(wf) if wf else None,
            intent=d.get("intent", ""),
            status=TaskStatus(d.get("status", "queued")),
            source=d.get("source", "manual"),
            route_id=d.get("route_id", ""),
            stage_id=d.get("stage_id", ""),
            stage_status=d.get("stage_status", ""),
            artifacts=d.get("artifacts", []),
            expected_artifacts=d.get("expected_artifacts", []),
            artifact_paths=d.get("artifact_paths", []),
            artifact_refs=ArtifactRefs.from_dict(d.get("artifact_refs", {})),
            guard_status=GuardStatus.from_dict(d.get("guard_status", {})),
            retry_count=d.get("retry_count", 0),
            same_failure_type_count=d.get("same_failure_type_count", 0),
            failure_type=FailureType(ft) if ft else None,
            next_action=d.get("next_action", ""),
            safe_mode=d.get("safe_mode", False),
            safe_mode_reason=d.get("safe_mode_reason", ""),
            study_mode=d.get("study_mode", ""),
            topic=d.get("topic", ""),
            source_plan=d.get("source_plan", ""),
            stage=d.get("stage", ""),
            estimated_minutes=d.get("estimated_minutes", 0),
            actual_minutes=d.get("actual_minutes", 0),
            created_at=d.get("created_at", _now_iso()),
            updated_at=d.get("updated_at", _now_iso()),
        )

    # ── v1 兼容迁移 ──

    @classmethod
    def from_v1_dict(cls, d: dict) -> "TaskEntry":
        """从 v1 格式 task dict 迁移到 v4 TaskEntry"""
        status = normalize_v1_status(d.get("status", "queued"))
        wf = d.get("workflow")
        return cls(
            task_id=d["task_id"],
            title=d["title"],
            workflow=Workflow(wf) if wf else Workflow.DELIVERY,
            status=status,
            source=d.get("source", "manual"),
            artifacts=d.get("artifacts", []),
            next_action=d.get("next_action", ""),
            created_at=d.get("created_at", _now_iso()),
            updated_at=d.get("updated_at", _now_iso()),
        )


# ── artifact_paths 安全规则 ────────────────────────────

class ArtifactPathError(Exception):
    """artifact_path 安全违规"""


def validate_artifact_path(artifact_path: str, repo_root: Path) -> Path:
    """
    验证单个 artifact_path 的安全性。

    规则 (per 03_safe_mode_and_rollback.md §5):
    1. 禁止 '../' 向上遍历
    2. normalize → resolve against repo root
    3. 检查最终路径位于 repo root 内
    4. 越界 → raise ArtifactPathError

    Returns: 安全的 resolved Path
    """
    if not artifact_path or not artifact_path.strip():
        raise ArtifactPathError("artifact_path 为空")

    # Rule 1: 禁止 ../
    if ".." in artifact_path.split("/"):
        raise ArtifactPathError(
            f"artifact_path 包含禁止的 '../' : {artifact_path}"
        )

    # Rule 2: reject absolute paths
    if artifact_path.startswith("/") or os.path.isabs(artifact_path):
        raise ArtifactPathError(
            f"artifact_path 不允许绝对路径: {artifact_path}"
        )

    # Rule 3: normalize + resolve against repo root
    normalized = os.path.normpath(artifact_path)
    resolved = (repo_root / normalized).resolve()

    # Rule 3: boundary check
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError:
        raise ArtifactPathError(
            f"artifact_path 越界（不在 repo root 内）: {artifact_path} → {resolved}"
        )

    return resolved


def validate_artifact_paths(artifact_paths: list[str], repo_root: Path) -> list[Path]:
    """
    批量验证 artifact_paths。返回安全的 Path 列表。
    越界的路径不会静默跳过 — 会抛出 ArtifactPathError。
    """
    validated = []
    for ap in artifact_paths:
        validated.append(validate_artifact_path(ap, repo_root))
    return validated


def is_artifact_safe(artifact_path: str, repo_root: Path) -> bool:
    """快速安全检查（不抛异常）"""
    try:
        validate_artifact_path(artifact_path, repo_root)
        return True
    except ArtifactPathError:
        return False


# ── Ledger 顶层结构 ───────────────────────────────────

@dataclass
class TaskLedger:
    """任务账本完整数据结构"""
    meta: dict
    tasks: list[TaskEntry]

    def to_dict(self) -> dict:
        return {
            "meta": self.meta,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, d: dict, migrate_v1: bool = True) -> "TaskLedger":
        """从 dict 加载，可选自动迁移 v1 数据"""
        tasks = []
        for t in d.get("tasks", []):
            # 检测是否为 v1 任务（缺少 task_type 字段）
            if migrate_v1 and "task_type" not in t:
                tasks.append(TaskEntry.from_v1_dict(t))
            else:
                tasks.append(TaskEntry.from_dict(t))
        return cls(meta=d.get("meta", {}), tasks=tasks)

    def find_task(self, task_id: str) -> Optional[TaskEntry]:
        for t in self.tasks:
            if t.task_id == task_id:
                return t
        return None

    def get_tasks_by_status(self, status: TaskStatus) -> list[TaskEntry]:
        return [t for t in self.tasks if t.status == status]

    def get_tasks_by_workflow(self, workflow: Workflow) -> list[TaskEntry]:
        return [t for t in self.tasks if t.workflow == workflow]

    def get_tasks_by_route(self, route_id: str) -> list[TaskEntry]:
        return [t for t in self.tasks if t.route_id == route_id]

    def get_active_tasks(self) -> list[TaskEntry]:
        from orchestration.orchestration_types import ACTIVE_STATUSES
        return [t for t in self.tasks if t.status in ACTIVE_STATUSES]

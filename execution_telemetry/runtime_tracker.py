"""
runtime_tracker — 运行时状态追踪器
TELEMETRY-ONLY: NO_STATE_MUTATION | FAIL_SILENT

负责：
- 维护当前 workflow / stage / skill / status 的运行时状态
- 更新 state/telemetry/runtime-status.json
- 提供统一状态修改 API
- 编排 cli_display + timeline_logger 的调用

所有状态更新 try-except 包裹，任何异常 Fail-Silent。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_enabled() -> bool:
    return os.environ.get("SKILL_OS_TELEMETRY", "0") == "1"


# ── 内部状态 ──────────────────────────────────────────────

class _RuntimeSnapshot:
    """运行时状态快照（内存中）"""
    __slots__ = (
        "workflow", "task_id", "status", "stage_index",
        "total_stages", "stage_name", "skill", "action",
        "action_zh", "started_at", "updated_at",
    )

    def __init__(self):
        self.workflow = ""
        self.task_id = ""
        self.status = "idle"
        self.stage_index = 0
        self.total_stages = 0
        self.stage_name = ""
        self.skill = ""
        self.action = ""
        self.action_zh = ""
        self.started_at = ""
        self.updated_at = ""

    def to_dict(self) -> dict:
        return {
            "workflow": self.workflow,
            "task_id": self.task_id,
            "status": self.status,
            "stage_index": self.stage_index,
            "total_stages": self.total_stages,
            "stage_name": self.stage_name,
            "skill": self.skill,
            "action": self.action,
            "action_zh": self.action_zh,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }


_snapshot = _RuntimeSnapshot()

# 累积执行信息（用于最终摘要）
_acc = {
    "started_at": "",
    "last_stage_index": 0,
    "last_stage_name": "",
    "last_skill": "",
    "failed_reason": "",
}


# ── 持久化 ────────────────────────────────────────────────

def _telemetry_dir() -> Optional[Path]:
    try:
        d = Path(__file__).parent.parent / ".claude" / "state" / "telemetry"
        d.mkdir(parents=True, exist_ok=True)
        return d
    except Exception:
        return None


def _persist_snapshot() -> None:
    """将当前快照写入 runtime-status.json"""
    if not _is_enabled():
        return
    try:
        d = _telemetry_dir()
        if d is None:
            return
        _snapshot.updated_at = _now_iso()
        path = d / "runtime-status.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_snapshot.to_dict(), f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── 现有 state 兼容读取 ───────────────────────────────────

def _read_existing_execution_state() -> Optional[dict]:
    """
    优先读取现有 execution-state.json 中的 pipeline_templates。
    用于获取 total_stages。
    """
    try:
        path = Path(__file__).parent.parent / ".claude" / "state" / "execution-state.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _get_total_stages_from_existing(workflow: str) -> int:
    """从现有 execution-state.json 获取某 workflow 的 stage 总数"""
    es = _read_existing_execution_state()
    if es is None:
        return 0
    templates = es.get("pipeline_templates", {})
    stages = templates.get(workflow, [])
    return len(stages) if stages else 0


# ── 公开 API ──────────────────────────────────────────────

def get_snapshot() -> dict:
    """获取当前运行时状态快照"""
    return _snapshot.to_dict()


def start_workflow(
    workflow_name: str,
    total_stages: int = 0,
    task_id: str = "",
    message: str = "",
    message_zh: str = "",
) -> None:
    """workflow 开始"""
    if not _is_enabled():
        return
    try:
        from execution_telemetry import cli_display, timeline_logger

        # 如果未指定总 stage 数，从现有 state 读取
        if total_stages <= 0:
            total_stages = _get_total_stages_from_existing(workflow_name)

        _snapshot.workflow = workflow_name
        _snapshot.task_id = task_id
        _snapshot.status = "running"
        _snapshot.stage_index = 0
        _snapshot.total_stages = total_stages
        _snapshot.stage_name = ""
        _snapshot.skill = ""
        _snapshot.action = message or "workflow started"
        _snapshot.action_zh = message_zh or ""
        _snapshot.started_at = _now_iso()
        _snapshot.updated_at = _snapshot.started_at

        _acc["started_at"] = _snapshot.started_at
        _acc["last_stage_index"] = 0
        _acc["last_stage_name"] = ""
        _acc["last_skill"] = ""
        _acc["failed_reason"] = ""

        _persist_snapshot()

        timeline_logger.append_event(
            event="workflow_started",
            workflow=workflow_name,
            task_id=task_id,
            message=message or f"workflow {workflow_name} started",
            message_zh=message_zh or f"工作流 {workflow_name} 开始执行",
        )

        cli_display.display_workflow_started(
            workflow=workflow_name,
            total_stages=total_stages,
            task_id=task_id,
        )
    except Exception:
        pass


def enter_stage(
    stage_index: int,
    stage_name: str,
    total_stages: int = 0,
    skill: str = "",
    message: str = "",
    message_zh: str = "",
) -> None:
    """stage 进入"""
    if not _is_enabled():
        return
    try:
        from execution_telemetry import cli_display, timeline_logger

        if total_stages > 0:
            _snapshot.total_stages = total_stages

        _snapshot.status = "running"
        _snapshot.stage_index = stage_index
        _snapshot.stage_name = stage_name
        _snapshot.action = message or f"entering stage {stage_name}"
        _snapshot.action_zh = message_zh or ""
        _snapshot.updated_at = _now_iso()

        _acc["last_stage_index"] = stage_index
        _acc["last_stage_name"] = stage_name

        _persist_snapshot()

        timeline_logger.append_event(
            event="stage_entered",
            workflow=_snapshot.workflow,
            task_id=_snapshot.task_id,
            stage_index=stage_index,
            stage_name=stage_name,
            skill=skill,
            message=message or f"stage {stage_name} entered",
            message_zh=message_zh or f"进入 {stage_name} 阶段",
        )

        cli_display.display_stage_entered(
            workflow=_snapshot.workflow,
            stage_index=stage_index,
            stage_name=stage_name,
            total_stages=_snapshot.total_stages,
            skill=skill,
        )
    except Exception:
        pass


def complete_stage(
    stage_index: int,
    stage_name: str = "",
    next_stage: str = "",
    message: str = "",
    message_zh: str = "",
) -> None:
    """stage 完成"""
    if not _is_enabled():
        return
    try:
        from execution_telemetry import cli_display, timeline_logger

        name = stage_name or _snapshot.stage_name
        _snapshot.action = message or f"stage {name} completed"
        _snapshot.action_zh = message_zh or ""
        _snapshot.updated_at = _now_iso()

        _persist_snapshot()

        timeline_logger.append_event(
            event="stage_completed",
            workflow=_snapshot.workflow,
            task_id=_snapshot.task_id,
            stage_index=stage_index,
            stage_name=name,
            message=message or f"stage {name} completed",
            message_zh=message_zh or f"{name} 阶段完成",
        )

        cli_display.display_stage_completed(
            stage_index=stage_index,
            stage_name=name,
            total_stages=_snapshot.total_stages,
            next_stage=next_stage,
        )
    except Exception:
        pass


def fail_stage(
    stage_index: int,
    stage_name: str = "",
    reason: str = "",
    reason_zh: str = "",
    message: str = "",
    message_zh: str = "",
) -> None:
    """stage 失败"""
    if not _is_enabled():
        return
    try:
        from execution_telemetry import cli_display, timeline_logger

        name = stage_name or _snapshot.stage_name
        _snapshot.status = "failed"
        _snapshot.action = message or f"stage {name} failed"
        _snapshot.action_zh = message_zh or reason_zh or ""
        _snapshot.updated_at = _now_iso()

        _persist_snapshot()

        timeline_logger.append_event(
            event="stage_failed",
            workflow=_snapshot.workflow,
            task_id=_snapshot.task_id,
            stage_index=stage_index,
            stage_name=name,
            message=message or f"stage {name} failed: {reason}",
            message_zh=message_zh or reason_zh or f"{name} 阶段失败",
            extra={"reason": reason} if reason else None,
        )

        cli_display.display_stage_failed(
            stage_index=stage_index,
            stage_name=name,
            reason=reason,
        )
    except Exception:
        pass


def set_skill(
    skill_name: str,
    message: str = "",
    message_zh: str = "",
) -> None:
    """skill 切换"""
    if not _is_enabled():
        return
    try:
        from execution_telemetry import cli_display, timeline_logger

        _snapshot.skill = skill_name
        _snapshot.action = message or f"executing skill {skill_name}"
        _snapshot.action_zh = message_zh or ""
        _snapshot.updated_at = _now_iso()

        _acc["last_skill"] = skill_name

        _persist_snapshot()

        timeline_logger.append_event(
            event="skill_started",
            workflow=_snapshot.workflow,
            task_id=_snapshot.task_id,
            skill=skill_name,
            message=message or f"skill {skill_name} started",
            message_zh=message_zh or f"开始执行 {skill_name} 技能",
        )

        cli_display.display_skill_started(skill=skill_name)
    except Exception:
        pass


def heartbeat(
    message: str,
    message_zh: str = "",
) -> None:
    """关键动作 heartbeat"""
    if not _is_enabled():
        return
    try:
        from execution_telemetry import cli_display, timeline_logger

        _snapshot.action = message
        _snapshot.action_zh = message_zh or ""
        _snapshot.updated_at = _now_iso()

        _persist_snapshot()

        timeline_logger.append_event(
            event="heartbeat",
            workflow=_snapshot.workflow,
            task_id=_snapshot.task_id,
            message=message,
            message_zh=message_zh or "",
        )

        cli_display.display_heartbeat(message=message, message_zh=message_zh)
    except Exception:
        pass


def complete_workflow(
    summary: str = "",
    summary_zh: str = "",
) -> None:
    """workflow 完成"""
    if not _is_enabled():
        return
    try:
        from execution_telemetry import cli_display, timeline_logger

        ended_at = _now_iso()
        _snapshot.status = "completed"
        _snapshot.action = summary or "workflow completed"
        _snapshot.action_zh = summary_zh or ""
        _snapshot.updated_at = ended_at

        _persist_snapshot()

        timeline_logger.append_event(
            event="workflow_completed",
            workflow=_snapshot.workflow,
            task_id=_snapshot.task_id,
            message=summary or f"workflow {_snapshot.workflow} completed",
            message_zh=summary_zh or f"工作流 {_snapshot.workflow} 已完成",
        )

        # 计算 duration
        duration = 0
        if _acc["started_at"] and ended_at:
            try:
                s = datetime.fromisoformat(_acc["started_at"])
                e = datetime.fromisoformat(ended_at)
                duration = int((e - s).total_seconds())
            except (ValueError, TypeError):
                pass

        cli_display.display_workflow_completed(
            workflow=_snapshot.workflow,
            duration_seconds=duration,
        )

        timeline_logger.write_last_run_summary(
            workflow=_snapshot.workflow,
            task_id=_snapshot.task_id,
            final_status="completed",
            last_stage_index=_acc["last_stage_index"],
            last_stage_name=_acc["last_stage_name"],
            last_skill=_acc["last_skill"],
            started_at=_acc["started_at"],
            ended_at=ended_at,
            failed_reason="",
            resumable=False,
            summary_zh=summary_zh or f"{_snapshot.workflow} 已成功完成",
        )
    except Exception:
        pass


def fail_workflow(
    reason: str = "",
    reason_zh: str = "",
    stage_name: str = "",
) -> None:
    """workflow 失败"""
    if not _is_enabled():
        return
    try:
        from execution_telemetry import cli_display, timeline_logger

        ended_at = _now_iso()
        _snapshot.status = "failed"
        _snapshot.action = reason or "workflow failed"
        _snapshot.action_zh = reason_zh or ""
        _snapshot.updated_at = ended_at

        failed_stage = stage_name or _acc["last_stage_name"]
        _acc["failed_reason"] = reason

        _persist_snapshot()

        timeline_logger.append_event(
            event="workflow_failed",
            workflow=_snapshot.workflow,
            task_id=_snapshot.task_id,
            stage_name=failed_stage,
            message=reason or f"workflow {_snapshot.workflow} failed",
            message_zh=reason_zh or f"工作流 {_snapshot.workflow} 失败",
            extra={"reason": reason} if reason else None,
        )

        cli_display.display_workflow_failed(
            workflow=_snapshot.workflow,
            stage_name=failed_stage,
            reason=reason,
        )

        timeline_logger.write_last_run_summary(
            workflow=_snapshot.workflow,
            task_id=_snapshot.task_id,
            final_status="failed",
            last_stage_index=_acc["last_stage_index"],
            last_stage_name=_acc["last_stage_name"],
            last_skill=_acc["last_skill"],
            started_at=_acc["started_at"],
            ended_at=ended_at,
            failed_reason=reason,
            resumable=True,
            summary_zh=reason_zh or f"{_snapshot.workflow} 在 {failed_stage} 阶段失败",
        )
    except Exception:
        pass

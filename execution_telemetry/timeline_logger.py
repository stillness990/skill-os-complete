"""
timeline_logger — 执行时间线日志记录器
TELEMETRY-ONLY: NO_STATE_MUTATION | FAIL_SILENT

负责：
- 向 state/telemetry/execution-timeline.jsonl 追加事件
- 生成 / 更新 state/telemetry/last-run-summary.json
- 处理 timeline 事件序列化

所有写操作 try-except 包裹，Fail-Silent。
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


# ── 路径解析 ──────────────────────────────────────────────

def _telemetry_dir() -> Path:
    """解析 telemetry 状态目录"""
    return Path(__file__).parent.parent / ".claude" / "state" / "telemetry"


def _ensure_dir() -> Optional[Path]:
    """确保 telemetry 目录存在，返回 Path 或 None"""
    try:
        d = _telemetry_dir()
        d.mkdir(parents=True, exist_ok=True)
        return d
    except Exception:
        return None


# ── Timeline 事件写入 ─────────────────────────────────────

def append_event(
    event: str,
    workflow: str = "",
    task_id: str = "",
    stage_index: int = 0,
    stage_name: str = "",
    skill: str = "",
    message: str = "",
    message_zh: str = "",
    extra: Optional[dict] = None,
) -> bool:
    """
    向 execution-timeline.jsonl 追加一行事件。

    返回 True 表示写入成功，False 表示静默失败。
    """
    if not _is_enabled():
        return False

    d = _ensure_dir()
    if d is None:
        return False

    try:
        record = {
            "ts": _now_iso(),
            "event": event,
            "workflow": workflow,
            "task_id": task_id,
            "stage_index": stage_index,
            "stage_name": stage_name,
            "skill": skill,
            "message": message,
            "message_zh": message_zh,
        }
        if extra:
            record.update(extra)

        timeline_path = d / "execution-timeline.jsonl"
        with open(timeline_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


# ── 摘要生成 ──────────────────────────────────────────────

def write_last_run_summary(
    workflow: str = "",
    task_id: str = "",
    final_status: str = "",
    last_stage_index: int = 0,
    last_stage_name: str = "",
    last_skill: str = "",
    started_at: str = "",
    ended_at: str = "",
    failed_reason: str = "",
    resumable: bool = False,
    summary_zh: str = "",
) -> bool:
    """
    生成 / 更新 last-run-summary.json。

    返回 True 表示写入成功。
    """
    if not _is_enabled():
        return False

    d = _ensure_dir()
    if d is None:
        return False

    # 计算 duration
    duration_seconds = 0
    if started_at and ended_at:
        try:
            start = datetime.fromisoformat(started_at)
            end = datetime.fromisoformat(ended_at)
            duration_seconds = int((end - start).total_seconds())
        except (ValueError, TypeError):
            pass

    try:
        summary = {
            "workflow": workflow,
            "task_id": task_id,
            "final_status": final_status,
            "last_stage_index": last_stage_index,
            "last_stage_name": last_stage_name,
            "last_skill": last_skill,
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_seconds": duration_seconds,
            "failed_reason": failed_reason,
            "resumable": resumable,
            "summary_zh": summary_zh,
        }

        summary_path = d / "last-run-summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def read_last_run_summary() -> Optional[dict]:
    """读取上次运行摘要，不存在时返回 None。"""
    if not _is_enabled():
        return None
    try:
        summary_path = _telemetry_dir() / "last-run-summary.json"
        if not summary_path.exists():
            return None
        with open(summary_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def read_timeline_events(limit: int = 100) -> list[dict]:
    """读取最近的 timeline 事件。"""
    if not _is_enabled():
        return []
    try:
        timeline_path = _telemetry_dir() / "execution-timeline.jsonl"
        if not timeline_path.exists():
            return []
        events = []
        with open(timeline_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return events[-limit:]
    except Exception:
        return []

"""
resume_manager — 断点恢复管理器
TELEMETRY-ONLY: NO_STATE_MUTATION | FAIL_SILENT

负责：
- 检查是否存在 unfinished workflow
- 读取上次摘要
- 生成 resume 提示文本
- 如果现有系统有恢复入口，负责接线

所有读操作 try-except 包裹，Fail-Silent。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from execution_telemetry.timeline_logger import read_last_run_summary


def _is_enabled() -> bool:
    return os.environ.get("SKILL_OS_TELEMETRY", "0") == "1"


def check_unfinished_workflow(
    current_workflow: str = "",
) -> Optional[dict]:
    """
    检查是否存在未完成的 workflow。

    参数:
        current_workflow: 当前即将进入的 workflow 名称

    返回:
        - 如果发现未完成且可恢复的 workflow: 返回 resume_info dict
        - 否则: 返回 None
    """
    if not _is_enabled():
        return None

    try:
        summary = read_last_run_summary()
        if summary is None:
            return None

        # 检查是否是同一个 workflow
        if current_workflow and summary.get("workflow") != current_workflow:
            return None

        # 已完成的不需要恢复
        final_status = summary.get("final_status", "")
        if final_status == "completed":
            return None

        # 不可恢复的跳过
        if not summary.get("resumable", False):
            return None

        return {
            "workflow": summary.get("workflow", ""),
            "task_id": summary.get("task_id", ""),
            "last_stage_index": summary.get("last_stage_index", 0),
            "last_stage_name": summary.get("last_stage_name", ""),
            "last_skill": summary.get("last_skill", ""),
            "final_status": final_status,
            "failed_reason": summary.get("failed_reason", ""),
            "summary_zh": summary.get("summary_zh", ""),
            "started_at": summary.get("started_at", ""),
            "ended_at": summary.get("ended_at", ""),
            "duration_seconds": summary.get("duration_seconds", 0),
        }
    except Exception:
        return None


def get_resume_context() -> Optional[dict]:
    """
    获取 resume 上下文（不带 current_workflow 过滤）。
    用于 CLI 脚本等场景。
    """
    if not _is_enabled():
        return None

    try:
        summary = read_last_run_summary()
        if summary is None:
            return None

        final_status = summary.get("final_status", "")
        if final_status == "completed":
            return None
        if not summary.get("resumable", False):
            return None

        return {
            "workflow": summary.get("workflow", ""),
            "task_id": summary.get("task_id", ""),
            "last_stage_index": summary.get("last_stage_index", 0),
            "last_stage_name": summary.get("last_stage_name", ""),
            "last_skill": summary.get("last_skill", ""),
            "final_status": final_status,
            "failed_reason": summary.get("failed_reason", ""),
            "summary_zh": summary.get("summary_zh", ""),
        }
    except Exception:
        return None

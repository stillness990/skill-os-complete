"""
cli_display — 终端格式化输出
TELEMETRY-ONLY: NO_STATE_MUTATION | FAIL_SILENT

负责：
- 把 runtime 状态格式化为终端输出
- 统一输出 stage 切换、skill 切换、heartbeat、完成、失败等信息
- 只做展示，不做业务逻辑
- 统一处理中英混合输出格式
- heartbeat 节流：最小间隔 ≥ 2s，仅在当前 stage 持续 > 5s 后才开始输出
"""

from __future__ import annotations

import sys
import time
from typing import Optional

from execution_telemetry.zh_messages import (
    workflow_started_zh,
    stage_entered_zh,
    stage_completed_zh,
    stage_failed_zh,
    skill_started_zh,
    heartbeat_zh,
    workflow_completed_zh,
    workflow_failed_zh,
)


# ── Terminal check ───────────────────────────────────────

def _is_tty() -> bool:
    """检查 stdout 是否为终端"""
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def _safe_print(text: str) -> None:
    """安全打印，始终 try-except"""
    try:
        print(text, flush=True)
    except Exception:
        pass


# ── Heartbeat 节流 ───────────────────────────────────────

_heartbeat_state = {
    "last_heartbeat_time": 0.0,
    "stage_entered_at": 0.0,
    "heartbeat_count_in_stage": 0,
}


def _reset_heartbeat_state() -> None:
    """重置 heartbeat 状态（stage 切换时调用）"""
    _heartbeat_state["last_heartbeat_time"] = 0.0
    _heartbeat_state["stage_entered_at"] = time.time()
    _heartbeat_state["heartbeat_count_in_stage"] = 0


def _can_heartbeat() -> bool:
    """检查是否允许输出 heartbeat"""
    now = time.time()
    # 当前 stage 必须已持续 ≥ 5 秒
    stage_elapsed = now - _heartbeat_state["stage_entered_at"]
    if stage_elapsed < 5:
        return False
    # 距离上次 heartbeat ≥ 2 秒
    since_last = now - _heartbeat_state["last_heartbeat_time"]
    if since_last < 2:
        return False
    # 非终端环境不输出
    if not _is_tty():
        return False
    return True


def _record_heartbeat() -> None:
    """记录一次 heartbeat 输出"""
    _heartbeat_state["last_heartbeat_time"] = time.time()
    _heartbeat_state["heartbeat_count_in_stage"] += 1


# ── 格式化输出函数 ────────────────────────────────────────

# 表格宽字符宽度常量
PANEL_WIDTH = 55


def _status_box(title: str, lines: list[str]) -> str:
    """
    构建统一的状态面板。

    title: 面板标题（如 "SKILL OS EXECUTION / 执行状态"）
    lines: [(label, value), ...]
    """
    body = "\n".join(f"  {label:<12}: {value}" for label, value in lines)
    return (
        f"\n┌── {title} {'─' * (PANEL_WIDTH - len(title) - 6)}┐\n"
        f"{body}\n"
        f"└{'─' * PANEL_WIDTH}┘"
    )


def display_workflow_started(
    workflow: str,
    total_stages: int = 0,
    task_id: str = "",
) -> None:
    """workflow 开始时的终端输出"""
    _reset_heartbeat_state()

    lines = [
        ("Workflow", workflow),
        ("Status", "RUNNING"),
    ]
    if task_id:
        lines.insert(0, ("Task ID", task_id))
    if total_stages > 0:
        lines.append(("Stages", str(total_stages)))

    zh = workflow_started_zh(workflow)

    _safe_print(_status_box("SKILL OS EXECUTION / 执行状态", lines))
    _safe_print(f"  {zh}\n")


def display_stage_entered(
    workflow: str,
    stage_index: int,
    stage_name: str,
    total_stages: int = 0,
    skill: str = "",
) -> None:
    """stage 进入时的终端输出"""
    _reset_heartbeat_state()

    stage_display = f"{stage_index}/{total_stages}" if total_stages > 0 else str(stage_index)
    lines = [
        ("Workflow", workflow),
        ("Stage", f"{stage_display} ({stage_name})"),
        ("Status", "RUNNING"),
    ]
    if skill:
        lines.append(("Skill", skill))

    zh = stage_entered_zh(stage_index, total_stages, stage_name)

    _safe_print(_status_box("SKILL OS EXECUTION / 执行状态", lines))
    _safe_print(f"  {zh}\n")


def display_stage_completed(
    stage_index: int,
    stage_name: str,
    total_stages: int = 0,
    next_stage: str = "",
) -> None:
    """stage 完成时的终端输出"""
    parts = [f"✓ 阶段 {stage_index}（{stage_name}）已完成"]
    if next_stage:
        parts.append(f"→ 进入阶段 {stage_index + 1}（{next_stage}）")
    _safe_print("  " + " ".join(parts))

    zh = stage_completed_zh(stage_index, total_stages, stage_name)
    if next_stage:
        zh += f"，正在进入 {next_stage}"
    _safe_print(f"  {zh}")


def display_stage_failed(
    stage_index: int,
    stage_name: str,
    reason: str = "",
) -> None:
    """stage 失败时的终端输出"""
    _safe_print(f"  ✗ 阶段 {stage_index}（{stage_name}）失败")
    if reason:
        _safe_print(f"    原因：{reason}")

    zh = stage_failed_zh(stage_index, stage_name, reason)
    _safe_print(f"  {zh}")


def display_skill_started(skill: str) -> None:
    """skill 启动时的终端输出"""
    _safe_print(f"  → 执行技能：{skill}")

    zh = skill_started_zh(skill)
    _safe_print(f"  {zh}")


def display_heartbeat(message: str, message_zh: str = "") -> None:
    """heartbeat 输出（受节流控制）"""
    if not _can_heartbeat():
        return

    _record_heartbeat()
    if message_zh:
        _safe_print(f"  · {message} / {message_zh}")
    else:
        _safe_print(f"  · {message}")


def display_workflow_completed(
    workflow: str,
    duration_seconds: int = 0,
) -> None:
    """workflow 完成时的终端输出"""
    duration_str = f"（{duration_seconds}s）" if duration_seconds > 0 else ""
    _safe_print(f"\n  ✓ Workflow {workflow} 已完成 {duration_str}")

    zh = workflow_completed_zh(workflow)
    _safe_print(f"  {zh}\n")


def display_workflow_failed(
    workflow: str,
    stage_name: str = "",
    reason: str = "",
) -> None:
    """workflow 失败时的终端输出"""
    _safe_print(f"\n  ✗ Workflow {workflow} 执行失败")
    if stage_name:
        _safe_print(f"    失败于阶段：{stage_name}")
    if reason:
        _safe_print(f"    原因：{reason}")

    zh = workflow_failed_zh(workflow, stage_name, reason)
    _safe_print(f"  {zh}\n")


def display_resume_hint(
    workflow: str,
    last_stage_index: int,
    last_stage_name: str,
    last_skill: str,
    final_status: str,
) -> None:
    """resume 断点恢复提示"""
    from execution_telemetry.zh_messages import resume_hint_zh

    lines = [
        ("Workflow", workflow),
        ("Last Stage", f"{last_stage_index} ({last_stage_name})"),
        ("Last Skill", last_skill),
        ("Status", final_status),
    ]

    _safe_print(_status_box("SKILL OS RESUME / 断点恢复提示", lines))

    zh = resume_hint_zh(workflow, last_stage_name, last_skill)
    _safe_print(f"  {zh}\n")

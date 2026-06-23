#!/usr/bin/env python3
"""
Skill OS v5 — Task Guard Hook（任务状态变更校验 + 状态注入）
触发时机: task_ledger 任务状态更新前 / 会话开始
作用:    校验状态流转合法性 + 检测 stall + 注入执行上下文
状态:    v5.0.0 — 从 v4 占位升级，接入 state/ 统一状态层

v5 核心升级:
  - 主数据源从 system/task_ledger/tasks.json → state/current-task.json + state/execution-state.json
  - stall 检测覆盖 state/ 三文件 (current-task + execution-state + learning-state)
  - 注入上下文包含 pipeline 进度、guard_status、safe_mode 信息
  - 保留 v4 legacy fallback 链

校验规则引用:
  - .claude/system/execution_guard/task-state-machine.md
  - .claude/system/execution_guard/guard-rules.md
  - .claude/system/execution_guard/stall-policy.md
  - .claude/state/README.md
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


CLAUDE_DIR = Path(__file__).parent.parent
GUARD_DIR = CLAUDE_DIR / "system" / "execution_guard"
STATE_DIR = CLAUDE_DIR / "state"

# v5 primary sources
CURRENT_TASK_FILE = STATE_DIR / "current-task.json"
EXECUTION_STATE_FILE = STATE_DIR / "execution-state.json"
LEARNING_STATE_FILE = STATE_DIR / "learning-state.json"
TASK_HISTORY_FILE = STATE_DIR / "task-history.json"

# v4 legacy fallback
LEGACY_LEDGER_FILE = CLAUDE_DIR / "system" / "task_ledger" / "tasks.json"

# Stall thresholds (from stall-policy.md)
WARNING_DAYS = 3
STALL_DAYS = 7
MAX_RETRY_WARNING = 3
MAX_RETRY_STALL = 5


# ── v5 State Loading ───────────────────────────────────────────

def load_json(path: Path) -> dict | None:
    """安全加载 JSON 文件。"""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def get_active_task() -> dict | None:
    """v5: 从 state/current-task.json 获取当前活跃任务。"""
    data = load_json(CURRENT_TASK_FILE)
    if data:
        task = data.get("active_task")
        if task:
            return task
    return None


def get_execution_state() -> dict | None:
    """v5: 获取执行状态。"""
    return load_json(EXECUTION_STATE_FILE)


def get_learning_state() -> dict | None:
    """v5: 获取学习状态。"""
    return load_json(LEARNING_STATE_FILE)


def get_legacy_active_tasks() -> list:
    """v4 legacy fallback: 从 tasks.json 获取活跃任务。"""
    ledger = load_json(LEGACY_LEDGER_FILE)
    if not ledger:
        return []
    return [t for t in ledger.get("tasks", []) if t.get("status") not in ("done", "cancelled")]


# ── Stall Detection ────────────────────────────────────────────

def detect_stalled_current_task(task: dict | None) -> list:
    """检测 current-task.json 中的 stall 状态。"""
    if not task:
        return []
    stalled = []
    now = datetime.now(timezone.utc)
    status = task.get("status", "")

    if status in ("done", "cancelled"):
        return []

    try:
        updated = datetime.fromisoformat(task.get("last_activity_at") or task.get("updated_at", ""))
    except (ValueError, TypeError):
        return []

    days_since = (now - updated).days
    retry_count = task.get("retry_count", 0)

    if status in ("planning", "executing") and days_since >= STALL_DAYS:
        stalled.append({
            "source": "state/current-task.json",
            "task_id": task.get("task_id", "unknown"),
            "title": task.get("title", ""),
            "status": status,
            "days_stale": days_since,
            "level": "stalled",
            "advice": "状态超过 7 天未更新，建议标记 stalled 或检查是否卡住"
        })
    elif status in ("planning", "executing") and days_since >= WARNING_DAYS:
        stalled.append({
            "source": "state/current-task.json",
            "task_id": task.get("task_id", "unknown"),
            "title": task.get("title", ""),
            "status": status,
            "days_stale": days_since,
            "level": "warning",
            "advice": f"状态 {days_since} 天未更新，建议更新进度"
        })
    elif status == "retrying" and retry_count >= MAX_RETRY_STALL:
        stalled.append({
            "source": "state/current-task.json",
            "task_id": task.get("task_id", "unknown"),
            "title": task.get("title", ""),
            "status": status,
            "retry_count": retry_count,
            "level": "stalled",
            "advice": f"已重试 {retry_count} 次，建议分析失败模式或标记 stalled"
        })
    elif status == "retrying" and retry_count >= MAX_RETRY_WARNING:
        stalled.append({
            "source": "state/current-task.json",
            "task_id": task.get("task_id", "unknown"),
            "title": task.get("title", ""),
            "status": status,
            "retry_count": retry_count,
            "level": "warning",
            "advice": f"已重试 {retry_count} 次，建议分析失败模式"
        })

    return stalled


def detect_stalled_legacy(tasks: list) -> list:
    """v4 legacy: 检测 tasks.json 中的 stall 状态。"""
    stalled = []
    now = datetime.now(timezone.utc)
    for t in tasks:
        status = t.get("status", "")
        if status in ("done", "cancelled"):
            continue
        try:
            updated = datetime.fromisoformat(t.get("updated_at", ""))
        except (ValueError, TypeError):
            continue
        days_since = (now - updated).days
        retry_count = t.get("retry_count", 0)

        if status in ("planning", "executing") and days_since >= STALL_DAYS:
            stalled.append({
                "source": "system/task_ledger/tasks.json (legacy)",
                "task_id": t["task_id"],
                "title": t.get("title", ""),
                "status": status,
                "days_stale": days_since,
                "level": "stalled",
                "advice": "建议检查是否卡住，考虑标记 stalled 或更新进度"
            })
        elif status in ("planning", "executing") and days_since >= WARNING_DAYS:
            stalled.append({
                "source": "system/task_ledger/tasks.json (legacy)",
                "task_id": t["task_id"],
                "title": t.get("title", ""),
                "status": status,
                "days_stale": days_since,
                "level": "warning",
                "advice": "建议更新任务进度"
            })
        elif status == "retrying" and retry_count >= MAX_RETRY_STALL:
            stalled.append({
                "source": "system/task_ledger/tasks.json (legacy)",
                "task_id": t["task_id"],
                "title": t.get("title", ""),
                "status": status,
                "retry_count": retry_count,
                "level": "stalled",
                "advice": f"已重试 {retry_count} 次"
            })
        elif status == "retrying" and retry_count >= MAX_RETRY_WARNING:
            stalled.append({
                "source": "system/task_ledger/tasks.json (legacy)",
                "task_id": t["task_id"],
                "title": t.get("title", ""),
                "status": status,
                "retry_count": retry_count,
                "level": "warning",
                "advice": f"已重试 {retry_count} 次"
            })
    return stalled


def detect_learning_stall() -> list:
    """检测 learning-state.json 中的学习断档。"""
    ls = get_learning_state()
    if not ls:
        return []

    stalled = []
    now = datetime.now(timezone.utc)

    for topic in ls.get("topics", []):
        stage = topic.get("current_stage", "")
        if stage in ("mastered", "paused"):
            continue

        try:
            last_activity = datetime.fromisoformat(topic.get("last_activity_at", ""))
        except (ValueError, TypeError):
            continue

        days_since = (now - last_activity).days
        if days_since >= STALL_DAYS:
            stalled.append({
                "source": "state/learning-state.json",
                "topic_id": topic.get("topic_id", "unknown"),
                "topic_name": topic.get("topic_name", ""),
                "current_stage": stage,
                "days_stale": days_since,
                "level": "stalled",
                "advice": f"学习主题 '{topic.get('topic_name', '')}' {days_since} 天未活动，建议恢复或标记 paused"
            })
        elif days_since >= WARNING_DAYS:
            stalled.append({
                "source": "state/learning-state.json",
                "topic_id": topic.get("topic_id", "unknown"),
                "topic_name": topic.get("topic_name", ""),
                "current_stage": stage,
                "days_stale": days_since,
                "level": "warning",
                "advice": f"学习主题 '{topic.get('topic_name', '')}' {days_since} 天未活动"
            })

    return stalled


# ── Context Building ───────────────────────────────────────────

def build_execution_context() -> dict:
    """构建执行上下文摘要（v5: 从 state/ 读取）。"""
    exec_state = get_execution_state()
    active_task = get_active_task()

    context = {
        "version": "5.0.0",
        "active_task_id": None,
        "active_workflow": None,
        "pipeline_progress": None,
        "guard_status": "idle",
        "safe_mode": False,
        "degraded": False,
        "total_tasks_done": 0,
    }

    if exec_state:
        context["active_workflow"] = exec_state.get("active_workflow")
        context["guard_status"] = exec_state.get("guard_status", "idle")
        context["safe_mode"] = exec_state.get("safe_mode", False)
        context["degraded"] = exec_state.get("degraded", False)

        pipeline = exec_state.get("pipeline_progress", {})
        if pipeline:
            stages = pipeline.get("stages", [])
            completed = sum(1 for s in stages if s.get("status") == "completed")
            context["pipeline_progress"] = {
                "current_stage": pipeline.get("current_stage_index", -1) + 1,
                "total_stages": pipeline.get("total_stages", len(stages)),
                "completed": completed,
                "stages": [
                    {"name": s.get("name", "?"), "status": s.get("status", "?")}
                    for s in stages
                ],
            }

    if active_task:
        context["active_task_id"] = active_task.get("task_id")
        context["task_status"] = active_task.get("status")
        context["task_title"] = active_task.get("title")
        context["task_validation"] = active_task.get("validation_status", "pending")

    # Count done tasks from history
    history = load_json(TASK_HISTORY_FILE)
    if history:
        done = [h for h in history.get("history", []) if h.get("status") == "done"]
        context["total_tasks_done"] = len(done)

    return context


# ── Injection Formatting ───────────────────────────────────────

def format_guard_injection(
    context: dict,
    stalled: list,
) -> str:
    """格式化 guard 状态注入文本。"""
    lines = [
        f"",
        f"╔══ EXECUTION GUARD (v5) ═══════════════╗",
    ]

    # Active task
    if context.get("active_task_id"):
        lines.append(f"║  📋 Task: {context['active_task_id']:<30}║")
        lines.append(f"║     Title: {context.get('task_title', 'N/A'):<30}║")
        lines.append(f"║     Status: {context.get('task_status', 'N/A'):<30}║")
    else:
        lines.append(f"║  📋 No active task                      ║")

    # Pipeline
    pp = context.get("pipeline_progress")
    if pp:
        lines.append(f"║  🔄 Pipeline: {pp.get('completed', 0)}/{pp.get('total_stages', 0)} stages done                ║")
        for s in pp.get("stages", []):
            icon = "✅" if s["status"] == "completed" else ("🔄" if s["status"] == "executing" else "⏳")
            lines.append(f"║     {icon} {s['name']:<30}║")

    # Guard status
    guard = context.get("guard_status", "idle")
    safe = context.get("safe_mode", False)
    degraded = context.get("degraded", False)
    status_flags = []
    if safe:
        status_flags.append("SAFE_MODE")
    if degraded:
        status_flags.append("DEGRADED")
    flags_str = f" ({', '.join(status_flags)})" if status_flags else ""
    lines.append(f"║  🛡️  Guard: {guard}{flags_str:<30}║")

    # Done count
    lines.append(f"║  ✅ Done: {context.get('total_tasks_done', 0)} tasks                        ║")

    # ── Chinese hint ──────────────────────────────────
    task_status = context.get("task_status", "")
    if task_status:
        cn_status = {
            "queued": "任务已排队等待处理",
            "planning": "系统正在分析需求并制定执行计划",
            "executing": "系统正在推进代码实现与文件修改",
            "blocked": "任务被阻塞，请检查阻塞原因或提供所需信息",
            "retrying": "系统正在重试恢复执行",
            "stalled": "任务长时间未推进，建议检查是否卡在某个阶段或等待输入",
        }.get(task_status, "任务正在处理中")
        lines.append(f"║  中文提示: {cn_status:<30}║")

    # Stall warnings
    if stalled:
        lines.append(f"╠══ ⚠️  Stalled/Warnings ({len(stalled)}) ═══════════╣")
        for s in stalled:
            level_icon = "🔴" if s.get("level") == "stalled" else "🟡"
            src = s.get("source", "").split("/")[-1].replace(".json", "")
            if "days_stale" in s:
                lines.append(f"║  {level_icon} [{src}] {s.get('task_id', s.get('topic_id', '?'))} — {s.get('days_stale', '?')}d stale ║")
            elif "retry_count" in s:
                lines.append(f"║  {level_icon} [{src}] {s['task_id']} — {s['retry_count']} retries ║")

    lines.append(f"║                                              ║")
    lines.append(f"║  Rules: guard-rules.md                       ║")
    lines.append(f"║  State: .claude/state/                       ║")
    lines.append(f"╚══════════════════════════════════════════════╝")
    lines.append(f"")

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────

def main():
    # v5: 构建执行上下文
    context = build_execution_context()

    # Stall detection — v5 primary + v4 legacy fallback
    all_stalled = []

    # v5: current-task.json
    active_task = get_active_task()
    if active_task:
        all_stalled.extend(detect_stalled_current_task(active_task))

    # v5: learning-state.json
    all_stalled.extend(detect_learning_stall())

    # v4 legacy fallback
    if not active_task:
        legacy_tasks = get_legacy_active_tasks()
        if legacy_tasks:
            all_stalled.extend(detect_stalled_legacy(legacy_tasks))

    # Build injection
    if active_task or all_stalled:
        injection = format_guard_injection(context, all_stalled)
        output = {
            "guard_context": context,
            "stalled_count": len(all_stalled),
            "stalled_items": all_stalled,
            "prompt_injection": injection,
        }
    else:
        output = {
            "guard_context": context,
            "stalled_count": 0,
            "stalled_items": [],
        }

    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()

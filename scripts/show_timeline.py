#!/usr/bin/env python3
"""
show_timeline — Skill OS Execution Timeline 查看脚本
TELEMETRY-ONLY: NO_STATE_MUTATION | FAIL_SILENT

用法:
    python scripts/show_timeline.py              # 默认：显示最近一次执行摘要
    python scripts/show_timeline.py summary      # 同上
    python scripts/show_timeline.py events       # 显示 timeline 事件流
    python scripts/show_timeline.py events 20    # 显示最近 20 条事件
    python scripts/show_timeline.py check        # 检查是否有未完成的 workflow

依赖:
    SKILL_OS_TELEMETRY=1 环境变量
    以及 state/telemetry/last-run-summary.json 和 execution-timeline.jsonl 文件
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
TELEMETRY_DIR = REPO_ROOT / ".claude" / "state" / "telemetry"
SUMMARY_FILE = TELEMETRY_DIR / "last-run-summary.json"
TIMELINE_FILE = TELEMETRY_DIR / "execution-timeline.jsonl"
STATUS_FILE = TELEMETRY_DIR / "runtime-status.json"


def _check_enabled() -> bool:
    """检查 telemetry 是否可用"""
    if os.environ.get("SKILL_OS_TELEMETRY", "0") != "1":
        print(
            "⚠️  SKILL_OS_TELEMETRY 未启用。\n"
            "   请先设置: export SKILL_OS_TELEMETRY=1"
        )
        return False
    if not TELEMETRY_DIR.exists():
        print("⚠️  Telemetry 数据目录不存在，尚未记录任何执行数据。")
        return False
    return True


def _load_json(path: Path):
    """安全加载 JSON 文件"""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


# ── Chinese label helpers ──────────────────────────────────

_WORKFLOW_ZH = {
    "delivery_pipeline": "项目交付工作流",
    "debug_pipeline": "故障诊断工作流",
    "learning_pipeline": "学习工作流",
}

_EVENT_ZH = {
    "workflow_started": "工作流开始",
    "workflow_resumed": "工作流恢复",
    "stage_entered": "进入阶段",
    "stage_completed": "阶段完成",
    "stage_failed": "阶段失败",
    "skill_started": "技能启动",
    "heartbeat": "心跳",
    "workflow_completed": "工作流完成",
    "workflow_failed": "工作流失败",
}

_STATUS_ZH = {
    "completed": "已完成",
    "failed": "失败",
    "running": "运行中",
    "interrupted": "中断",
    "idle": "空闲",
}


# ── Mode: summary ──────────────────────────────────────────

def show_summary():
    """显示最近一次执行摘要"""
    if not _check_enabled():
        sys.exit(1)

    summary = _load_json(SUMMARY_FILE)
    if summary is None:
        print("📭 暂无执行记录。")
        return

    workflow = summary.get("workflow", "未知")
    status = summary.get("final_status", "未知")
    stage_idx = summary.get("last_stage_index", 0)
    stage_name = summary.get("last_stage_name", "?")
    skill = summary.get("last_skill", "?")
    duration = summary.get("duration_seconds", 0)
    reason = summary.get("failed_reason", "")
    resumable = summary.get("resumable", False)
    summary_zh = summary.get("summary_zh", "")

    cn_workflow = _WORKFLOW_ZH.get(workflow, workflow)
    cn_status = _STATUS_ZH.get(status, status)

    duration_str = f"{duration}s" if duration > 0 else "N/A"
    if duration >= 60:
        duration_str = f"{duration}s（{duration // 60}分{duration % 60}秒）"

    print()
    print("┌── Last Workflow Run / 最近一次执行 ─────────────────┐")
    print(f"  Workflow : {workflow}")
    print(f"  中文说明 : {cn_workflow}")
    print(f"  Status   : {status}（{cn_status}）")
    print(f"  Stage    : {stage_idx}（{stage_name}）")
    print(f"  Skill    : {skill}")
    print(f"  Duration : {duration_str}")
    if reason:
        print(f"  Reason   : {reason}")
    if summary_zh:
        print(f"  中文摘要 : {summary_zh}")
    print(f"  Resumable: {'是 — 可以从断点继续' if resumable else '否'}")
    print("└──────────────────────────────────────────────────────┘")
    print()

    # Check for unfinished workflow
    if resumable and status != "completed":
        print("⚠️  检测到未完成的工作流，建议从断点继续。")
        print(f"   上次停在: Stage {stage_idx}（{stage_name}），技能 {skill}")
        print()


# ── Mode: events ───────────────────────────────────────────

def show_events(limit: int = 50):
    """显示 timeline 事件流"""
    if not _check_enabled():
        sys.exit(1)

    if not TIMELINE_FILE.exists():
        print("📭 暂无 timeline 事件记录。")
        return

    events = []
    try:
        with open(TIMELINE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except IOError:
        print("❌ 读取 timeline 文件失败。")
        sys.exit(1)

    if not events:
        print("📭 timeline 为空。")
        return

    events = events[-limit:]

    print()
    print(f"┌── Execution Timeline / 执行时间线（最近 {len(events)} 条）{'─' * 20}┐")

    for e in events:
        ts = e.get("ts", "")[:19]  # truncate to seconds
        try:
            dt = datetime.fromisoformat(ts)
            ts_fmt = dt.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            ts_fmt = ts

        event = e.get("event", "?")
        cn_event = _EVENT_ZH.get(event, event)

        stage = e.get("stage_name", "")
        stage_idx = e.get("staging_index", e.get("stage_index", 0))
        skill = e.get("skill", "")
        msg = e.get("message", "")
        msg_zh = e.get("message_zh", "")

        # Build line
        parts = [f"[{ts_fmt}] {event}"]
        if stage:
            parts.append(f"stage={stage_idx} {stage}")
        if skill:
            parts.append(f"skill={skill}")
        if msg and msg != event:
            parts.append(msg)

        print(f"  {' '.join(parts)}")

        # Chinese line
        cn_line = cn_event
        if msg_zh:
            cn_line += f" — {msg_zh}"
        print(f"         中文：{cn_line}")

    print("└──────────────────────────────────────────────────────────────┘")
    print()


# ── Mode: check ────────────────────────────────────────────

def show_check():
    """检查是否有未完成的 workflow"""
    if not _check_enabled():
        sys.exit(1)

    summary = _load_json(SUMMARY_FILE)
    if summary is None:
        print("📭 暂无执行记录。")
        return

    status = summary.get("final_status", "")
    resumable = summary.get("resumable", False)

    if status == "completed":
        print("✅ 上一次执行已成功完成，无需恢复。")
        return

    if resumable:
        workflow = summary.get("workflow", "?")
        cn_workflow = _WORKFLOW_ZH.get(workflow, workflow)
        stage_name = summary.get("last_stage_name", "?")
        skill = summary.get("last_skill", "?")
        reason = summary.get("failed_reason", "")

        print()
        print("⚠️  检测到未完成的工作流：")
        print(f"  Workflow : {workflow}（{cn_workflow}）")
        print(f"  Stage    : {summary.get('last_stage_index', '?')}（{stage_name}）")
        print(f"  Skill    : {skill}")
        print(f"  Status   : {status}")
        if reason:
            print(f"  Reason   : {reason}")
        print()
        print("  中文提示：如果当前任务与上次一致，建议从上述阶段继续，而不是重新开始整个工作流。")
        print()
    else:
        print("📭 没有可恢复的未完成工作流。")


# ── Main ───────────────────────────────────────────────────

def main():
    mode = "summary"
    limit = 50

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("summary", "events", "check"):
            mode = arg
        elif arg.isdigit():
            mode = "events"
            limit = int(arg)
        else:
            print(f"用法: {sys.argv[0]} [summary|events|check] [limit]")
            sys.exit(1)

    if len(sys.argv) > 2:
        try:
            limit = int(sys.argv[2])
        except ValueError:
            pass

    if mode == "summary":
        show_summary()
    elif mode == "events":
        show_events(limit)
    elif mode == "check":
        show_check()


if __name__ == "__main__":
    main()

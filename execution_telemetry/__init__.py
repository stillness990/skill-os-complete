"""
execution_telemetry — Execution Telemetry v2
TELEMETRY-ONLY: NO_STATE_MUTATION | FAIL_SILENT

Skill OS v4/v5 L6 Extension 层：执行过程可视化层。

提供：
- RuntimeTracker — 运行时状态追踪 + CLI 输出 + Timeline 记录
- ResumeManager — 断点恢复检测
- cli_display — 终端格式化输出
- timeline_logger — JSONL 事件日志
- zh_messages — 中文提示模板

启用方式:
    export SKILL_OS_TELEMETRY=1

关闭（默认）:
    export SKILL_OS_TELEMETRY=0
    或 不设置环境变量

架构约束:
- 属 L6 Extension 层，不写入 L4 State 核心文件
- 仅写入 state/telemetry/ 子目录
- 不在 Guard 层注入任何写操作
- Fail-Silent: 所有异常不中断主 Workflow
"""

from execution_telemetry.runtime_tracker import (
    start_workflow,
    enter_stage,
    complete_stage,
    fail_stage,
    set_skill,
    heartbeat,
    complete_workflow,
    fail_workflow,
    get_snapshot,
)

from execution_telemetry.resume_manager import (
    check_unfinished_workflow,
    get_resume_context,
)

from execution_telemetry.cli_display import (
    display_resume_hint,
    display_workflow_started,
    display_stage_entered,
    display_stage_completed,
    display_stage_failed,
    display_skill_started,
    display_heartbeat,
    display_workflow_completed,
    display_workflow_failed,
)

from execution_telemetry.timeline_logger import (
    append_event,
    write_last_run_summary,
    read_last_run_summary,
    read_timeline_events,
)

from execution_telemetry.zh_messages import (
    workflow_started_zh,
    stage_entered_zh,
    stage_completed_zh,
    stage_failed_zh,
    skill_started_zh,
    heartbeat_zh,
    workflow_completed_zh,
    workflow_failed_zh,
    resume_hint_zh,
    router_hint_zh,
    guard_hint_zh,
    completion_pass_zh,
    completion_fail_zh,
)

__all__ = [
    # Runtime tracker API
    "start_workflow",
    "enter_stage",
    "complete_stage",
    "fail_stage",
    "set_skill",
    "heartbeat",
    "complete_workflow",
    "fail_workflow",
    "get_snapshot",
    # Resume manager
    "check_unfinished_workflow",
    "get_resume_context",
    # CLI display
    "display_resume_hint",
    "display_workflow_started",
    "display_stage_entered",
    "display_stage_completed",
    "display_stage_failed",
    "display_skill_started",
    "display_heartbeat",
    "display_workflow_completed",
    "display_workflow_failed",
    # Timeline logger
    "append_event",
    "write_last_run_summary",
    "read_last_run_summary",
    "read_timeline_events",
    # Chinese messages
    "workflow_started_zh",
    "stage_entered_zh",
    "stage_completed_zh",
    "stage_failed_zh",
    "skill_started_zh",
    "heartbeat_zh",
    "workflow_completed_zh",
    "workflow_failed_zh",
    "resume_hint_zh",
    "router_hint_zh",
    "guard_hint_zh",
    "completion_pass_zh",
    "completion_fail_zh",
]

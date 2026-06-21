#!/usr/bin/env python3
"""
Task Ledger — 任务操作脚本（Phase 2 升级）
v4 状态词汇 + 主链接入 ledger/ 模块

用法：
    python task-ops.py list                    # 列出所有任务
    python task-ops.py add <title> [--source] [--workflow] [--task-type]  # 添加任务
    python task-ops.py status <task_id> <new_status>          # 更新状态
    python task-ops.py next                     # 显示下一个待办任务
    python task-ops.py show <task_id>           # 显示任务详情

Phase 2 升级：状态验证统一为 v4 词汇，兼容 v1 旧词汇自动迁移。
Phase 2+：可导入 ledger/task_ledger.py 的 TaskLedgerManager 获得完整功能。
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


LEDGER_FILE = Path(__file__).parent / "tasks.json"

# ── v4 状态词汇定义（与 orchestration_types.py 保持一致）──

_V4_VALID_STATUSES = {
    "queued", "planning", "executing", "blocked",
    "retrying", "stalled", "done", "cancelled",
}

# v1 → v4 兼容映射
_V1_TO_V4 = {
    "in_progress": "executing",
    "retry": "retrying",
}

_STATUS_ICONS = {
    "queued": "⏳", "planning": "📋", "executing": "🔄",
    "blocked": "🚧", "retrying": "🔁", "stalled": "⏸️",
    "done": "✅", "cancelled": "❌",
}

_STATUS_ORDER = {
    "executing": 0, "blocked": 1, "retrying": 2,
    "planning": 3, "queued": 4, "stalled": 5,
    "done": 6, "cancelled": 7,
}

# 终态
_TERMINAL = {"done", "cancelled"}

# 合法转移表 (from → {to})
_LEGAL_TRANSITIONS = {
    "queued": {"planning", "cancelled"},
    "planning": {"executing", "blocked", "done", "cancelled"},
    "executing": {"blocked", "retrying", "done", "cancelled"},
    "blocked": {"planning", "executing", "cancelled"},
    "retrying": {"executing", "blocked", "stalled", "cancelled"},
    "stalled": {"planning", "executing", "cancelled"},
    "done": set(),
    "cancelled": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_status(status: str) -> str:
    """将 v1 词汇转换为 v4，未知状态原样返回"""
    return _V1_TO_V4.get(status, status)


def _is_legal_transition(from_status: str, to_status: str) -> bool:
    """检查状态转移是否合法"""
    return to_status in _LEGAL_TRANSITIONS.get(from_status, set())


def _load() -> dict:
    if not LEDGER_FILE.exists():
        return {
            "meta": {"version": "4.0.0", "project": "", "created": _now(), "updated": _now()},
            "tasks": [],
        }
    with open(LEDGER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    data["meta"]["updated"] = _now()
    # 自动升级 version
    if data["meta"].get("version") in ("1.0.0", None):
        data["meta"]["version"] = "4.0.0"
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _next_id(data: dict) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    existing = [t["task_id"] for t in data["tasks"] if t["task_id"].startswith(f"tsk_{today}")]
    seq = len(existing) + 1
    while f"tsk_{today}_{seq:03d}" in existing:
        seq += 1
    return f"tsk_{today}_{seq:03d}"


def cmd_list(data: dict) -> None:
    tasks = data["tasks"]
    if not tasks:
        print("（无任务）")
        return

    tasks_sorted = sorted(
        tasks,
        key=lambda t: (_STATUS_ORDER.get(t["status"], 9), t.get("created_at", ""))
    )

    for t in tasks_sorted:
        status = _normalize_status(t.get("status", "queued"))
        icon = _STATUS_ICONS.get(status, "❓")
        wf = f" [{t.get('workflow', '')}]" if t.get("workflow") else ""
        print(f"  {icon} [{status}] {t['task_id']}{wf}  {t['title']}")
        if t.get("next_action"):
            print(f"       → {t['next_action']}")


def cmd_add(data: dict, title: str, source: str = "manual",
            workflow: str = "delivery_pipeline", task_type: str = "delivery") -> None:
    task = {
        "task_id": _next_id(data),
        "title": title,
        "task_type": task_type,
        "workflow": workflow,
        "status": "queued",
        "source": source,
        "intent": "",
        "route_id": "",
        "stage_id": "",
        "stage_status": "",
        "next_action": "",
        "artifacts": [],
        "expected_artifacts": [],
        "artifact_paths": [],
        "artifact_refs": {},
        "guard_status": {"last_check_at": None, "stall_detected": False, "warnings": []},
        "retry_count": 0,
        "same_failure_type_count": 0,
        "failure_type": None,
        "safe_mode": False,
        "safe_mode_reason": "",
        "created_at": _now(),
        "updated_at": _now(),
    }
    data["tasks"].append(task)
    _save(data)
    print(f"✓ 已添加任务：{task['task_id']} — {title}")


def cmd_status(data: dict, task_id: str, new_status: str) -> None:
    # 规范化状态（兼容 v1 词汇）
    new_status = _normalize_status(new_status)

    if new_status not in _V4_VALID_STATUSES:
        valid_list = ", ".join(sorted(_V4_VALID_STATUSES))
        print(f"✗ 无效状态：{new_status}，有效状态：{valid_list}")
        sys.exit(1)

    for t in data["tasks"]:
        if t["task_id"] == task_id:
            old = _normalize_status(t.get("status", "queued"))

            # 终态不可逆
            if old in _TERMINAL:
                print(f"✗ 终态任务不可再转移：{old}")
                sys.exit(1)

            # 合法性检查（planning → done 给出警告但允许，因为可能是 plan_only）
            if not _is_legal_transition(old, new_status):
                print(f"✗ 非法状态转移：{old} → {new_status}")
                sys.exit(1)

            t["status"] = new_status
            t["updated_at"] = _now()
            _save(data)
            print(f"✓ {task_id}：{old} → {new_status}")
            return

    print(f"✗ 未找到任务：{task_id}")
    sys.exit(1)


def cmd_next(data: dict) -> None:
    for status in ("executing", "blocked", "retrying", "planning", "queued"):
        for t in data["tasks"]:
            if _normalize_status(t.get("status", "")) == status:
                icon = _STATUS_ICONS.get(status, "")
                print(f"{icon} 下一步：{t['task_id']} — {t['title']}")
                if t.get("next_action"):
                    print(f"    操作：{t['next_action']}")
                return
    print("✓ 所有任务已完成！")


def cmd_show(data: dict, task_id: str) -> None:
    for t in data["tasks"]:
        if t["task_id"] == task_id:
            status = _normalize_status(t.get("status", "queued"))
            print(f"  Task:     {t['task_id']}")
            print(f"  Title:    {t['title']}")
            print(f"  Type:     {t.get('task_type', 'N/A')}")
            print(f"  Workflow: {t.get('workflow', 'N/A')}")
            print(f"  Status:   {status}")
            print(f"  Source:   {t.get('source', 'N/A')}")
            print(f"  Route:    {t.get('route_id', 'N/A')}")
            print(f"  Stage:    {t.get('stage_id', 'N/A')}")
            print(f"  SafeMode: {'ON' if t.get('safe_mode') else 'off'}")
            print(f"  Retries:  {t.get('retry_count', 0)} (same type: {t.get('same_failure_type_count', 0)})")
            if t.get("artifact_paths"):
                print(f"  Artifacts:")
                for ap in t["artifact_paths"]:
                    print(f"    - {ap}")
            if t.get("next_action"):
                print(f"  Next:     {t['next_action']}")
            print(f"  Created:  {t.get('created_at', 'N/A')}")
            print(f"  Updated:  {t.get('updated_at', 'N/A')}")
            return
    print(f"✗ 未找到任务：{task_id}")
    sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2:
        print("用法：python task-ops.py <list|add|status|next|show> [参数...]")
        print()
        print("  list                        列出所有任务")
        print("  add <title>                 添加任务")
        print("    [--source planning|debug|teach-plus|manual]")
        print("    [--workflow delivery_pipeline|debug_pipeline|learning_pipeline]")
        print("    [--task-type delivery|debug|learning|plan_only]")
        print("  status <task_id> <状态>     更新任务状态")
        print("    有效状态(v4): queued planning executing blocked retrying stalled done cancelled")
        print("    兼容旧词汇: in_progress→executing, retry→retrying")
        print("  next                        显示下一个待办任务")
        print("  show <task_id>              显示任务详情")
        sys.exit(1)

    cmd = sys.argv[1]
    data = _load()

    if cmd == "list":
        cmd_list(data)
    elif cmd == "next":
        cmd_next(data)
    elif cmd == "add":
        if len(sys.argv) < 3:
            print("✗ 请提供任务标题")
            sys.exit(1)
        title = sys.argv[2]
        source = "manual"
        workflow = "delivery_pipeline"
        task_type = "delivery"
        args = sys.argv[3:]
        for i, a in enumerate(args):
            if a == "--source" and i + 1 < len(args):
                source = args[i + 1]
            elif a == "--workflow" and i + 1 < len(args):
                workflow = args[i + 1]
            elif a == "--task-type" and i + 1 < len(args):
                task_type = args[i + 1]
        cmd_add(data, title, source=source, workflow=workflow, task_type=task_type)
    elif cmd == "status":
        if len(sys.argv) < 4:
            print("✗ 请提供 task_id 和新状态")
            sys.exit(1)
        cmd_status(data, sys.argv[2], sys.argv[3])
    elif cmd == "show":
        if len(sys.argv) < 3:
            print("✗ 请提供 task_id")
            sys.exit(1)
        cmd_show(data, sys.argv[2])
    else:
        print(f"✗ 未知命令：{cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()

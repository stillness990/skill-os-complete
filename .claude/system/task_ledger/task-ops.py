#!/usr/bin/env python3
"""
Task Ledger — 最小任务操作脚本（Phase 1）

用法：
    python task-ops.py list                    # 列出所有任务
    python task-ops.py add <title> [--source] [--workflow]  # 添加任务
    python task-ops.py status <task_id> <new_status>          # 更新状态
    python task-ops.py next                     # 显示下一个待办任务

Phase 1 最小实现。后续版本可扩展为完整 CLI。
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


LEDGER_FILE = Path(__file__).parent / "tasks.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> dict:
    if not LEDGER_FILE.exists():
        return {"meta": {"version": "1.0.0", "project": "", "created": _now(), "updated": _now()}, "tasks": []}
    with open(LEDGER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    data["meta"]["updated"] = _now()
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

    status_order = {"in_progress": 0, "blocked": 1, "queued": 2, "retry": 3, "done": 4}
    tasks_sorted = sorted(tasks, key=lambda t: (status_order.get(t["status"], 9), t["created_at"]))

    for t in tasks_sorted:
        icon = {"queued": "⏳", "in_progress": "🔄", "blocked": "🚧", "done": "✅", "retry": "🔁"}.get(t["status"], "❓")
        print(f"  {icon} [{t['status']}] {t['task_id']}  {t['title']}")
        if t.get("next_action"):
            print(f"       → {t['next_action']}")


def cmd_add(data: dict, title: str, source: str = "manual", workflow: str = "delivery_pipeline") -> None:
    task = {
        "task_id": _next_id(data),
        "title": title,
        "workflow": workflow,
        "status": "queued",
        "source": source,
        "next_action": "",
        "artifacts": [],
        "created_at": _now(),
        "updated_at": _now(),
    }
    data["tasks"].append(task)
    _save(data)
    print(f"✓ 已添加任务：{task['task_id']} — {title}")


def cmd_status(data: dict, task_id: str, new_status: str) -> None:
    valid = {"queued", "in_progress", "blocked", "done", "retry"}
    if new_status not in valid:
        print(f"✗ 无效状态：{new_status}，有效状态：{', '.join(valid)}")
        sys.exit(1)

    for t in data["tasks"]:
        if t["task_id"] == task_id:
            old = t["status"]
            t["status"] = new_status
            t["updated_at"] = _now()
            _save(data)
            print(f"✓ {task_id}：{old} → {new_status}")
            return

    print(f"✗ 未找到任务：{task_id}")
    sys.exit(1)


def cmd_next(data: dict) -> None:
    # 优先返回 in_progress，其次 blocked，最后 queued
    for status in ("in_progress", "blocked", "queued", "retry"):
        for t in data["tasks"]:
            if t["status"] == status:
                icon = {"in_progress": "🔄", "blocked": "🚧", "queued": "⏳", "retry": "🔁"}.get(status, "")
                print(f"{icon} 下一步：{t['task_id']} — {t['title']}")
                if t.get("next_action"):
                    print(f"    操作：{t['next_action']}")
                return
    print("✓ 所有任务已完成！")


def main() -> None:
    if len(sys.argv) < 2:
        print("用法：python task-ops.py <list|add|status|next> [参数...]")
        print()
        print("  list                    列出所有任务")
        print("  add <title>             添加任务 [--source planning|debug|manual] [--workflow delivery|debug|learning]")
        print("  status <task_id> <状态>  更新任务状态")
        print("  next                    显示下一个待办任务")
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
        # 简单参数解析
        args = sys.argv[3:]
        for i, a in enumerate(args):
            if a == "--source" and i + 1 < len(args):
                source = args[i + 1]
            if a == "--workflow" and i + 1 < len(args):
                workflow = args[i + 1]
        cmd_add(data, title, source=source, workflow=workflow)
    elif cmd == "status":
        if len(sys.argv) < 4:
            print("✗ 请提供 task_id 和新状态")
            sys.exit(1)
        cmd_status(data, sys.argv[2], sys.argv[3])
    else:
        print(f"✗ 未知命令：{cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()

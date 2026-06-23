"""
Task Ledger — 任务账本主模块
Phase 2: 升级版 CRUD + v4 状态机验证 + artifact_paths 安全规则

这是 task-ops.py 的升级版，提供：
- 完整 v4 状态词汇支持
- 状态转移合法性验证
- artifact_paths 安全校验
- CLI 兼容接口
- Python API
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from orchestration.orchestration_types import (
    TaskStatus,
    TaskType,
    Workflow,
    FailureType,
    is_legal_transition,
    normalize_v1_status,
    TERMINAL_STATUSES,
    ACTIVE_STATUSES,
)
from .ledger_schema import (
    TaskEntry,
    TaskLedger,
    ArtifactRefs,
    GuardStatus,
    validate_artifact_path,
    validate_artifact_paths,
    ArtifactPathError,
    _now_iso,
)


# ── 默认账本路径 ──

DEFAULT_LEDGER_PATH = Path(__file__).parent.parent / ".claude" / "system" / "task_ledger" / "tasks.json"


# ── TaskLedgerManager ─────────────────────────────────

class TaskLedgerManager:
    """
    任务账本管理器 — 核心操作入口。

    职责：
    - CRUD
    - 状态转移校验
    - artifact_paths 安全验证
    - 读写 tasks.json
    """

    def __init__(self, ledger_path: Path = DEFAULT_LEDGER_PATH):
        self._path = Path(ledger_path)
        self._ledger: Optional[TaskLedger] = None

    # ── IO ──

    def load(self) -> TaskLedger:
        if not self._path.exists():
            return TaskLedger(
                meta={
                    "version": "4.0.0",
                    "project": "",
                    "created": _now_iso(),
                    "updated": _now_iso(),
                },
                tasks=[],
            )
        with open(self._path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return TaskLedger.from_dict(data, migrate_v1=True)

    @property
    def ledger(self) -> TaskLedger:
        if self._ledger is None:
            self._ledger = self.load()
        return self._ledger

    def reload(self) -> None:
        self._ledger = None

    def save(self) -> None:
        if self._ledger is None:
            return
        self._ledger.meta["updated"] = _now_iso()
        # 自动升级 version 标记
        if self._ledger.meta.get("version") in ("1.0.0", None):
            self._ledger.meta["version"] = "4.0.0"
        data = self._ledger.to_dict()
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ── 查询 ──

    def find_task(self, task_id: str) -> Optional[TaskEntry]:
        return self.ledger.find_task(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> list[TaskEntry]:
        if status:
            return self.ledger.get_tasks_by_status(status)
        return list(self.ledger.tasks)

    def get_active_tasks(self) -> list[TaskEntry]:
        return [t for t in self.ledger.tasks if t.status in ACTIVE_STATUSES]

    def get_next_task(self) -> Optional[TaskEntry]:
        """获取下一个待执行任务"""
        priority = [
            TaskStatus.EXECUTING,
            TaskStatus.BLOCKED,
            TaskStatus.RETRYING,
            TaskStatus.PLANNING,
            TaskStatus.QUEUED,
        ]
        for status in priority:
            for t in self.ledger.tasks:
                if t.status == status:
                    return t
        return None

    # ── 创建 ──

    def add_task(
        self,
        title: str,
        task_type: TaskType = TaskType.DELIVERY,
        workflow: Workflow = Workflow.DELIVERY,
        intent: str = "",
        source: str = "manual",
        next_action: str = "",
        artifacts: Optional[list[str]] = None,
        route_id: str = "",
        stage_id: str = "",
        **extra,
    ) -> TaskEntry:
        """创建新任务"""
        task_id = self._next_task_id()
        task = TaskEntry(
            task_id=task_id,
            title=title,
            task_type=task_type,
            workflow=workflow,
            intent=intent,
            status=TaskStatus.QUEUED,
            source=source,
            next_action=next_action,
            artifacts=artifacts or [],
            route_id=route_id,
            stage_id=stage_id,
            created_at=_now_iso(),
            updated_at=_now_iso(),
            **extra,
        )
        self.ledger.tasks.append(task)
        self.save()
        return task

    # ── 状态转移 ──

    def transition_status(
        self, task_id: str, new_status: TaskStatus
    ) -> tuple[bool, str]:
        """
        执行状态转移。
        返回 (success, message)
        """
        task = self.ledger.find_task(task_id)
        if task is None:
            return False, f"任务不存在: {task_id}"

        # 终态不可逆
        if task.status in TERMINAL_STATUSES:
            return False, f"终态任务不可再转移: {task.status}"

        # 合法性检查
        if not is_legal_transition(task.status, new_status):
            # planning → done 只对 plan_only 合法
            if task.status == TaskStatus.PLANNING and new_status == TaskStatus.DONE:
                if task.task_type == TaskType.PLAN_ONLY:
                    pass  # 允许
                else:
                    return False, (
                        f"非法状态转移: {task.status.value} → {new_status.value} "
                        f"(仅 plan_only 任务允许 planning → done)"
                    )
            else:
                return False, (
                    f"非法状态转移: {task.status.value} → {new_status.value}"
                )

        task.status = new_status
        task.updated_at = _now_iso()
        self.save()
        return True, f"{task_id}: {task.status.value} → {new_status.value}"

    # ── artifact_paths 操作 ──

    def add_artifact_path(self, task_id: str, path: str, repo_root: Optional[Path] = None) -> tuple[bool, str]:
        """
        安全添加 artifact_path。
        如果提供 repo_root，会做边界校验。
        """
        task = self.ledger.find_task(task_id)
        if task is None:
            return False, f"任务不存在: {task_id}"

        if repo_root:
            try:
                validate_artifact_path(path, repo_root)
            except ArtifactPathError as e:
                return False, f"artifact_path 安全校验失败: {e}"

        if path not in task.artifact_paths:
            task.artifact_paths.append(path)
            task.updated_at = _now_iso()
            self.save()
        return True, "ok"

    def get_artifact_paths(self, task_id: str) -> list[str]:
        """获取任务的 artifact_paths"""
        task = self.ledger.find_task(task_id)
        if task is None:
            return []
        return list(task.artifact_paths)

    # ── 重试/失败跟踪 ──

    def record_failure(self, task_id: str, failure_type: FailureType) -> tuple[bool, str]:
        """记录任务失败"""
        task = self.ledger.find_task(task_id)
        if task is None:
            return False, f"任务不存在: {task_id}"

        task.retry_count += 1
        if task.failure_type == failure_type:
            task.same_failure_type_count += 1
        else:
            task.failure_type = failure_type
            task.same_failure_type_count = 1
        task.updated_at = _now_iso()
        self.save()

        # 检查上限
        if task.retry_count > 3:
            return False, f"retry_count 超限 ({task.retry_count} > 3)"
        if task.same_failure_type_count > 2:
            return False, f"same_failure_type_count 超限 ({task.same_failure_type_count} > 2)"

        return True, f"failure 已记录: {failure_type.value}"

    # ── SAFE MODE ──

    def mark_safe_mode(self, task_id: str, reason: str) -> tuple[bool, str]:
        """标记任务进入 SAFE MODE"""
        task = self.ledger.find_task(task_id)
        if task is None:
            return False, f"任务不存在: {task_id}"
        task.safe_mode = True
        task.safe_mode_reason = reason
        task.updated_at = _now_iso()
        self.save()
        return True, "SAFE MODE 已标记"

    # ── 内部工具 ──

    def _next_task_id(self) -> str:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"tsk_{today}"
        existing = [t.task_id for t in self.ledger.tasks if t.task_id.startswith(prefix)]
        seq = len(existing) + 1
        while f"{prefix}_{seq:03d}" in existing:
            seq += 1
        return f"{prefix}_{seq:03d}"


# ── CLI (兼容 task-ops.py) ────────────────────────────

def _status_icon(status: TaskStatus) -> str:
    icons = {
        TaskStatus.QUEUED: "⏳",
        TaskStatus.PLANNING: "📋",
        TaskStatus.EXECUTING: "🔄",
        TaskStatus.BLOCKED: "🚧",
        TaskStatus.RETRYING: "🔁",
        TaskStatus.STALLED: "⏸️",
        TaskStatus.DONE: "✅",
        TaskStatus.CANCELLED: "❌",
    }
    return icons.get(status, "❓")


def cmd_list(mgr: TaskLedgerManager) -> None:
    tasks = mgr.list_tasks()
    if not tasks:
        print("（无任务）")
        return

    status_order = {
        TaskStatus.EXECUTING: 0,
        TaskStatus.BLOCKED: 1,
        TaskStatus.RETRYING: 2,
        TaskStatus.PLANNING: 3,
        TaskStatus.QUEUED: 4,
        TaskStatus.STALLED: 5,
        TaskStatus.DONE: 6,
        TaskStatus.CANCELLED: 7,
    }
    tasks_sorted = sorted(tasks, key=lambda t: (status_order.get(t.status, 9), t.created_at))

    for t in tasks_sorted:
        icon = _status_icon(t.status)
        wf = f" [{t.workflow.value}]" if t.workflow else ""
        print(f"  {icon} [{t.status.value}] {t.task_id}{wf}  {t.title}")
        if t.next_action:
            print(f"       → {t.next_action}")
        if t.artifact_paths:
            print(f"       📦 {', '.join(t.artifact_paths)}")


def cmd_add(mgr: TaskLedgerManager, title: str, source: str = "manual",
            workflow: str = "delivery_pipeline", task_type: str = "delivery") -> None:
    try:
        wf = Workflow(workflow)
    except ValueError:
        print(f"✗ 无效 workflow: {workflow}")
        sys.exit(1)
    try:
        tt = TaskType(task_type)
    except ValueError:
        print(f"✗ 无效 task_type: {task_type}")
        sys.exit(1)

    task = mgr.add_task(title=title, task_type=tt, workflow=wf, source=source)
    print(f"✓ 已添加任务：{task.task_id} — {title}")


def cmd_status(mgr: TaskLedgerManager, task_id: str, new_status_str: str) -> None:
    # 兼容 v1 词汇
    try:
        new_status = TaskStatus(new_status_str)
    except ValueError:
        # 尝试 v1 → v4 迁移
        new_status = normalize_v1_status(new_status_str)
        if new_status == TaskStatus.QUEUED and new_status_str != "queued":
            print(f"✗ 无效状态：{new_status_str}")
            sys.exit(1)

    ok, msg = mgr.transition_status(task_id, new_status)
    if ok:
        print(f"✓ {msg}")
    else:
        print(f"✗ {msg}")
        sys.exit(1)


def cmd_next(mgr: TaskLedgerManager) -> None:
    task = mgr.get_next_task()
    if task is None:
        print("✓ 所有任务已完成！")
        return

    icon = _status_icon(task.status)
    print(f"{icon} 下一步：{task.task_id} — {task.title}")
    if task.next_action:
        print(f"    操作：{task.next_action}")


def cmd_show(mgr: TaskLedgerManager, task_id: str) -> None:
    task = mgr.find_task(task_id)
    if task is None:
        print(f"✗ 未找到任务：{task_id}")
        sys.exit(1)

    print(f"  Task:     {task.task_id}")
    print(f"  Title:    {task.title}")
    print(f"  Type:     {task.task_type.value}")
    print(f"  Workflow: {task.workflow.value if task.workflow else 'N/A'}")
    print(f"  Status:   {task.status.value}")
    print(f"  Source:   {task.source}")
    print(f"  Route:    {task.route_id or 'N/A'}")
    print(f"  Stage:    {task.stage_id or 'N/A'}")
    print(f"  SafeMode: {'ON' if task.safe_mode else 'off'}")
    print(f"  Retries:  {task.retry_count} (same type: {task.same_failure_type_count})")
    if task.artifact_paths:
        print(f"  Artifacts:")
        for ap in task.artifact_paths:
            print(f"    - {ap}")
    if task.next_action:
        print(f"  Next:     {task.next_action}")
    print(f"  Created:  {task.created_at}")
    print(f"  Updated:  {task.updated_at}")


def main() -> None:
    if len(sys.argv) < 2:
        print("用法：python task_ledger.py <list|add|status|next|show> [参数...]")
        print()
        print("  list                        列出所有任务")
        print("  add <title>                 添加任务")
        print("    [--source planning|debug|teach-plus|manual]")
        print("    [--workflow delivery_pipeline|debug_pipeline|learning_pipeline]")
        print("    [--task-type delivery|debug|learning|plan_only]")
        print("  status <task_id> <状态>     更新任务状态")
        print("    有效状态: queued planning executing blocked retrying stalled done cancelled")
        print("  next                        显示下一个待办任务")
        print("  show <task_id>              显示任务详情")
        sys.exit(1)

    cmd = sys.argv[1]
    mgr = TaskLedgerManager()

    if cmd == "list":
        cmd_list(mgr)
    elif cmd == "next":
        cmd_next(mgr)
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
        cmd_add(mgr, title, source=source, workflow=workflow, task_type=task_type)
    elif cmd == "status":
        if len(sys.argv) < 4:
            print("✗ 请提供 task_id 和新状态")
            sys.exit(1)
        cmd_status(mgr, sys.argv[2], sys.argv[3])
    elif cmd == "show":
        if len(sys.argv) < 3:
            print("✗ 请提供 task_id")
            sys.exit(1)
        cmd_show(mgr, sys.argv[2])
    else:
        print(f"✗ 未知命令：{cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()

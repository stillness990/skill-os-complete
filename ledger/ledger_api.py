"""
Ledger API — 可编程查询接口
Phase 2: 提供结构化查询 API 供 resolver/guard/healing 调用

与 CLI (task-ops.py) 的区别：
- CLI 面向人工操作
- API 面向程序模块调用，返回结构化数据
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .ledger_schema import TaskEntry, TaskLedger
from orchestration.orchestration_types import TaskStatus, TaskType, Workflow, FailureType


class LedgerAPI:
    """
    任务账本查询 API。

    用法:
        api = LedgerAPI(Path(".claude/system/task_ledger/tasks.json"))
        tasks = api.get_tasks_by_route("rte_xxx")
        active = api.get_active_tasks()
    """

    def __init__(self, ledger_path: Path):
        self._path = Path(ledger_path)
        self._ledger: Optional[TaskLedger] = None

    # ── 加载/保存 ──

    def _load(self) -> TaskLedger:
        """加载账本（自动迁移 v1 数据）"""
        if not self._path.exists():
            return TaskLedger(
                meta={"version": "4.0.0", "project": "", "created": "", "updated": ""},
                tasks=[],
            )
        with open(self._path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return TaskLedger.from_dict(data, migrate_v1=True)

    @property
    def ledger(self) -> TaskLedger:
        if self._ledger is None:
            self._ledger = self._load()
        return self._ledger

    def reload(self) -> None:
        self._ledger = None

    def save(self) -> None:
        """保存回文件"""
        if self._ledger is None:
            return
        data = self._ledger.to_dict()
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ── 查询 ──

    def get_task(self, task_id: str) -> Optional[TaskEntry]:
        return self.ledger.find_task(task_id)

    def get_all_tasks(self) -> list[TaskEntry]:
        return list(self.ledger.tasks)

    def get_tasks_by_status(self, status: TaskStatus) -> list[TaskEntry]:
        return self.ledger.get_tasks_by_status(status)

    def get_tasks_by_workflow(self, workflow: Workflow) -> list[TaskEntry]:
        return self.ledger.get_tasks_by_workflow(workflow)

    def get_tasks_by_route(self, route_id: str) -> list[TaskEntry]:
        return self.ledger.get_tasks_by_route(route_id)

    def get_active_tasks(self) -> list[TaskEntry]:
        return self.ledger.get_active_tasks()

    def get_stalled_tasks(self) -> list[TaskEntry]:
        """获取停滞任务 (planning/executing 超时)"""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        stalled = []
        for t in self.ledger.tasks:
            if t.status in (TaskStatus.PLANNING, TaskStatus.EXECUTING):
                try:
                    updated = datetime.fromisoformat(
                        t.updated_at.replace("Z", "+00:00")
                    )
                    if now - updated > timedelta(days=3):
                        stalled.append(t)
                except (ValueError, AttributeError):
                    pass
        return stalled

    def get_tasks_by_failure_type(self, failure_type: FailureType) -> list[TaskEntry]:
        return [t for t in self.ledger.tasks if t.failure_type == failure_type]

    def count_retries_for_route(self, route_id: str) -> int:
        tasks = self.get_tasks_by_route(route_id)
        return sum(t.retry_count for t in tasks)

    # ── 写入 ──

    def add_task(self, task: TaskEntry) -> None:
        self.ledger.tasks.append(task)

    def update_task(self, task_id: str, **fields) -> Optional[TaskEntry]:
        """更新任务字段"""
        task = self.ledger.find_task(task_id)
        if task is None:
            return None
        for key, value in fields.items():
            if hasattr(task, key):
                setattr(task, key, value)
        # updated_at 由调用方设置或在此自动更新
        from .ledger_schema import _now_iso
        task.updated_at = _now_iso()
        return task

    def remove_task(self, task_id: str) -> bool:
        """删除任务"""
        task = self.ledger.find_task(task_id)
        if task is None:
            return False
        self.ledger.tasks.remove(task)
        return True

    # ── 批量操作 ──

    def get_artifact_paths_for_route(self, route_id: str) -> list[str]:
        """收集 route 下所有 artifact_paths（供 rollback 使用）"""
        paths = []
        for t in self.get_tasks_by_route(route_id):
            paths.extend(t.artifact_paths)
        return paths

    def count_same_failure_type(self, route_id: str, failure_type: FailureType) -> int:
        """统计同一 route 下同类型失败次数"""
        tasks = self.get_tasks_by_route(route_id)
        return sum(1 for t in tasks if t.failure_type == failure_type)

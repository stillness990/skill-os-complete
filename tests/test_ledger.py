"""
Tests: Task Ledger
Phase 5 — 验证 ledger CRUD, 状态转移, artifact 存储
"""

import sys
import json
import tempfile
from pathlib import Path
import os

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from orchestration.orchestration_types import TaskStatus, TaskType, Workflow, Intent
from ledger.ledger_schema import TaskEntry, TaskLedger


# ── Helpers ──────────────────────────────────────────

def _make_temp_ledger_path():
    """Create a temp file for testing (avoids touching real tasks.json)"""
    fd, path = tempfile.mkstemp(suffix=".json", prefix="test_ledger_")
    import os as _os
    _os.close(fd)
    return path


# ── Tests ────────────────────────────────────────────

def test_create_task_basic():
    """Task can be created with basic fields"""
    print("1. Create task → valid TaskEntry")
    task = TaskEntry(
        task_id="task_001",
        title="Test delivery task",
        task_type=TaskType.DELIVERY,
        workflow=Workflow.DELIVERY,
        status=TaskStatus.QUEUED,
    )
    assert task.task_id == "task_001"
    assert task.title == "Test delivery task"
    assert task.status == TaskStatus.QUEUED
    assert task.workflow == Workflow.DELIVERY
    print(f"  id={task.task_id}, title={task.title}, status={task.status.value}")
    print("  PASS")


def test_task_has_timestamps():
    """Task has created_at and updated_at timestamps"""
    print("2. Task timestamps")
    task = TaskEntry(
        task_id="task_002",
        title="Timestamp test",
        task_type=TaskType.DEBUG,
        workflow=Workflow.DEBUG,
        status=TaskStatus.QUEUED,
    )
    assert task.created_at, "created_at should be set"
    assert task.updated_at, "updated_at should be set"
    print(f"  created={task.created_at}, updated={task.updated_at}")
    print("  PASS")


def test_task_artifacts():
    """Task can store and retrieve artifact paths"""
    print("3. Task artifacts")
    task = TaskEntry(
        task_id="task_003",
        title="Artifact test",
        task_type=TaskType.DELIVERY,
        workflow=Workflow.DELIVERY,
        status=TaskStatus.EXECUTING,
        artifacts=["output/summary.md", "output/plan.md"],
    )
    assert len(task.artifacts) == 2
    assert "output/summary.md" in task.artifacts
    print(f"  artifacts={task.artifacts}")
    print("  PASS")


def test_task_status_transitions():
    """Task status can be updated through valid transitions"""
    print("4. Status transitions")
    task = TaskEntry(
        task_id="task_004",
        title="Transition test",
        task_type=TaskType.DELIVERY,
        workflow=Workflow.DELIVERY,
        status=TaskStatus.QUEUED,
    )
    assert task.status == TaskStatus.QUEUED

    # QUEUED → PLANNING (valid)
    task.status = TaskStatus.PLANNING
    assert task.status == TaskStatus.PLANNING

    # PLANNING → EXECUTING (valid)
    task.status = TaskStatus.EXECUTING
    assert task.status == TaskStatus.EXECUTING

    # EXECUTING → DONE (valid)
    task.status = TaskStatus.DONE
    assert task.status == TaskStatus.DONE
    print(f"  queued→planning→executing→done OK")
    print("  PASS")


def test_task_to_dict():
    """Task can serialize to dict and back"""
    print("5. Task serialization")
    task = TaskEntry(
        task_id="task_005",
        title="Serialization test",
        task_type=TaskType.LEARNING,
        workflow=Workflow.LEARNING,
        intent="learn_topic",
        status=TaskStatus.QUEUED,
        artifacts=["output/learning_brief.md"],
    )
    d = task.to_dict()
    assert d["task_id"] == "task_005"
    assert d["title"] == "Serialization test"
    assert d["status"] == "queued"
    assert d["artifacts"] == ["output/learning_brief.md"]
    print(f"  dict keys: {list(d.keys())}")
    print("  PASS")


def test_ledger_find_task():
    """TaskLedger can find tasks by ID"""
    print("6. Ledger find_task")
    ledger = TaskLedger(
        meta={"version": "4.0.0", "project": "test", "created": "2026-01-01", "updated": "2026-01-01"},
        tasks=[
            TaskEntry(task_id="task_a", title="Task A", task_type=TaskType.DELIVERY, workflow=Workflow.DELIVERY, status=TaskStatus.QUEUED),
            TaskEntry(task_id="task_b", title="Task B", task_type=TaskType.DEBUG, workflow=Workflow.DEBUG, status=TaskStatus.EXECUTING),
        ],
    )
    t = ledger.find_task("task_a")
    assert t is not None
    assert t.title == "Task A"

    t2 = ledger.find_task("task_b")
    assert t2 is not None
    assert t2.status == TaskStatus.EXECUTING

    t3 = ledger.find_task("nonexistent")
    assert t3 is None
    print(f"  found task_a={t.title}, task_b={t2.title}, nonexistent={t3}")
    print("  PASS")


def test_ledger_filter_by_status():
    """TaskLedger can filter by status"""
    print("7. Ledger filter by status")
    ledger = TaskLedger(
        meta={"version": "4.0.0", "project": "test", "created": "2026-01-01", "updated": "2026-01-01"},
        tasks=[
            TaskEntry(task_id="t1", title="Queued", task_type=TaskType.DELIVERY, workflow=Workflow.DELIVERY, status=TaskStatus.QUEUED),
            TaskEntry(task_id="t2", title="Executing", task_type=TaskType.DEBUG, workflow=Workflow.DEBUG, status=TaskStatus.EXECUTING),
            TaskEntry(task_id="t3", title="Done", task_type=TaskType.LEARNING, workflow=Workflow.LEARNING, status=TaskStatus.DONE),
        ],
    )
    queued = ledger.get_tasks_by_status(TaskStatus.QUEUED)
    assert len(queued) == 1
    assert queued[0].task_id == "t1"

    done = ledger.get_tasks_by_status(TaskStatus.DONE)
    assert len(done) == 1
    assert done[0].task_id == "t3"
    print(f"  QUEUED: {len(queued)}, DONE: {len(done)}")
    print("  PASS")


def test_ledger_from_dict_with_v1_migration():
    """TaskLedger.from_dict handles v1→v4 migration"""
    print("8. Ledger v1→v4 migration")
    data = {
        "meta": {"version": "1.0.0", "project": "test", "created": "2026-01-01", "updated": "2026-01-01"},
        "tasks": [
            {
                "task_id": "old_001",
                "title": "Old task",
                "workflow": "delivery_pipeline",
                "status": "in_progress",  # v1 status, migrated to EXECUTING
                "intent": "",
                "source": "manual",
            }
        ],
    }
    ledger = TaskLedger.from_dict(data, migrate_v1=True)
    task = ledger.find_task("old_001")
    assert task is not None
    # v1 "in_progress" → v4 TaskStatus.EXECUTING
    assert task.status == TaskStatus.EXECUTING
    print(f"  v1 'in_progress' → v4 {task.status.value}")
    print("  PASS")


def test_terminal_statuses():
    """DONE and CANCELLED are terminal statuses"""
    print("9. Terminal statuses")
    from orchestration.orchestration_types import TERMINAL_STATUSES
    assert TaskStatus.DONE in TERMINAL_STATUSES
    assert TaskStatus.CANCELLED in TERMINAL_STATUSES
    assert TaskStatus.QUEUED not in TERMINAL_STATUSES
    print(f"  terminal: {[s.value for s in TERMINAL_STATUSES]}")
    print("  PASS")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 5 — Task Ledger Tests")
    print("=" * 60)
    print()
    test_create_task_basic()
    print()
    test_task_has_timestamps()
    print()
    test_task_artifacts()
    print()
    test_task_status_transitions()
    print()
    test_task_to_dict()
    print()
    test_ledger_find_task()
    print()
    test_ledger_filter_by_status()
    print()
    test_ledger_from_dict_with_v1_migration()
    print()
    test_terminal_statuses()
    print()
    print("=" * 60)
    print("ALL LEDGER TESTS PASSED")
    print("=" * 60)

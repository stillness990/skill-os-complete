#!/usr/bin/env python3
"""
Skill OS v4 — Task Guard Hook（任务状态变更校验）
触发时机: task_ledger 任务状态更新前（PreToolUse 或 UserPromptSubmit）
作用:    校验状态流转合法性 + artifact 检查
状态:    v4.0.0 占位 — 完整逻辑待 Phase 4+ 实现

接入点：
  此 hook 在 skill-router 注入后、任务状态实际变更前执行。
  当前版本输出 guard 校验结果注入到 prompt context 中。
  后续版本将直接拦截非法状态变更。

校验规则引用：
  - .claude/system/execution_guard/task-state-machine.md
  - .claude/system/execution_guard/artifact-requirements.md
  - .claude/system/execution_guard/guard-rules.md
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


CLAUDE_DIR = Path(__file__).parent.parent
LEDGER_FILE = CLAUDE_DIR / "system" / "task_ledger" / "tasks.json"
GUARD_DIR = CLAUDE_DIR / "system" / "execution_guard"


def load_ledger():
    """加载任务账本。"""
    if not LEDGER_FILE.exists():
        return None
    with open(LEDGER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_active_tasks(ledger: dict) -> list:
    """获取所有非终态任务。"""
    if not ledger:
        return []
    return [t for t in ledger.get("tasks", []) if t.get("status") not in ("done", "cancelled")]


def get_stalled_tasks(ledger: dict) -> list:
    """检测卡住的任务。"""
    if not ledger:
        return []
    now = datetime.now(timezone.utc)
    stalled = []
    for t in ledger.get("tasks", []):
        status = t.get("status", "")
        if status in ("done", "cancelled"):
            continue
        try:
            updated = datetime.fromisoformat(t.get("updated_at", ""))
        except (ValueError, TypeError):
            continue
        days_since = (now - updated).days
        if status in ("planning", "executing") and days_since >= 7:
            stalled.append({
                "task_id": t["task_id"],
                "title": t.get("title", ""),
                "status": status,
                "days_stale": days_since,
                "advice": "建议检查是否卡住，考虑标记 stalled 或更新进度"
            })
        elif status in ("planning", "executing") and days_since >= 3:
            stalled.append({
                "task_id": t["task_id"],
                "title": t.get("title", ""),
                "status": status,
                "days_stale": days_since,
                "advice": "建议更新任务进度"
            })
    return stalled


def main():
    # Phase 1: 最小占位 — 输出当前任务状态摘要
    ledger = load_ledger()
    if not ledger:
        print(json.dumps({}))
        sys.exit(0)

    active = get_active_tasks(ledger)
    stalled = get_stalled_tasks(ledger)

    guard_context = {
        "active_tasks": len(active),
        "stalled_warnings": stalled,
        "guard_rules_ref": str(GUARD_DIR / "guard-rules.md"),
        "state_machine_ref": str(GUARD_DIR / "task-state-machine.md"),
    }

    # 如果有 stalled 任务，生成警告注入
    if stalled:
        stall_lines = "\n".join(
            f"  ⚠️ {s['task_id']}: {s['title']} — {s['days_stale']}天未更新 ({s['status']}) → {s['advice']}"
            for s in stalled
        )
        injection = (
            f"\n╔══ EXECUTION GUARD (v4) ═══════════════╗\n"
            f"║  监督状态：{len(active)} 个活跃任务            ║\n"
            f"║  ⚠️  {len(stalled)} 个任务可能卡住：            ║\n"
            f"{stall_lines}\n"
            f"╚══════════════════════════════════════════╝\n"
        )
        print(json.dumps({"prompt_injection": injection}))
    else:
        print(json.dumps({}))


if __name__ == "__main__":
    main()

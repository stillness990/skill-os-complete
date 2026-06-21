#!/usr/bin/env python3
"""
Skill OS v4 — Completion Guard Hook（任务完成校验）
触发时机: 任务被标记为 done 前 / conversation 结束前
作用:    校验 done 条件是否满足（artifact / 状态流转 / 最小产物）
状态:    v4.0.0 占位 — 完整逻辑待 Phase 4+ 实现

接入点：
  此 hook 在任务进入 done 状态前执行。
  当前版本：检测到 done 意图时，注入 artifact 检查提示。
  后续版本：直接拦截不满足条件的 done 请求。

校验规则引用：
  - .claude/system/execution_guard/artifact-requirements.md
  - .claude/system/execution_guard/audit-checklist.md
  - .claude/system/execution_guard/guard-rules.md
"""

import json
import os
import sys
from pathlib import Path


CLAUDE_DIR = Path(__file__).parent.parent
GUARD_DIR = CLAUDE_DIR / "system" / "execution_guard"


def check_done_conditions(task: dict) -> list:
    """检查任务是否满足 done 条件。返回缺失项列表。"""
    missing = []

    # Rule 1: artifact 非空
    artifacts = task.get("artifacts", [])
    if not artifacts:
        missing.append("artifacts 为空 — done 必须至少有一个产物")

    # Rule 2: result_summary 非空
    summary = task.get("artifact_refs", {}).get("result_summary", "")
    if not summary or len(summary) < 10:
        missing.append("result_summary 缺失或过短 — done 必须有结果描述")

    # Rule 3: task_type 特定检查
    task_type = task.get("task_type", "")
    refs = task.get("artifact_refs", {})

    if task_type == "debug":
        if not refs.get("debug_report_ref"):
            missing.append("debug 类任务缺少 debug_report_ref")
        if not refs.get("root_cause"):
            missing.append("debug 类任务缺少 root_cause")

    elif task_type == "delivery":
        if not refs.get("plan_ref"):
            missing.append("delivery 类任务缺少 plan_ref")
        if not task.get("changed_files") and not refs.get("changed_files"):
            # 检查是否施工类
            title = task.get("title", "").lower()
            if any(kw in title for kw in ["实施", "重构", "修改", "创建", "部署", "implement", "refactor", "fix"]):
                missing.append("施工类 delivery 任务缺少 changed_files — 必须有落地证据")

    elif task_type == "learning":
        if not refs.get("next_action"):
            missing.append("learning 类任务缺少 next_action")

    return missing


def main():
    # Phase 1 最小占位：输出 done 检查清单注入
    injection = (
        f"\n╔══ COMPLETION GUARD (v4) ═══════════════╗\n"
        f"║  任务完成前请确认：                      ║\n"
        f"║  1. artifacts 数组非空                  ║\n"
        f"║  2. result_summary 有意义              ║\n"
        f"║  3. 状态流转合法（非跳步骤完成）         ║\n"
        f"║  4. task_type 对应 minimal artifact    ║\n"
        f"║  5. 施工任务有 changed_files           ║\n"
        f"║  规则详见：                             ║\n"
        f"║  {str(GUARD_DIR / 'guard-rules.md'):<36}║\n"
        f"║  {str(GUARD_DIR / 'audit-checklist.md'):<36}║\n"
        f"╚══════════════════════════════════════════╝\n"
    )
    print(json.dumps({"prompt_injection": injection}))


if __name__ == "__main__":
    main()

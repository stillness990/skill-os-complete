#!/usr/bin/env python3
"""
Skill OS v5 — Completion Guard Hook（任务完成校验）
触发时机: 任务被标记为 done 前 / conversation 结束前
作用:    强制执行 done 条件校验（artifact / 状态流转 / 最小产物 / knowledge-asset / state）
状态:    v5.0.0 — 从 v4 占位升级为强制执行层

v5 核心升级:
  - 主数据源从 system/task_ledger/tasks.json → state/current-task.json
  - 新增 knowledge_asset_ref 强制检查（L0 Knowledge Bus 闭环）
  - 新增 state/ 更新检查（L4 State 闭环）
  - 输出从 prompt_injection 占位 → 结构化 validation_result (pass/fail + missing)

校验规则引用:
  - .claude/system/execution_guard/guard-rules.md
  - .claude/system/execution_guard/artifact-requirements.md
  - .claude/system/execution_guard/audit-checklist.md
  - .claude/system/execution_guard/task-state-machine.md
  - .claude/state/README.md
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


CLAUDE_DIR = Path(__file__).parent.parent
GUARD_DIR = CLAUDE_DIR / "system" / "execution_guard"
STATE_DIR = CLAUDE_DIR / "state"

# v5 primary sources
CURRENT_TASK_FILE = STATE_DIR / "current-task.json"
EXECUTION_STATE_FILE = STATE_DIR / "execution-state.json"

# v4 legacy fallback
LEGACY_LEDGER_FILE = CLAUDE_DIR / "system" / "task_ledger" / "tasks.json"

# Knowledge-asset output directory (for ref validation)
KNOWLEDGE_DIR = CLAUDE_DIR / "skills" / "knowledge-asset" / "knowledge"


def load_current_task():
    """v5: 加载当前活跃任务 (state/current-task.json)。"""
    if CURRENT_TASK_FILE.exists():
        try:
            with open(CURRENT_TASK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("active_task")
        except (json.JSONDecodeError, IOError):
            pass
    return None


def load_legacy_active_tasks():
    """v4 legacy fallback: 从 tasks.json 获取活跃任务。"""
    if not LEGACY_LEDGER_FILE.exists():
        return []
    try:
        with open(LEGACY_LEDGER_FILE, "r", encoding="utf-8") as f:
            ledger = json.load(f)
        return [t for t in ledger.get("tasks", []) if t.get("status") not in ("done", "cancelled")]
    except (json.JSONDecodeError, IOError):
        return []


def load_execution_state():
    """加载执行状态。"""
    if EXECUTION_STATE_FILE.exists():
        try:
            with open(EXECUTION_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return None


def validate_state_transition(task: dict, target_status: str = "done") -> list:
    """校验状态流转合法性（Rule 2）。返回违规列表。"""
    violations = []
    current_status = task.get("status", "")
    task_type = task.get("task_type", "")

    # 非法流转定义 (from task-state-machine.md)
    ILLEGAL_TRANSITIONS = {
        ("queued", "done"): "跳过 planning 和 executing，属于跳步骤完成",
        ("queued", "executing"): "跳过 planning，没有计划就开始执行",
        ("blocked", "done"): "阻塞状态下不能直接完成，必须先恢复执行",
        ("retrying", "done"): "重试状态下不能直接完成，必须回到 executing",
        ("stalled", "done"): "卡住的任务不能直接标完成，必须先恢复",
        ("done",): "终态不可逆",
        ("cancelled",): "终态不可逆",
    }

    # Check for terminal state reversal
    if current_status in ("done", "cancelled"):
        violations.append(f"非法流转: {current_status} 是终态，不可再变更为 {target_status}")
        return violations

    # Check specific transition
    key = (current_status, target_status)
    if key in ILLEGAL_TRANSITIONS:
        violations.append(f"非法流转 ({current_status} → {target_status}): {ILLEGAL_TRANSITIONS[key]}")

    # Special: planning → done only for plan_only
    if current_status == "planning" and target_status == "done" and task_type != "plan_only":
        violations.append(
            f"非法流转 (planning → done): 仅 plan_only 类型允许。当前 task_type={task_type}，必须经过 executing"
        )

    return violations


def check_knowledge_asset_ref(task: dict, task_type: str) -> list:
    """v5: 检查 knowledge-asset 沉淀引用（L0 Knowledge Bus 闭环）。"""
    missing = []
    outputs = task.get("outputs", {})
    ka_ref = outputs.get("knowledge_asset_ref", "")

    # 判断该 task_type 是否需要 knowledge-asset 沉淀
    if task_type in ("debug", "learning"):
        # 强制: debug→troubleshooting, learning→knowledge-note
        if not ka_ref:
            missing.append(
                f"[v5 L0] {task_type} 类任务缺少 knowledge_asset_ref — "
                f"诊断/学习产出必须通过 knowledge-asset 沉淀"
            )
        elif not _ref_file_exists(ka_ref):
            missing.append(
                f"[v5 L0] knowledge_asset_ref '{ka_ref}' 指向的文件不存在或无法验证"
            )

    elif task_type == "delivery":
        # 推荐（施工类强制）
        title = task.get("title", "").lower()
        is_construction = any(kw in title for kw in
            ["实施", "重构", "修改", "创建", "部署", "实现", "构建",
             "implement", "refactor", "fix", "build", "create"])
        if is_construction and not ka_ref:
            missing.append(
                "[v5 L0] 施工类 delivery 任务建议通过 knowledge-asset 沉淀 (project-plan)"
            )

    return missing


def check_state_update(task: dict) -> list:
    """v5: 检查 state/ 更新（L4 State 闭环）。"""
    missing = []
    task_type = task.get("task_type", "")

    # 检查 execution-state.json 是否反映了此任务
    exec_state = load_execution_state()
    if exec_state:
        active_task_id = exec_state.get("active_task_id")
        if active_task_id and active_task_id == task.get("task_id"):
            # execution-state 已追踪此任务 — 检查是否已更新
            guard_status = exec_state.get("guard_status", "")
            if guard_status != "passed":
                missing.append(
                    f"[v5 L4] execution-state.json guard_status={guard_status}，"
                    f"done 前建议通过 validation"
                )
    else:
        missing.append("[v5 L4] execution-state.json 不存在 — state 系统未初始化")

    # 对 learning 类型，额外检查 learning-state.json
    if task_type == "learning":
        learning_state_file = STATE_DIR / "learning-state.json"
        if learning_state_file.exists():
            try:
                with open(learning_state_file, "r", encoding="utf-8") as f:
                    ls = json.load(f)
                topics = ls.get("topics", [])
                if not topics:
                    missing.append(
                        "[v5 L4] learning-state.json 中无学习主题记录 — "
                        "learning 任务 done 前应更新 learning-state"
                    )
                else:
                    # 检查是否有 topic 的 last_activity_at 是最近的
                    now = datetime.now(timezone.utc)
                    recent = False
                    for t in topics:
                        try:
                            last = datetime.fromisoformat(t.get("last_activity_at", ""))
                            if (now - last).days < 7:
                                recent = True
                                break
                        except (ValueError, TypeError):
                            pass
                    if not recent:
                        missing.append(
                            "[v5 L4] learning-state.json 中无最近 7 天活动记录 — "
                            "learning 任务 done 前应更新学习进度"
                        )
            except (json.JSONDecodeError, IOError):
                missing.append("[v5 L4] learning-state.json 读取失败")

    return missing


def check_artifacts(task: dict) -> list:
    """检查通用 artifact 要求（Rule 1 + Rule 4）。"""
    missing = []
    task_type = task.get("task_type", "")
    outputs = task.get("outputs", {})
    artifacts = task.get("artifacts", [])

    # Rule 1: artifacts 非空
    if not artifacts and not outputs.get("changed_files"):
        missing.append("artifacts 为空 — done 必须至少有一个产物")

    # Rule 1: result_summary 非空
    summary = outputs.get("result_summary", "")
    if not summary or len(str(summary)) < 10:
        missing.append("result_summary 缺失或过短 (< 10 字符) — done 必须有结果描述")

    # Rule 4: changed_files for construction tasks
    title = task.get("title", "").lower()
    is_construction = any(kw in title for kw in
        ["实施", "重构", "修改", "创建", "部署", "实现", "构建",
         "implement", "refactor", "fix", "build", "create"])
    if is_construction and task_type == "delivery":
        changed = outputs.get("changed_files", [])
        if not changed:
            missing.append("施工类 delivery 任务缺少 changed_files — 必须有落地证据")

    return missing


def check_task_type_artifacts(task: dict) -> list:
    """按 task_type 检查最小 artifact 要求（Rule 3）。"""
    missing = []
    task_type = task.get("task_type", "")
    outputs = task.get("outputs", {})

    if task_type == "debug":
        if not outputs.get("debug_report_ref"):
            missing.append("debug 类任务缺少 debug_report_ref")
        # root_cause might be in result_summary or as separate field
        summary = str(outputs.get("result_summary", "")).lower()
        if "根因" not in summary and "root cause" not in summary and "原因" not in summary:
            missing.append("debug 类任务缺少 root_cause（根因描述）")

    elif task_type == "delivery":
        if not outputs.get("plan_ref"):
            missing.append("delivery 类任务缺少 plan_ref")

    elif task_type == "learning":
        if not outputs.get("next_action") and not task.get("next_action"):
            missing.append("learning 类任务缺少 next_action")

    return missing


def _ref_file_exists(ref: str) -> bool:
    """验证引用路径是否指向存在的文件。"""
    if not ref:
        return False
    # Try relative to project root
    candidate = CLAUDE_DIR.parent / ref
    if candidate.exists():
        return True
    # Try relative to CLAUDE_DIR
    candidate = CLAUDE_DIR / ref
    if candidate.exists():
        return True
    # knowledge-asset refs are relative to knowledge/
    if ref.startswith("knowledge/"):
        candidate = CLAUDE_DIR / "skills" / "knowledge-asset" / ref
        if candidate.exists():
            return True
    return False


def run_validation(task: dict) -> dict:
    """执行完整的 done 条件校验（v5 5 层检查）。"""
    task_type = task.get("task_type", "")
    task_id = task.get("task_id", "unknown")

    all_missing = []
    warnings = []

    # Layer 1: 状态流转合法性
    transition_violations = validate_state_transition(task, "done")
    all_missing.extend(transition_violations)

    # Layer 2: 通用 artifact 检查
    all_missing.extend(check_artifacts(task))

    # Layer 3: task_type 特定 artifact 检查
    all_missing.extend(check_task_type_artifacts(task))

    # Layer 4: v5 L0 knowledge-asset 检查
    ka_missing = check_knowledge_asset_ref(task, task_type)
    all_missing.extend(ka_missing)

    # Layer 5: v5 L4 state/ 更新检查
    state_missing = check_state_update(task)
    # state checks are warnings for non-learning, errors for learning
    if task_type == "learning":
        all_missing.extend(state_missing)
    else:
        warnings.extend(state_missing)

    passed = len(all_missing) == 0

    return {
        "task_id": task_id,
        "validation_passed": passed,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "layers_checked": [
            "state_transition",
            "generic_artifacts",
            "task_type_artifacts",
            "v5_knowledge_asset (L0)",
            "v5_state_update (L4)",
        ],
        "missing_items": all_missing,
        "warnings": warnings,
        "recommendation": (
            "✅ 所有检查通过，可以标记为 done"
            if passed
            else f"❌ {len(all_missing)} 项未通过，建议修复后再 done"
        ),
        "rules_ref": str(GUARD_DIR / "guard-rules.md"),
    }


def format_injection(result: dict) -> str:
    """将 validation result 格式化为 prompt injection 文本。"""
    task_id = result["task_id"]
    passed = result["validation_passed"]
    missing = result["missing_items"]
    warnings = result.get("warnings", [])

    status_icon = "✅" if passed else "❌"
    lines = [
        f"",
        f"╔══ COMPLETION GUARD (v5) ═══════════════════╗",
        f"║  Task: {task_id:<34}║",
        f"║  Status: {status_icon} {'PASSED' if passed else 'FAILED':<32}║",
        f"║  Layers: state→artifacts→type→L0(ka)→L4(state) ║",
    ]

    if missing:
        lines.append(f"╠══ Missing Items ({len(missing)}) ═══════════════════╣")
        for i, item in enumerate(missing):
            # Truncate long messages to fit
            text = item if len(item) <= 52 else item[:49] + "..."
            lines.append(f"║  [{i+1}] {text:<48}║")

    if warnings:
        lines.append(f"╠══ Warnings ({len(warnings)}) ═══════════════════════╣")
        for i, w in enumerate(warnings):
            text = w if len(w) <= 52 else w[:49] + "..."
            lines.append(f"║  ⚠️  {text:<47}║")

    lines.append(f"║                                              ║")
    lines.append(f"║  Rules: guard-rules.md                       ║")
    lines.append(f"║  Checklist: audit-checklist.md               ║")
    lines.append(f"╚══════════════════════════════════════════════╝")

    # ── Chinese hint ──────────────────────────────────
    if passed:
        lines.append(f"中文提示：完成检查已通过，可以进入任务收尾或状态更新。")
    else:
        lines.append(f"中文提示：当前还不能标记为完成，有 {len(missing)} 项校验未通过，请检查交付物或状态文件。")
    lines.append(f"")

    return "\n".join(lines)


def main():
    # v5: 主数据源 — state/current-task.json
    task = load_current_task()

    # v4 legacy fallback
    if not task:
        legacy_tasks = load_legacy_active_tasks()
        if legacy_tasks:
            # Use the first active legacy task
            task = legacy_tasks[0]
            # Normalize v4→v5 field mapping
            if "outputs" not in task:
                task["outputs"] = task.get("artifact_refs", {})

    if not task:
        # No active task — nothing to guard
        print(json.dumps({
            "active_task": None,
            "message": "v5 completion-guard: 无活跃任务，跳过校验",
        }))
        sys.exit(0)

    # Run full v5 validation
    result = run_validation(task)

    # Output structured JSON + prompt injection
    injection = format_injection(result)
    output = {
        "validation_result": result,
        "prompt_injection": injection,
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()

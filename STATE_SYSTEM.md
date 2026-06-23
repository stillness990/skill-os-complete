# Skill OS v5 — 状态系统

> 版本：v5.0.0 | 生成：2026-06-22 | Phase 8 最终交付

---

## 一、概述

Skill OS v5 的状态系统（L4 State）是所有运行时状态的**单一真实来源**（Single Source of Truth）。v5 将 v4 分散在 `system/task_ledger/`、`system/learning_state/`、`system/execution_guard/` 的状态统一到 `.claude/state/` 目录。

### v4 → v5 统一

```
v4 (分散 3 处):
  system/task_ledger/tasks.json          → 任务状态
  system/learning_state/state.json       → 学习状态
  system/execution_guard/ (规则+逻辑)     → 执行状态 (无统一数据文件)

v5 (统一 1 处):
  .claude/state/
  ├── current-task.json      → 任务状态 (活跃)
  ├── task-history.json      → 任务状态 (归档)
  ├── learning-state.json    → 学习状态
  ├── execution-state.json   → 执行状态 (新建)
  └── checkpoint/            → 状态快照 (新建)
```

---

## 二、状态文件详解

### 2.1 current-task.json — 当前任务

**职责**：追踪当前正在执行的唯一活跃任务。

**Schema**：
```json
{
  "meta": {
    "version": "5.0.0",
    "updated_at": "ISO8601"
  },
  "active_task": {
    "task_id": "tsk_YYYYMMDD_NNN",
    "title": "任务标题",
    "task_type": "delivery | debug | learning | plan_only",
    "workflow": "delivery_pipeline | debug_pipeline | learning_pipeline",
    "current_skill": "当前执行的 skill",
    "phase": "当前阶段描述",
    "progress": "进度描述",
    "status": "queued | planning | executing | blocked | retrying | stalled",
    "blockers": ["阻塞原因"],
    "outputs": {
      "knowledge_asset_ref": "knowledge/...",
      "changed_files": ["..."],
      "plan_ref": "...",
      "debug_report_ref": "...",
      "result_summary": "..."
    },
    "next_action": "下一步操作",
    "validation_status": "pending | passed | failed",
    "retry_count": 0,
    "created_at": "ISO8601",
    "updated_at": "ISO8601",
    "last_activity_at": "ISO8601"
  }
}
```

**操作约定**：
- 一次只应有一个活跃任务（`active_task` 非 null）
- 任务 done/cancelled 后自动移至 `task-history.json`
- 新任务创建时覆盖 `active_task`

**写入者**：planning, debug, teach-plus, task_ledger
**读取者**：execution_guard, router, 所有 skill

---

### 2.2 task-history.json — 任务历史

**职责**：已完成/已取消任务的只读归档索引。

**Schema**：
```json
{
  "meta": {
    "version": "5.0.0",
    "total_archived": 0,
    "migrated_from": "system/task_ledger/tasks.json",
    "updated_at": "ISO8601"
  },
  "history": [
    {
      "task_id": "tsk_YYYYMMDD_NNN",
      "title": "...",
      "task_type": "...",
      "workflow": "...",
      "status": "done | cancelled",
      "artifacts": ["..."],
      "result_summary": "...",
      "retry_count": 0,
      "created_at": "ISO8601",
      "updated_at": "ISO8601",
      "archived_at": "ISO8601"
    }
  ]
}
```

**写入者**：execution_guard（任务终态时自动归档）
**读取者**：summarize, changelog, knowledge-asset

---

### 2.3 learning-state.json — 学习状态

**职责**：追踪所有学习主题的宏观进度（7 阶段状态机）。

**Schema**：
```json
{
  "meta": {
    "version": "5.0.0",
    "migrated_from": "system/learning_state/state.json",
    "updated_at": "ISO8601"
  },
  "topics": [
    {
      "topic_id": "learn_YYYYMMDD_NNN",
      "topic_name": "学习主题名称",
      "current_stage": "topic_new | understanding | guided_practice | independent_practice | consolidation | review_due | mastered",
      "current_phase": "当前阶段人类可读描述",
      "plan_ref": "学习计划路径",
      "review_ref": "复盘路径",
      "last_activity_at": "ISO8601",
      "next_action": "下一步学习建议",
      "next_review": "ISO8601",
      "knowledge_assets": ["knowledge/knowledge-notes/... (v5 新增)"],
      "created_at": "ISO8601",
      "updated_at": "ISO8601"
    }
  ]
}
```

**v5 新增字段**：
- `knowledge_assets[]` — 关联的 knowledge-asset 产出路径列表，追踪学习过程中产出的所有知识笔记。

**写入者**：teach-plus (explain/practice/review)
**读取者**：teach-plus, execution_guard, summarize

---

### 2.4 execution-state.json — 执行状态

**职责**：追踪系统级执行进度 — pipeline 推进 + guard 状态 + 降级标记。

**Schema**：
```json
{
  "meta": {
    "version": "5.0.0",
    "updated_at": "ISO8601"
  },
  "active_workflow": "delivery_pipeline | debug_pipeline | learning_pipeline | null",
  "active_task_id": "tsk_...",
  "pipeline_progress": {
    "current_stage_index": 2,
    "total_stages": 8,
    "stages": [
      {
        "name": "summarize",
        "status": "completed | executing | pending | failed | skipped",
        "skill": "summarize",
        "started_at": "ISO8601 | null",
        "completed_at": "ISO8601 | null",
        "knowledge_asset_ref": "knowledge/... | null"
      }
    ]
  },
  "guard_status": "idle | pending | passed | failed",
  "safe_mode": false,
  "safe_mode_reason": null,
  "degraded": false,
  "degraded_reason": null,
  "last_checkpoint_at": "ISO8601 | null",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

**Pipeline 模板**（预置在 `_schema.pipeline_templates` 中）：
| Pipeline | Stages |
|----------|--------|
| `delivery_pipeline` | summarize → planning → task_ledger → code_assistant → reviewer → changelog → knowledge_asset → execution_guard |
| `debug_pipeline` | summarize(optional) → debug → code_assistant → knowledge_asset → execution_guard |
| `learning_pipeline` | summarize → planning → teach-plus/explain → teach-plus/practice → task_ledger → learning_state → teach-plus/review → knowledge_asset → execution_guard |

**写入者**：workflow 推进逻辑, execution_guard
**读取者**：router, 所有 skill, execution_guard

---

## 三、状态机详解

### 3.1 Task 状态机（8 状态）

```
                    ┌──────────────┐
                    │    queued    │  初始状态
                    └──┬───────┬──┘
                       │       │
              ┌────────▼──┐    │
              │ planning  │    │
              └──┬───┬───┬┘    │
                 │   │   │     │
    ┌────────────▼┐  │   │     │
    │  executing  │  │   │     │
    └──┬──┬──┬──┬─┘  │   │     │
       │  │  │  │    │   │     │
       │  │  │  └────┼───┼─────┼──→ done (终态)
       │  │  │       │   │     │
       │  │  └──→ blocked ←───┼──→ cancelled (终态)
       │  │       │   │       │
       │  └──→ retrying │     │
       │          │   │       │
       └─────→ stalled ←─────┘
```

**合法流转表**：

| 从 ↓ / 到 → | queued | planning | executing | blocked | retrying | stalled | done | cancelled |
|-------------|--------|----------|-----------|---------|----------|---------|------|-----------|
| **queued** | — | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **planning** | ❌ | — | ✅ | ✅ | ❌ | ❌ | ✅¹ | ✅ |
| **executing** | ❌ | ❌ | — | ✅ | ✅ | ❌ | ✅ | ✅ |
| **blocked** | ❌ | ✅ | ✅ | — | ❌ | ❌ | ❌ | ✅ |
| **retrying** | ❌ | ❌ | ✅ | ✅ | — | ❌ | ❌ | ✅ |
| **stalled** | ❌ | ✅ | ✅ | ❌ | ❌ | — | ❌ | ✅ |
| **done** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | — | ❌ |
| **cancelled** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | — |

> ¹ `planning → done` 仅 `task_type = "plan_only"` 合法

**非法流转（L5 Guard 拦截）**：
- `queued → done`：跳过 planning+executing
- `queued → executing`：跳过 planning
- `planning → done` (非 plan_only)：必须经过 executing
- `blocked → done`：未恢复执行
- `retrying → done`：未回到 executing
- `stalled → done`：未恢复活动
- 终态 → 任意：不可逆

---

### 3.2 Learning Topic 状态机（7 阶段）

```
topic_new ──→ understanding ──→ guided_practice ──→ independent_practice
                                                          │
                                                          ▼
                                                    consolidation
                                                          │
                                                          ▼
                                                     review_due
                                                          │
                                                          ▼
                                                       mastered (终态)
```

**异常状态**：

| 状态 | 触发条件 | 恢复路径 |
|------|---------|---------|
| `paused` | 用户主动暂停 | → 原状态（恢复） |
| `stalled` | 7 天未活动 | → `understanding` 或 `restart_needed` |
| `restart_needed` | 长期断档 + 知识遗忘 | → `topic_new`（重新开始） |

**teach-plus 模式操作**：

| 模式 | 状态操作 | 说明 |
|------|---------|------|
| `explain` | `topic_new → understanding` | 创建 topic + 建立概念框架 |
| `practice` | `understanding → guided_practice` / `guided_practice → independent_practice` | 更新 last_activity_at + next_action |
| `review` | 推进至 `consolidation` / `review_due` / `mastered` | 更新 review_ref + next_review |

---

### 3.3 Pipeline 状态机

```
not_started → in_progress → completed
                        ↘ failed → retrying → in_progress
                                 ↘ safe_mode → degraded_completed
```

**Safe Mode 触发条件**：
- 同一 failure_type 连续 3 次
- artifact_missing 连续 2 次
- 用户手动触发 /safe

**Degraded 标记**：
- 非关键 stage 失败但不影响整体交付
- 降级完成仍记录 degraded_completed

---

## 四、Checkpoint 机制

### 4.1 触发条件

| 触发条件 | 说明 |
|---------|------|
| Pipeline stage 完成后 | 自动 checkpoint |
| 用户 `/checkpoint` 命令 | 手动 checkpoint |
| 进入 `safe_mode` | 强制 checkpoint |
| 任务状态变更前 | 可选 snapshot |

### 4.2 Checkpoint 文件格式

```
state/checkpoint/ckpt_YYYYMMDD_HHMMSS.json
```

**内容**：完整的状态快照，包含 `current-task.json` + `execution-state.json` + `learning-state.json` 的当前值。

```json
{
  "checkpoint_id": "ckpt_20260622_143000",
  "created_at": "ISO8601",
  "reason": "stage_completed | manual | safe_mode | pre_state_change",
  "snapshot": {
    "current_task": { ... },
    "execution_state": { ... },
    "learning_state": { ... }
  }
}
```

### 4.3 恢复流程

```
1. 读取 state/execution-state.json
   └── 确定 active_workflow + pipeline_progress

2. 读取 state/current-task.json
   └── 确定 task 进度 + outputs

3. 验证关键引用存在:
   ├── knowledge_asset_ref → 文件存在?
   ├── plan_ref → 文件存在?
   └── changed_files → 文件存在?

4. 定位最近 checkpoint → 对比当前状态差异

5. 决策:
   ├── 差异小 → resume (继续当前进度)
   └── 差异大 → rollback 到 checkpoint 状态
```

---

## 五、Stall 检测与恢复

### 5.1 检测覆盖

| 数据源 | 检测对象 | 阈值 |
|--------|---------|------|
| `current-task.json` | task status + last_activity_at | 3d warning, 7d stalled |
| `execution-state.json` | pipeline stage 持续时间 | 3d warning, 7d stalled |
| `learning-state.json` | topic last_activity_at | 3d warning, 7d stalled |
| `current-task.json` | retry_count | 3 warning, 5 stalled |

### 5.2 恢复选项

| 当前状态 | 恢复选项 |
|---------|---------|
| `stalled` (task) | → `planning` (重新规划) / → `executing` (继续) / → `blocked` (标记阻塞) |
| `stalled` (learning) | → `restart_needed` (重启) / → `understanding` (复习) |
| `warning` | 更新进度 + 清除 warning |

---

## 六、状态一致性保证

### 6.1 写入规则

1. **单一写入者**：每个 state 文件只有一个主要写入者
2. **原子写入**：先写临时文件，再原子 rename
3. **写入后校验**：L5 Guard 在写入后校验合法性

### 6.2 引用一致性

State 文件中的引用（`knowledge_asset_ref`, `plan_ref` 等）必须：
- 指向实际存在的文件（或可验证的路径）
- 相对路径基于项目根目录
- 不为空占位符

### 6.3 状态同步

```
current-task.json ←→ execution-state.json
       ↕                      ↕
task-history.json    learning-state.json
```

- `current-task.json` 的 `task_id` 必须与 `execution-state.json` 的 `active_task_id` 一致
- 任务从 `current-task.json` 归档到 `task-history.json` 时，同步更新 `execution-state.json`
- `learning-state.json` 的 topic 状态变更时，`task-guard.py` 检测并报告

---

## 七、文件索引

| 文件 | 内容 |
|------|------|
| `.claude/state/README.md` | State 系统文档 |
| `.claude/state/current-task.json` | 活跃任务状态（运行时） |
| `.claude/state/learning-state.json` | 学习状态（运行时） |
| `.claude/state/execution-state.json` | 执行状态（运行时） |
| `.claude/state/task-history.json` | 任务历史归档 |
| `.claude/state/checkpoint/` | 状态快照目录 |
| `.claude/system/execution_guard/task-state-machine.md` | Task 状态机定义 |
| `.claude/system/learning_state/learning-state-machine.md` | Learning 状态机定义 |
| `.claude/system/execution_guard/stall-policy.md` | Stall 策略 |
| `.claude/system/learning_state/study-resume-policy.md` | 学习断档恢复策略 |

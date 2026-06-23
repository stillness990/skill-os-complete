# State System（统一状态层）— v5

> Skill OS v5 L4 层：所有运行时状态的唯一真实来源（Single Source of Truth）。

## 版本

v5.0.0（Skill OS v5 — 统一状态层，从 v4 分散的 system/task_ledger + system/learning_state + system/execution_guard 合并）

---

## v4 → v5 变化

| 维度 | v4 | v5 |
|------|-----|-----|
| 任务状态 | `system/task_ledger/tasks.json` | `state/current-task.json` + `state/task-history.json` |
| 学习状态 | `system/learning_state/state.json` | `state/learning-state.json` |
| 执行状态 | 无统一结构（散落在 hook/workflow 中） | `state/execution-state.json` |
| 状态快照 | 无 | `state/checkpoint/` |

---

## 目录结构

```
.claude/state/
├── README.md                 ← 本文件
├── current-task.json         ← 当前活跃任务状态（一次只一个活跃任务）
├── learning-state.json       ← 学习主题状态（从 system/learning_state/ 迁移）
├── execution-state.json      ← 系统级执行状态（pipeline 进度 + guard 状态）
├── task-history.json         ← 已完成/已取消任务历史索引
└── checkpoint/               ← 状态快照（用于恢复）
    └── ckpt_YYYYMMDD_HHMMSS.json
```

---

## 文件职责

### current-task.json — 当前任务

追踪**当前正在执行**的任务。一次只应有一个活跃任务（status 为 queued/planning/executing/blocked/retrying）。

**关键字段**：
- `task_id` — 唯一标识
- `status` — 状态机状态（queued/planning/executing/blocked/retrying/stalled/done/cancelled）
- `workflow` — 所属 pipeline
- `outputs.knowledge_asset_ref` — v5 强制：关联的 knowledge-asset 产出
- `validation_status` — guard 校验状态

**写入者**：planning, debug, teach-plus, task_ledger
**读取者**：execution_guard, router, 所有 skill

### learning-state.json — 学习状态

追踪所有学习主题的**宏观进度**。从 v4 `system/learning_state/state.json` 迁移。

**关键字段**：
- `topics[].current_stage` — 7 阶段状态机
- `topics[].knowledge_assets` — v5 新增：关联的 knowledge-asset 产出列表
- `topics[].last_activity_at` — 断档检测基准

**写入者**：teach-plus（explain/practice/review）
**读取者**：teach-plus, execution_guard, summarize

### execution-state.json — 执行状态

追踪**系统级执行进度**。记录当前 workflow 的 pipeline 推进情况。

**关键字段**：
- `active_workflow` — 当前活跃的 pipeline
- `pipeline_progress.stages[]` — 每个 stage 的状态
- `guard_status` — 整体 guard 校验状态
- `safe_mode` / `degraded` — 降级模式标记

**写入者**：workflow 推进逻辑, execution_guard
**读取者**：router, 所有 skill, execution_guard

### task-history.json — 任务历史

已完成/已取消任务的**只读索引**。从 v4 `system/task_ledger/tasks.json` 中提取终态任务。

**写入者**：execution_guard（任务终态时归档）
**读取者**：summarize, changelog, knowledge-asset

### checkpoint/ — 状态快照

在关键节点自动或手动保存完整状态快照，用于断点恢复。

**触发条件**：
- 每个 pipeline stage 完成后自动 checkpoint
- 用户主动 `/checkpoint` 命令
- 进入 `safe_mode` 时强制 checkpoint

**恢复规则**：
1. 读取 `execution-state.json` → 确定当前 workflow + stage
2. 读取 `current-task.json` → 确定 task 进度
3. 验证 `knowledge_asset_ref` 存在性
4. resume 或 rollback 到最近合法状态

---

## 状态流转

### current-task 状态机

```
queued → planning → executing → done
             ↓         ↓
         blocked ←──────+────→ retrying
             ↓              ↓
             +──→ stalled ←─+
                    ↓
             planning / executing（恢复后）

任意活动态 → cancelled（用户取消）
```

**非法流转（execution_guard 拦截）**：
- `queued → done`（跳过 planning 和 executing）
- `planning → done`（非 plan_only 类型任务）
- `blocked → done`（没有恢复执行）
- `done → *` / `cancelled → *`（终态不可逆）

### learning-state topic 流转

```
topic_new → understanding → guided_practice → independent_practice
                                                 ↓
                                           consolidation
                                                 ↓
                                            review_due
                                                 ↓
                                             mastered
```

异常状态：`paused`, `stalled`, `restart_needed`

### execution-state pipeline 流转

```
not_started → in_progress → completed
                        ↘ failed → retrying → in_progress
                                 ↘ safe_mode → degraded_completed
```

---

## 与 L0 Knowledge Bus 的关系

```
state/current-task.json
  └── outputs.knowledge_asset_ref    ← 指向 knowledge-asset 产出

state/learning-state.json
  └── topics[].knowledge_assets[]    ← 指向 knowledge-asset 产出列表
```

所有长期产出必须通过 knowledge-asset 写入 `knowledge/`，state 层只记录**引用**，不持有知识内容。

---

## 与 L5 Execution Guard 的关系

```
state/current-task.json  ←─ guard 读取 + 校验 ─→ execution_guard
state/execution-state.json ←─ guard 写入 guard_status
state/checkpoint/         ←─ guard 触发 checkpoint
```

execution_guard 是 state 的主要消费者和校验者。详见 `.claude/system/execution_guard/guard-rules.md`。

---

## 迁移说明

### 从 v4 迁移

| v4 位置 | v5 位置 | 迁移方式 |
|---------|---------|---------|
| `system/task_ledger/tasks.json`（活跃任务） | `state/current-task.json` | 提取活跃任务，保留 schema 映射 |
| `system/task_ledger/tasks.json`（终态任务） | `state/task-history.json` | 提取终态任务，添加 archived_at |
| `system/learning_state/state.json` | `state/learning-state.json` | 直接迁移 + 添加 knowledge_assets 字段 |
| 无 | `state/execution-state.json` | 新建，初始化 |

### 旧目录保留策略

- `system/task_ledger/` — 保留（schema 文档 + task-ops.py 工具），tasks.json 标记为 legacy
- `system/learning_state/` — 保留（状态机文档 + 策略文档），state.json 标记为 legacy
- `system/execution_guard/` — 保留（规则文档），新增 state/ 引用

---

## 操作约定

1. **单一写入者原则**：每个 state 文件只有一个主要写入者，避免竞态
2. **引用而非内容**：state 只记录引用（ref），不持有知识内容
3. **checkpoint 先行**：状态变更前先 checkpoint，确保可回滚
4. **validation 后置**：状态变更后由 execution_guard 校验合法性
5. **不可手动编辑**：state 文件由 skill/workflow/guard 程序化写入，禁止手动编辑

# Phase 2: Skill OS v5 架构重构设计

> 生成时间：2026-06-21
> 输入：Phase 1 仓库扫描结果 + blog.txt v5 需求

---

## 一、v5 六层架构（对比 v4）

```
┌──────────────────────────────────────────────────────────────────┐
│                        v4 架构                                   │
│                                                                  │
│  L6 Extension  ← orchestration/ agents/  (占位)                   │
│  L5 Guard      ← execution_guard/  (规则 + 占位 hook)             │
│  L4 System     ← task_ledger/ learning_state/ knowledge/         │
│  L3 Workflow   ← 3 pipeline docs                                 │
│  L2 Core       ← summarize planning debug                        │
│  L1 Router     ← routing_rules.py + skill-router.py              │
│                                                                  │
│  问题：知识分散、状态不统一、guard 未闭环、knowledge-asset 孤立    │
└──────────────────────────────────────────────────────────────────┘

                              ↓ 升级 ↓

┌──────────────────────────────────────────────────────────────────┐
│                        v5 架构                                   │
│                                                                  │
│  L6 Extension    ← orchestration/ agents/  (不变)                 │
│  L5 Guard        ← 强制 validation + state checkpoint            │
│  L4 State        ← .claude/state/  (新统一状态层)                 │
│  L3 Workflow     ← 3 pipelines + routing (修复注册)              │
│  L2 Core         ← summarize planning debug (输出协议改造)       │
│  L1 Router       ← routing_rules.py (注册 knowledge-asset)       │
│                                                                  │
│  ═══════════════════════════════════════════════════════════     │
│  L0 Knowledge Bus ← .claude/skills/knowledge-asset/             │
│                      (唯一知识出口，横切所有层)                    │
│  ═══════════════════════════════════════════════════════════     │
└──────────────────────────────────────────────────────────────────┘
```

**关键变化**：
- **L0 Knowledge Bus**：从"一个 skill"升级为"基础设施层"，所有长期产出必经此层
- **L4 State**：从分散的 system/task_ledger + system/learning_state + system/execution_guard 合并为统一的 `.claude/state/`
- **L5 Guard**：从"规则文档 + 占位 hook"升级为"强制执行 + 自动化验证"

---

## 二、Skill 调度模型

### 2.1 调度闭环（v5 核心）

```
                     ┌──────────────────────────────────────────┐
                     │              knowledge-asset              │
                     │         (唯一知识出口 / L0)                │
                     │   ┌────────┐ ┌────────┐ ┌──────────┐    │
                     │   │  SOP   │ │Trouble-│ │Knowledge │    │
                     │   │  mode  │ │shooting│ │  Note    │ ... │
                     │   └────────┘ └────────┘ └──────────┘    │
                     └──────────────────────────────────────────┘
                                    ↑  ↑  ↑
                    ┌───────────────┼──┼──┼───────────────┐
                    │               │  │  │               │
        ┌───────────┴──┐  ┌────────┴──┴─┴────┐  ┌───────┴──────────┐
        │  summarize   │  │     debug         │  │   teach-plus     │
        │  (briefing)  │  │  (diagnosis)      │  │ (explain/practice│
        │              │  │                   │  │  /review)        │
        └──────────────┘  └───────────────────┘  └──────────────────┘
                ↑                  ↑                      ↑
                │                  │                      │
        ┌───────┴──────────────────┴──────────────────────┴──────┐
        │                     Router                               │
        │         intent → workflow → primary skill               │
        └─────────────────────────────────────────────────────────┘
                                   ↑
                            User Input
```

### 2.2 单任务完整链路

```
User Input
  │
  ▼
Router (L1)                      intent → workflow → skill
  │
  ▼
Core Skill (L2)                  执行核心逻辑
  │
  ├──→ 对话输出（即时反馈）
  │
  ▼
Knowledge Asset Engine (L0)     结构化沉淀
  │   ├── schema 校验 (9 段)
  │   ├── 模板匹配 (5 种)
  │   └── 写入 .claude/skills/knowledge-asset/knowledge/
  │
  ▼
State System (L4)               状态更新
  │   ├── state/current-task.json    (任务进度)
  │   ├── state/learning-state.json  (学习进度)
  │   └── state/execution-state.json (执行状态)
  │
  ▼
Execution Guard (L5)            验证检查
  │   ├── 结构化输出? ✓
  │   ├── 写入 knowledge-asset? ✓
  │   ├── 更新 state? ✓
  │   ├── 有 next_action? ✓
  │   └── 可继续下一阶段? ✓
  │
  ▼
Next Step Trigger               触发下一步 / 返回用户
```

### 2.3 调度规则

| 场景 | 路由决策 | primary skill | 沉淀模板 | state 更新 |
|------|---------|---------------|---------|-----------|
| 需求澄清 | fallback | `ask` | 无（不入沉淀） | 无 |
| 项目规划 | delivery_pipeline | `planning` | `project-plan` | current-task |
| 故障诊断 | debug_pipeline | `debug` | `troubleshooting` | current-task |
| 学习练习 | learning_pipeline | `teach-plus` | `knowledge-note` | learning-state |
| 知识沉淀 | knowledge-asset | `knowledge-asset` | 按需匹配 | current-task |
| 生成 SOP | knowledge-asset | `knowledge-asset` | `sop` | current-task |
| 代码编写 | delivery_pipeline | `code_assistant` | 可选 | current-task |
| 代码审查 | delivery_pipeline | `reviewer` | 可选 | 无 |

---

## 三、Knowledge Flow 模型

### 3.1 知识单向流动

```
                    所有技能输出
                         │
                         ▼
              ┌─────────────────────┐
              │  是否长期知识？      │
              │  (SOP/诊断/学习/    │
              │   架构/计划/排障)    │
              └─────────┬───────────┘
                        │
              ┌─────────┴──────────┐
              │ YES                │ NO
              ▼                    ▼
    ┌──────────────────┐    直接对话输出
    │ knowledge-asset   │    (echo/ask/changelog/
    │ Engine            │     code_assistant 即时响应)
    │                   │
    │ 1. Schema 校验    │
    │ 2. 模板匹配       │
    │ 3. 元数据提取     │
    │ 4. 写入 knowledge/│
    │ 5. 返回 ref       │
    └──────┬────────────┘
           │
           ▼
    .claude/skills/knowledge-asset/knowledge/
    ├── sop/              ← SOP 模板产出
    ├── troubleshooting/  ← 诊断模板产出
    ├── architecture/     ← 架构模板产出
    ├── knowledge-notes/  ← 知识笔记产出
    └── project-plans/    ← 项目计划产出
```

### 3.2 禁止项（强制）

| ❌ 禁止 | 说明 |
|--------|------|
| 任何 skill 直接写 `knowledge/*` | 必须通过 knowledge-asset |
| 任何 skill 直接写 `docs/*` | 必须通过 knowledge-asset |
| `sop` skill 独立输出 | 已删除，合并入 knowledge-asset sop mode |
| `debug_log` skill 独立输出 | 已删除，合并入 knowledge-asset troubleshooting mode |

### 3.3 Skill 输出改造对照

| Skill | v4 输出目标 | v5 输出目标 | 沉淀时机 |
|-------|-----------|-----------|---------|
| `summarize` | 对话 | 对话 + **knowledge-asset** (knowledge-note/architecture) | briefing 完成后 |
| `planning` | 对话 | 对话 + **可选** knowledge-asset (project-plan) | 用户确认计划后 |
| `debug` | 对话 → debug_log → debug-logs/ | 对话 + **knowledge-asset** (troubleshooting) | 诊断完成后 |
| `teach-plus` | 对话 + practice/ | 对话 + **knowledge-asset** (knowledge-note) | 每个 mode 完成后 |
| `sop` | 对话 | **删除** → knowledge-asset sop mode | — |
| `debug_log` | debug-logs/*.md | **删除** → knowledge-asset troubleshooting mode | — |
| `code_assistant` | 对话 | 对话 (可选 knowledge-asset) | 重大改动时 |
| `reviewer` | 对话 | 对话 (不入沉淀) | — |
| `changelog` | 对话 | 对话 (不入沉淀) | — |

---

## 四、State Machine 模型

### 4.1 统一 State 目录结构

```
.claude/state/
├── README.md                 # State 系统文档
├── current-task.json         # 当前活跃任务状态
├── learning-state.json       # 学习主题状态 (从 system/learning_state/ 迁移)
├── execution-state.json      # 系统级执行状态
├── task-history.json         # 已完成任务索引 (从 task_ledger/tasks.json 分离)
└── checkpoint/               # 状态快照 (用于恢复)
    └── ckpt_YYYYMMDD_HHMMSS.json
```

### 4.2 current-task.json Schema

```json
{
  "task_id": "tsk_20260621_003",
  "title": "修复路由注册缺失",
  "task_type": "delivery",
  "workflow": "delivery_pipeline",
  "current_skill": "code_assistant",
  "phase": "executing",
  "progress": "modifying_skill_rules",
  "status": "executing",
  "blockers": [],
  "outputs": {
    "knowledge_asset_ref": "knowledge/troubleshooting/2026-06-21_路由注册修复.md",
    "changed_files": [".claude/skill-rules.json"],
    "plan_ref": "knowledge/project-plans/2026-06-20_v5升级计划.md"
  },
  "next_action": "运行测试验证路由",
  "validation_status": "pending",
  "retry_count": 0,
  "created_at": "2026-06-21T10:00:00",
  "updated_at": "2026-06-21T10:30:00",
  "last_activity_at": "2026-06-21T10:30:00"
}
```

### 4.3 learning-state.json Schema

```json
{
  "version": "5.0.0",
  "updated_at": "2026-06-21T10:00:00",
  "topics": [
    {
      "topic_id": "learn_20260621_001",
      "topic_name": "Claude Code Skill 系统架构",
      "current_stage": "understanding",
      "current_phase": 1,
      "plan_ref": "knowledge/project-plans/学习计划_skill_arch.md",
      "review_ref": null,
      "last_activity_at": "2026-06-21T10:00:00",
      "next_action": "完成核心概念理解",
      "next_review": "2026-06-23T10:00:00",
      "knowledge_assets": [
        "knowledge/knowledge-notes/2026-06-21_skill_arch_concepts.md"
      ],
      "created_at": "2026-06-21T10:00:00",
      "updated_at": "2026-06-21T10:00:00"
    }
  ]
}
```

### 4.4 execution-state.json Schema

```json
{
  "version": "5.0.0",
  "active_workflow": "delivery_pipeline",
  "active_task_id": "tsk_20260621_003",
  "pipeline_progress": {
    "current_stage_index": 3,
    "total_stages": 6,
    "stages": [
      {"name": "summarize", "status": "completed", "skill": "summarize"},
      {"name": "planning", "status": "completed", "skill": "planning"},
      {"name": "task_ledger", "status": "completed", "skill": "task_ledger"},
      {"name": "code_assistant", "status": "executing", "skill": "code_assistant"},
      {"name": "knowledge_asset", "status": "pending", "skill": "knowledge-asset"},
      {"name": "execution_guard", "status": "pending", "skill": "execution_guard"}
    ]
  },
  "guard_status": "pending",
  "safe_mode": false,
  "degraded": false,
  "last_checkpoint_at": "2026-06-21T10:00:00",
  "created_at": "2026-06-21T10:00:00",
  "updated_at": "2026-06-21T10:30:00"
}
```

### 4.5 状态流转规则

```
current-task 状态流转 (与 task_ledger 同步):
  queued → planning → executing → done
                   ↘ blocked → executing
                   ↘ stalled → planning
                   ↘ retrying → executing (≤3次)
                            ↘ stalled (>3次)

execution-state pipeline 流转:
  not_started → in_progress → completed
                           ↘ failed → retrying → in_progress
                                    ↘ safe_mode → degraded_completed

learning-state topic 流转:
  topic_new → understanding → guided_practice → independent_practice
                                                   ↘ consolidation
                                                     → review_due
                                                     → mastered
```

### 4.6 Checkpoint 机制

```
触发条件:
  - 每个 stage 完成后自动 checkpoint
  - 用户主动 /checkpoint 命令
  - 进入 safe_mode 时强制 checkpoint

恢复规则:
  1. 读取 execution-state.json → 确定当前 workflow + stage
  2. 读取 current-task.json → 确定 task 进度
  3. 验证 knowledge-asset ref 存在性
  4. resume 或 rollback 到最近合法状态
```

---

## 五、v5 完整文件变更计划

### 5.1 新增文件

| 文件 | 用途 |
|------|------|
| `.claude/state/README.md` | State 系统文档 |
| `.claude/state/current-task.json` | 当前任务状态模板 |
| `.claude/state/learning-state.json` | 学习状态数据 |
| `.claude/state/execution-state.json` | 执行状态数据 |
| `.claude/state/task-history.json` | 已完成任务历史 |
| `.claude/skills/knowledge-asset/knowledge/` | 知识库根目录 |
| `.claude/skills/knowledge-asset/knowledge/sop/` | SOP 产出 |
| `.claude/skills/knowledge-asset/knowledge/troubleshooting/` | 排障产出 |
| `.claude/skills/knowledge-asset/knowledge/architecture/` | 架构产出 |
| `.claude/skills/knowledge-asset/knowledge/knowledge-notes/` | 笔记产出 |
| `.claude/skills/knowledge-asset/knowledge/project-plans/` | 计划产出 |
| `ARCHITECTURE.md` | 最终架构文档 (Phase 8) |
| `EXECUTION_FLOW.md` | 执行链路文档 (Phase 8) |
| `STATE_SYSTEM.md` | 状态机说明 (Phase 8) |
| `KNOWLEDGE_SYSTEM.md` | 知识系统说明 (Phase 8) |

### 5.2 删除文件

| 文件 | 原因 |
|------|------|
| `.claude/skills/sop/SKILL.md` | 收编入 knowledge-asset sop mode |
| `.claude/skills/debug_log/SKILL.md` | 收编入 knowledge-asset troubleshooting mode |

### 5.3 修改文件

| 文件 | 变更 |
|------|------|
| `.claude/skill-rules.json` | +knowledge-asset 注册；-sop standalone；-debug_log standalone；sop/debug_log 关键词重定向到 knowledge-asset |
| `.claude/skills/knowledge-asset/SKILL.md` | 升级为 Knowledge Asset Engine；+sop mode；+troubleshooting mode；+强制输出规则 |
| `.claude/skills/core/summarize/SKILL.md` | 输出协议增加 knowledge-asset 沉淀步骤 |
| `.claude/skills/core/debug/SKILL.md` | 输出协议增加 knowledge-asset 沉淀步骤（取代 debug_log 引用） |
| `.claude/skills/core/planning/SKILL.md` | 输出协议增加可选 knowledge-asset 沉淀 |
| `.claude/skills/teach-plus/SKILL.md` | 输出协议增加 knowledge-asset 沉淀步骤 |
| `.claude/hooks/completion-guard.py` | main() 接入 check_done_conditions()；增加 knowledge-asset 检查 |
| `.claude/hooks/task-guard.py` | 增加 state/ 检查；state 更新逻辑 |
| `.claude/router/skill_index.json` | +knowledge-asset 条目；更新 sop/debug_log 状态 |
| `README.md` | 更新至 v5 架构 |
| `CLAUDE.md` | 更新操作手册 |

---

## 六、Phase 2 设计总结

| 维度 | v4 现状 | v5 目标 |
|------|---------|---------|
| **知识出口** | 分散（对话/debug-logs/docs/practice） | **单一**：knowledge-asset Engine |
| **状态管理** | 分散 3 处（task_ledger/learning_state/execution_guard） | **统一**：`.claude/state/` |
| **sop** | 独立 skill，输出到对话 | **删除**，成为 knowledge-asset sop mode |
| **debug_log** | 独立 skill，写 debug-logs/ | **删除**，成为 knowledge-asset troubleshooting mode |
| **summarize/debug/teach-plus** | 输出到对话，不入沉淀 | **强制**接入 knowledge-asset |
| **knowledge-asset** | 孤立 skill，未注册路由 | **基础设施层**，横切所有技能 |
| **execution guard** | 占位 hook | **强制执行**，自动化验证 |
| **路由** | 16 条规则，knowledge-asset 缺失 | 修复注册，关键词触发 |

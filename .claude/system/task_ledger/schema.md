# Task Ledger Schema（任务账本数据结构）

## 版本

v4.0.0（Skill OS v4 — 扩展状态机 + execution_guard 约束）

## 文件

- `.claude/system/task_ledger/tasks.json` — 任务账本主文件
- `.claude/system/task_ledger/schema.md` — 本文件（通用 schema）
- `.claude/system/task_ledger/learning-task-schema.md` — 学习任务专属 schema
- `.claude/system/task_ledger/task-ops.py` — 任务操作脚本
- `.claude/system/execution_guard/task-state-machine.md` — 正式状态流转规则（v4 新增）

## 顶层结构

```json
{
  "meta": {
    "version": "4.0.0",
    "project": "项目名",
    "created": "ISO8601",
    "updated": "ISO8601"
  },
  "tasks": []
}
```

## Task 对象（v4 完整字段集）

```json
{
  "task_id": "tsk_YYYYMMDD_xxx",
  "title": "任务标题",
  "task_type": "delivery | debug | learning | plan_only",
  "workflow": "delivery_pipeline | debug_pipeline | learning_pipeline",
  "status": "queued | planning | executing | blocked | retrying | stalled | done | cancelled",
  "source": "planning | debug | teach-plus | manual",
  "next_action": "下一步具体操作",
  "artifacts": ["产出物路径或描述"],
  "artifact_refs": {
    "plan_ref": "计划文档路径",
    "implementation_ref": "实现文档路径",
    "debug_report_ref": "诊断报告路径",
    "fix_ref": "修复引用",
    "study_plan_ref": "学习计划路径",
    "practice_log_ref": "练习日志路径",
    "review_log_ref": "复盘日志路径",
    "changed_files": ["变更文件列表"],
    "changelog_ref": "变更日志路径",
    "review_ref": "审查意见路径",
    "result_summary": "结果摘要"
  },
  "guard_status": {
    "last_check_at": "ISO8601",
    "stall_detected": false,
    "warnings": []
  },
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | ✅ | 唯一标识，格式 `tsk_YYYYMMDD_NNN` |
| `title` | string | ✅ | 任务标题，一句话 |
| `task_type` | string | ✅ | 任务类型：delivery / debug / learning / plan_only |
| `workflow` | string | ✅ | 所属工作流 |
| `status` | string | ✅ | 当前状态（v4 扩展至 8 个状态） |
| `source` | string | ✅ | 来源技能 |
| `next_action` | string | 推荐 | 下一步具体操作 |
| `artifacts` | string[] | 推荐 | 产出物列表（简单描述） |
| `artifact_refs` | object | 推荐 | 结构化 artifact 引用（v4 新增，供 execution_guard 检查） |
| `guard_status` | object | 推荐 | 监督状态（v4 新增） |
| `created_at` | string | ✅ | 创建时间（ISO8601） |
| `updated_at` | string | ✅ | 最后更新时间（ISO8601） |

## 状态集合（v4 扩展 — 全系统统一词汇）

| 状态 | 含义 | 合法来源 | 合法去向 |
|------|------|---------|---------|
| `queued` | 排队中，待开始 | （初始状态） | `planning`, `cancelled` |
| `planning` | 规划中 | `queued`, `blocked` | `executing`, `blocked`, `done`（仅 plan_only）, `cancelled` |
| `executing` | 执行中 | `planning`, `retrying`, `blocked` | `blocked`, `retrying`, `done`, `cancelled` |
| `blocked` | 被阻塞 | `planning`, `executing` | `planning`, `executing`, `cancelled` |
| `retrying` | 重试中 | `executing` | `executing`, `blocked`, `stalled`, `cancelled` |
| `stalled` | 卡住/超时未更新 | `planning`, `executing`, `retrying` | `planning`, `executing`, `cancelled` |
| `done` | 已完成（终态） | `planning`（仅 plan_only）, `executing` | — |
| `cancelled` | 已取消（终态） | 任意非终态 | — |

> **兼容说明**：旧代码中使用的 `in_progress` → 映射为 `executing`；`retry` → 映射为 `retrying`。
> v1→v4 迁移映射定义在 `orchestration/orchestration_types.py` 的 `V1_TO_V4_STATUS` 中。

## 状态流转图（v4）

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

## 非法流转（v4 execution_guard 拦截）

以下流转被视为非法，execution_guard 应拦截：
- `queued → done`（跳过 planning 和 executing）
- `planning → done`（非 plan_only 类型任务）
- `blocked → done`（没有恢复执行）
- `retrying → done`（没有重新执行过程）
- `stalled → done`（没有恢复动作）
- `done → *`（终态不可逆）
- `cancelled → *`（终态不可逆）

## 来源技能写入方式

### planning → task_ledger

planning 产出阶段计划后，每个阶段的每个关键任务写入一条 task：

```json
{
  "task_id": "tsk_20260620_001",
  "title": "重构 summarize 目录结构",
  "workflow": "delivery_pipeline",
  "status": "queued",
  "source": "planning",
  "next_action": "创建 .claude/skills/core/summarize/ 目录并写入 SKILL.md",
  "artifacts": [".claude/skills/core/summarize/SKILL.md"]
}
```

### debug → task_ledger

debug 诊断完成后，如需代码修改，可写入 task（source=debug），交给 code_assistant：

```json
{
  "task_id": "tsk_20260620_002",
  "title": "修复 KeyError：config 模块缺少默认值",
  "workflow": "debug_pipeline",
  "status": "queued",
  "source": "debug",
  "next_action": "打开 config.py，在 get() 调用中增加默认值参数",
  "artifacts": ["config.py"]
}
```

### teach-plus → task_ledger（Phase 2 正式接入）

teach-plus 产出的每日学习任务写入 task（source=teach-plus，workflow=learning_pipeline，task_type=learning）。

完整学习任务数据结构见 `learning-task-schema.md`。

最小写入示例：

```json
{
  "task_id": "tsk_20260620_003",
  "task_type": "learning",
  "title": "阅读 skill-rules.json 并理解路由规则",
  "workflow": "learning_pipeline",
  "status": "queued",
  "source": "teach-plus",
  "study_mode": "practice",
  "topic": "路由系统",
  "source_plan": "skill-os-complete-4周学习计划",
  "stage": "阶段一",
  "next_action": "打开 .claude/skill-rules.json，阅读 skills 对象的每个条目",
  "estimated_minutes": 30
}
```

## 扩展字段（Phase 2+ 预留）

以下字段 Phase 1 不实现，但 schema 预留命名空间：

- `priority`: 优先级（high / medium / low）
- `assignee`: 负责人
- `deadline`: 截止时间
- `tags`: 标签列表
- `parent_task_id`: 父任务 ID（子任务拆分）
- `blocked_by`: 阻塞此任务的任务 ID 列表
- `estimated_minutes`: 预估耗时（分钟）
- `actual_minutes`: 实际耗时（分钟）

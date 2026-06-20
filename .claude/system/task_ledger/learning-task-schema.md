# Learning Task Schema（学习任务数据结构）

## 版本

v1.0.0（Phase 2）

## 概述

定义学习任务在 task_ledger 中的数据结构。
学习任务与普通项目任务共享 `tasks.json`，通过 `task_type: "learning"` 区分，
并扩展学习专属字段。

## 学习任务对象（完整字段集）

```json
{
  "task_id": "tsk_YYYYMMDD_NNN",
  "task_type": "learning",
  "title": "学习任务标题",
  "workflow": "learning_pipeline",
  "status": "queued | in_progress | blocked | done | retry",
  "source": "teach-plus",
  "study_mode": "explain | practice | review",
  "topic": "学习主题（如：skill-os-complete 路由系统）",
  "source_plan": "关联的学习计划名称或路径",
  "stage": "当前学习阶段（如：阶段一 / 第2周）",
  "next_action": "下一步具体操作",
  "artifacts": ["产出物路径或描述"],
  "completion_notes": "完成后填写的学习笔记或心得",
  "review_due": "预计复盘日期（ISO8601，可选）",
  "estimated_minutes": 30,
  "actual_minutes": null,
  "tags": ["学习标签"],
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | ✅ | 唯一标识，格式 `tsk_YYYYMMDD_NNN` |
| `task_type` | string | ✅ | 固定值 `"learning"`，区分普通项目任务 |
| `title` | string | ✅ | 任务标题，一句话 |
| `workflow` | string | ✅ | 固定值 `"learning_pipeline"` |
| `status` | string | ✅ | 当前状态：queued / in_progress / blocked / done / retry |
| `source` | string | ✅ | 来源技能，学习任务固定 `"teach-plus"` |
| `study_mode` | string | ✅ | teach-plus 子模式：`explain` / `practice` / `review` |
| `topic` | string | ✅ | 学习主题，比 title 更宏观（如 "路由系统" "协议层"） |
| `source_plan` | string | 推荐 | 关联的阶段学习计划名称或路径 |
| `stage` | string | 推荐 | 当前学习阶段（如 "阶段一：理解骨架"） |
| `next_action` | string | 推荐 | 下一步具体操作 |
| `artifacts` | string[] | 推荐 | 产出物列表 |
| `completion_notes` | string | 推荐 | 完成后的学习笔记 |
| `review_due` | string | 可选 | 预计复盘日期 |
| `estimated_minutes` | number | 可选 | 预估耗时（分钟） |
| `actual_minutes` | number | 可选 | 实际耗时（分钟） |
| `tags` | string[] | 可选 | 学习标签 |
| `created_at` | string | ✅ | 创建时间（ISO8601） |
| `updated_at` | string | ✅ | 最后更新时间（ISO8601） |

## 状态流转（与通用任务一致）

```
queued → in_progress → done
              ↓
          blocked → in_progress
              ↓
           retry → in_progress
```

## 与通用任务的关系

学习任务和项目任务共享 `tasks.json` 的 `tasks` 数组，通过 `task_type` 和 `workflow` 字段区分：

| 属性 | 学习任务 | 项目任务 |
|------|---------|---------|
| `task_type` | `"learning"` | 不设置或 `"project"` |
| `workflow` | `"learning_pipeline"` | `"delivery_pipeline"` / `"debug_pipeline"` |
| `source` | `"teach-plus"` | `"planning"` / `"debug"` / `"manual"` |
| `study_mode` | ✅ 有 | ❌ 无 |
| `topic` | ✅ 有 | ❌ 无 |
| `source_plan` | ✅ 有 | ❌ 无 |
| `completion_notes` | ✅ 学习笔记 | ❌ 无（用其他方式） |
| `review_due` | ✅ 可选 | ❌ 无 |

## teach-plus → task_ledger 写入方式

### teach-plus/practice → ledger

practice 产出每日学习单后，将核心任务写入 ledger：

```json
{
  "task_id": "tsk_20260620_001",
  "task_type": "learning",
  "title": "阅读 skill-rules.json 并理解路由规则",
  "workflow": "learning_pipeline",
  "status": "queued",
  "source": "teach-plus",
  "study_mode": "practice",
  "topic": "skill-os-complete 路由系统",
  "source_plan": "skill-os-complete-4周学习计划",
  "stage": "阶段一：理解骨架（第1周）",
  "next_action": "打开 .claude/skill-rules.json，阅读 skills 对象的每个条目",
  "estimated_minutes": 30,
  "tags": ["路由", "skill-os-complete"],
  "created_at": "2026-06-20T14:30:00Z",
  "updated_at": "2026-06-20T14:30:00Z"
}
```

### teach-plus/review → 读取 ledger

review 模式从 ledger 读取数据的方式：

```
筛选条件：
- task_type = "learning"
- created_at 在复盘周期内
- （可选）study_mode = "practice"

聚合统计：
- 按 status 分组统计（done / in_progress / queued / blocked）
- 按 topic 分组查看学习覆盖范围
- 检查是否有长期 blocked 的任务
```

## 示例：一周学习任务在 ledger 中的状态

```json
{
  "tasks": [
    {
      "task_id": "tsk_20260616_001",
      "task_type": "learning",
      "title": "阅读 CLAUDE.md 了解项目结构",
      "workflow": "learning_pipeline",
      "status": "done",
      "source": "teach-plus",
      "study_mode": "practice",
      "topic": "skill-os-complete 总览",
      "source_plan": "skill-os-complete-4周学习计划",
      "stage": "阶段一",
      "completion_notes": "读完了，理解了技能依赖关系和路由机制",
      "estimated_minutes": 30,
      "actual_minutes": 25,
      "created_at": "2026-06-16T09:00:00Z",
      "updated_at": "2026-06-16T09:25:00Z"
    },
    {
      "task_id": "tsk_20260617_001",
      "task_type": "learning",
      "title": "手动追踪一个学习请求的完整路由路径",
      "workflow": "learning_pipeline",
      "status": "done",
      "source": "teach-plus",
      "study_mode": "practice",
      "topic": "skill-os-complete 路由系统",
      "source_plan": "skill-os-complete-4周学习计划",
      "stage": "阶段一",
      "completion_notes": "完成了，理解了 intent→workflow→skill 的链路",
      "estimated_minutes": 45,
      "actual_minutes": 60,
      "created_at": "2026-06-17T09:00:00Z",
      "updated_at": "2026-06-17T10:00:00Z"
    },
    {
      "task_id": "tsk_20260618_001",
      "task_type": "learning",
      "title": "对比 delivery_pipeline 和 learning_pipeline 的 stage 设计",
      "workflow": "learning_pipeline",
      "status": "in_progress",
      "source": "teach-plus",
      "study_mode": "practice",
      "topic": "skill-os-complete workflow 层",
      "source_plan": "skill-os-complete-4周学习计划",
      "stage": "阶段一",
      "next_action": "继续写对比笔记的第二部分",
      "estimated_minutes": 45,
      "created_at": "2026-06-18T09:00:00Z",
      "updated_at": "2026-06-18T09:30:00Z"
    }
  ]
}
```

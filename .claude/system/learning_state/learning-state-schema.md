# Learning State Schema（学习状态数据结构）— v4

## 版本

v4.0.0（Skill OS v4）

## 概述

定义 learning_state 的数据结构。learning_state 是 Skill OS v4 系统层的学习状态追踪模块，teach-plus 依赖它来维持学习进度闭环。

---

## Learning State 对象

```json
{
  "topic_id": "learn_YYYYMMDD_xxx",
  "topic_name": "学习主题名称",
  "current_stage": "topic_new | understanding | guided_practice | independent_practice | consolidation | review_due | mastered",
  "current_phase": "当前阶段描述",
  "plan_ref": "关联的学习计划路径",
  "review_ref": "最近一次复盘路径",
  "last_activity_at": "ISO8601",
  "next_action": "下一步学习建议",
  "next_review": "下次复盘日期 (ISO8601)",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

---

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `topic_id` | string | ✅ | 学习主题唯一标识 |
| `topic_name` | string | ✅ | 学习主题名称 |
| `current_stage` | string | ✅ | 当前学习阶段 |
| `current_phase` | string | 推荐 | 当前阶段的人类可读描述 |
| `plan_ref` | string | 推荐 | 关联的学习计划文档路径 |
| `review_ref` | string | 推荐 | 最近一次复盘文档路径 |
| `last_activity_at` | string | ✅ | 上次学习活动时间（ISO8601） |
| `next_action` | string | 推荐 | 下一步学习建议（具体可操作） |
| `next_review` | string | 推荐 | 下次复盘日期（ISO8601） |
| `created_at` | string | ✅ | 创建时间 |
| `updated_at` | string | ✅ | 最后更新时间 |

---

## 状态字段详解

### current_stage（学习阶段）

见 `learning-state-machine.md`。完整阶段集合：
- `topic_new` — 新主题，等待开始
- `understanding` — 理解阶段，建立概念框架
- `guided_practice` — 引导练习，有示范/有提示
- `independent_practice` — 独立练习，无提示
- `consolidation` — 巩固整合，融会贯通
- `review_due` — 需要复盘（间隔重复）
- `mastered` — 已掌握（终态）

允许的异常状态：
- `paused` — 暂停学习
- `stalled` — 卡住/超时未学
- `restart_needed` — 需要重新开始

---

## 与 task_ledger 的关系

```
learning_state（宏观：主题级学习进度）
        ↕ 双向关联
task_ledger（微观：每日学习任务记录）
```

- learning_state 描述一个学习主题的**整体进度**
- task_ledger 中的 learning 任务描述**每天的具体学习动作**
- teach-plus/review 读取两者来生成复盘报告

## 与 teach-plus 模式的关系

| teach-plus 模式 | 对 learning_state 的操作 |
|----------------|------------------------|
| `explain` | 创建 learning_state（topic_new → understanding），写入 topic_name / plan_ref |
| `practice` | 更新 current_stage（understanding → guided_practice / independent_practice），更新 last_activity_at / next_action |
| `review` | 读取 learning_state，更新 review_ref / next_review，可能推进到 consolidation / review_due / mastered |

## 存储位置

```
.claude/system/learning_state/
├── learning-state-schema.md       ← 本文件
├── learning-state-machine.md      ← 状态机定义
├── study-resume-policy.md         ← 断档恢复策略
└── state.json                     ← 学习状态数据文件（运行时读写）
```

## state.json 最小示例

```json
{
  "topics": [
    {
      "topic_id": "learn_20260621_001",
      "topic_name": "skill-os-complete 路由系统",
      "current_stage": "guided_practice",
      "current_phase": "阶段一第3天：手动追踪路由路径",
      "plan_ref": "knowledge/study_plans/skill-os-complete-4周学习计划.md",
      "review_ref": null,
      "last_activity_at": "2026-06-21T09:30:00Z",
      "next_action": "完成 delivery_pipeline 的完整路由追踪练习",
      "next_review": "2026-06-28T00:00:00Z",
      "created_at": "2026-06-19T09:00:00Z",
      "updated_at": "2026-06-21T09:30:00Z"
    }
  ]
}
```

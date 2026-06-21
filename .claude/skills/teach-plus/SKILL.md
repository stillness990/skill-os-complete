---
name: teach-plus
version: "4.0"
description: "学习工作流控制器（Learning Workflow Controller）：把学习底稿 + 学习计划转成真正可执行的学习行动与复盘机制。提供 explain / practice / review 三种模式。正式接入 learning_state 和 execution_guard。"
---

# Teach-Plus（学习工作流控制器 / Learning Workflow Controller）— v4

## 定位

> teach-plus 不是普通"教学 skill"，而是 **Learning Workflow Controller / 学习工作流控制器**。
> 它负责把 summarize 产出的学习底稿和 planning 产出的阶段学习计划，
> 转成**可执行的学习行动**（讲解、每日练习、复盘），驱动 learning_state 追踪学习进度，
> 并接受 execution_guard 的完成约束。

## 负责什么 / 不负责什么

**负责：**
- 把学习对象讲清楚，建立理解框架（explain 模式）
- 把学习计划转成每日可执行学习单与刻意练习（practice 模式）
- 做周复盘 / 阶段复盘，调整学习策略（review 模式）
- 把学习任务写入 task_ledger
- **驱动 learning_state 更新学习进度**（v4 新增）
- **检测断档并执行恢复策略**（v4 新增）

**不负责：**
- 原始材料的知识整理与结构化（交给 summarize）
- 项目式拆解与阶段计划制定（交给 planning）
- 长期任务状态管理（交给 task_ledger）
- 代码编写 / bug 修复（交给 code_assistant / debug）
- **学习任务完成质量检查（交给 execution_guard）**（v4 新增）

## 与其他技能的边界

| 技能 | 职责 | teach-plus 如何使用 |
|------|------|-------------------|
| **summarize** | 生成学习底稿 / 项目底稿 | 作为 explain 的输入材料 |
| **planning** | 生成阶段学习计划 / 项目计划 | 作为 practice 的输入材料 |
| **task_ledger** | 记录任务状态、进度 | practice 产出写入 ledger；review 读取 ledger |
| **learning_state** | 追踪学习主题的阶段、进度、断档 | explain/practice/review 都读写 learning_state（v4 新增） |
| **execution_guard** | 检查 learning 任务 done 条件 | learning 任务完成前受 execution_guard 约束（v4 新增） |
| **debug** | 诊断实操卡点 | 学习过程中遇到报错/异常时调用 |
| **knowledge** | 知识沉淀存放 | 学习底稿/计划/复盘归档到此 |

## 三种模式

### 模式 1：explain（讲解）

**适用场景：**
- "我想学这个仓库 / 项目 / 技能"
- "把这个文档讲给小白听"
- "帮我梳理这个知识体系"
- 用户第一次接触某个学习对象，需要建立整体理解框架

**状态推进**：`topic_new → understanding`

**输入：** 学习对象 + summarize 学习底稿（如有）+ 用户当前水平

**输出：** 结构化理解框架（核心概念、主线、前置点、卡点、学习顺序建议）

**learning_state 操作**：创建或更新 learning_state，写入 topic_name、plan_ref、current_stage=understanding

**详见：** `explain.md`

### 模式 2：practice（练习）

**适用场景：**
- "给我今天的学习任务"
- "按这个学习计划拆成今天可执行动作"
- "给我练习题 / 练习任务 / 今日训练单"
- 已有学习计划，只需要今天的学习单

**状态推进**：`understanding → guided_practice → independent_practice → consolidation`

**输入：** planning/learning 产出的学习计划 + learning_state 当前阶段 + 可用时间

**输出：** 每日学习单（主题、步骤、练习、验收标准、时长）

**learning_state 操作**：更新 current_stage、last_activity_at、next_action

**断档检测**：每次进入 practice 前检查 last_activity_at，按 study-resume-policy.md 执行恢复

**详见：** `practice.md`

### 模式 3：review（复盘）

**适用场景：**
- "帮我复盘这周学习"
- "我学了一周，现在下一周怎么调"
- "哪些地方没掌握好"
- task_ledger 中已积累一段学习记录

**状态推进**：`consolidation → review_due → mastered`（或回退到 guided_practice）

**输入：** 本周 daily 文件 + task_ledger 学习任务记录 + learning_state 当前状态

**输出：** 周复盘报告（完成情况、卡点、下周调整建议）

**learning_state 操作**：更新 review_ref、next_review、可能推进或回退 current_stage

**详见：** `review.md`

## 典型学习链路（v4）

```
用户学习请求
    ↓
summarize/briefing（生成学习底稿）
    ↓
planning/learning（生成阶段学习计划）
    ↓
teach-plus/explain（建立理解框架 → 推进 topic_new → understanding）
    ↓
teach-plus/practice（生成每日学习单 → 推进 guided_practice / independent_practice）
    ↓
task_ledger（学习任务入账）
    ↓
learning_state（学习状态更新：阶段 + 进度 + next_action）
    ↓
teach-plus/review（周复盘 / 阶段复盘 → 推进 consolidation / review_due / mastered）
    ↓
execution_guard（完成检查：study_plan_ref / practice_log_ref / learning_state 更新）
```

## 触发关键词

`我想学`、`学会`、`教我`、`入门`、`系统学习`、`学习路线`、`每日练习`、`帮我设计学习`、`学习计划`、`今天学什么`、`复盘`、`本周复盘`、`学习复盘`

## 目录结构

```
.claude/skills/teach-plus/
├── SKILL.md              ← 本文件（学习控制层总入口）
├── explain.md            ← explain 模式定义
├── practice.md           ← practice 模式定义
├── review.md             ← review 模式定义
└── templates/
    ├── learning-plan-template.md
    ├── daily-study-template.md
    └── weekly-review-template.md
```

## 行为规则

- **先查输入源**：进入 explain 前，检查是否有 summarize 底稿；进入 practice 前，检查是否有 planning 计划
- **模式选择**：根据用户意图自动选择 explain / practice / review，必要时询问确认
- **写入 ledger**：practice 产出的每日学习任务应写入 task_ledger
- **读取 ledger**：review 模式应读取 task_ledger 中的学习任务完成记录
- **读写 learning_state**（v4 新增）：每次进入 teach-plus 时读取 learning_state，操作后更新 learning_state
- **断档检测**（v4 强化）：每次 practice 前检查 last_activity_at，按 study-resume-policy.md 执行恢复策略
- **受 execution_guard 约束**（v4 新增）：learning 类任务进入 done 前，必须满足 execution_guard 的 artifact 要求
- **卡点处理**：遇到技术问题调用 debug，不自己硬解
- **保存产物**：学习单写入 practice/daily/YYYY-MM-DD.md，复盘写入 practice/reviews/

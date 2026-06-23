# Learning Pipeline（学习工作流）— v4

## 版本

v4.0.0（Skill OS v4）

## 概述

Learning Pipeline 是 Skill OS v4 的**学习工作流标准链路**。
它定义了一个学习请求如何从"我想学"一路流到每日练习、任务记录、每周复盘和学习状态追踪。

## 标准链路

```text
用户学习请求
    ↓
ask（仅在目标不清时）
    ↓
summarize/briefing（生成学习底稿）
    ↓
planning/learning（生成阶段学习计划）
    ↓
teach-plus/explain（建立理解框架 → 推进 topic_new → understanding）
    ↓
teach-plus/practice（生成每日学习单 + 练习任务 → 推进 guided_practice / independent_practice）
    ↓
task_ledger（学习任务入账，可选但推荐）
    ↓
learning_state（学习状态更新：阶段、进度、next_action）
    ↓
teach-plus/review（周复盘 / 阶段复盘 → 推进 consolidation / review_due / mastered）
    ↓
knowledge-asset / knowledge-note（学习笔记结构化沉淀）
    ↓
execution_guard（完成检查：study_plan_ref / practice_log_ref / learning_state 更新）
```

## 各阶段详细说明

### Phase 1：ask（可选）

**触发条件：** 用户请求模糊，学习目标、对象或时间范围不明确。

**做什么：** 最多问 2 个关键问题澄清学习意图。

**跳过条件：** 用户已明确指定学习对象 + 目标 + 时间范围。

### Phase 2：summarize/briefing

**触发条件：** 学习对象是仓库/文档/技能体系，需要先结构化理解。

**做什么：** 对学习对象做结构化分析，产出学习底稿（briefing），包含：
- 核心概念
- 模块/结构主线
- 依赖关系
- 难点/卡点

**产物：** 学习底稿 → 可存入 `knowledge/learning_briefs/`

### Phase 3：planning/learning

**触发条件：** 学习底稿已就绪，需要制定阶段学习计划。

**做什么：** 把学习底稿拆成阶段计划，包含：
- 阶段划分与时间分配
- 每阶段目标与验收方式
- 本周重点
- 风险提示

**产物：** 阶段学习计划 → 可存入 `knowledge/study_plans/`

### Phase 4：teach-plus/explain

**触发条件：**
- 用户说"给我讲明白""帮我梳理""这是什么"
- 用户首次接触该学习对象
- 当前缺少基础理解框架

**做什么：** 把学习对象讲清楚，建立理解框架，输出：
- 一句话定义
- 核心概念/模块
- 主线结构
- 前置知识
- 最容易卡住的点
- 推荐学习顺序

**输出后：** 引导用户进入 practice 模式。

### Phase 5：teach-plus/practice

**触发条件：**
- 用户说"给我今天的学习任务""帮我练""今天学什么"
- 已有学习计划，需要转成每日行动
- 用户明确要练习/动手

**做什么：** 生成每日学习单，包含：
- 今日学习主题
- 步骤清单（含预估时间）
- 练习/输出任务（1-3个，必须有动手成分）
- 最小动作（≤15分钟）
- 验收标准
- 自测问题
- 卡住时的 fallback

**产物：** 每日学习单 → 保存到 `practice/daily/YYYY-MM-DD.md`
**写入 ledger：** 将核心任务写入 task_ledger（task_type=learning）

### Phase 6：task_ledger（可选但推荐）

**触发条件：** practice 产出了学习任务。

**做什么：** 将每日学习任务写入 `tasks.json`，记录状态。

**写入内容：**
- task_type = "learning"
- study_mode = "practice"（来自 teach-plus）
- source_plan = 关联的学习计划
- status = "queued"

### Phase 7：teach-plus/review

**触发条件：**
- 用户说"帮我复盘这周""本周复盘""学了一周总结一下"
- 用户说"最近学得很乱，帮我看看怎么调整"
- task_ledger 中已积累一周以上学习记录

**做什么：** 复盘一周学习，输出：
- 本周计划 vs 实际完成
- 已掌握内容
- 仍不稳的点
- 卡点类型判断（理解问题 / 练习不足）
- 下周调整建议（保留/停止/增加/新增）
- 是否需要回退到 explain 或 practice

**产物：** 周复盘报告 → 保存到 `practice/reviews/YYYY-WXX.md` 和 `knowledge/review_logs/`

## 模式路由规则

当 intent 判定为 `learn_topic` 后，根据用户输入中的关键词路由到 teach-plus 的具体模式：

| 用户意图 | 路由目标 | 关键词示例 |
|---------|---------|-----------|
| 想理解某物 | teach-plus/explain | "讲明白""是什么""梳理""帮我讲""解释" |
| 想要今日任务 | teach-plus/practice | "练习""今天学什么""学习单""训练""动手" |
| 想复盘总结 | teach-plus/review | "复盘""本周""回顾""学得怎么样" |

## 与其他 pipeline 的关系

| Pipeline | 关系 |
|----------|------|
| `delivery_pipeline` | 学习工作流的独立并行管线；学习过程中如需开发/重构，可切入 delivery_pipeline |
| `debug_pipeline` | 学习过程中遇到代码报错/异常时，可切入 debug_pipeline |

## 与其他技能的边界

| 技能 | 在 learning_pipeline 中的职责 | 不在 learning_pipeline 中的职责 |
|------|---------------------------|-------------------------------|
| **summarize** | 生成学习底稿 | 不做长期学习编排 |
| **planning** | 生成阶段学习计划 | 不生成每日训练单 |
| **teach-plus** | 负责 explain / practice / review | 不做原始材料整理 |
| **task_ledger** | 记录学习任务状态 | 不生成学习内容 |
| **knowledge** | 存放学习沉淀物 | 不参与生成逻辑 |

## 完整示例：一个学习请求的流转

```
用户输入："我想系统学习 skill-os-complete 这个仓库"

阶段1 - ask：[目标已明确，跳过]

阶段2 - summarize/briefing：
  → 分析仓库结构，产出学习底稿
  → 核心概念：skill路由、workflow管线、协议层、任务账本
  → 主线：输入→intent判定→workflow→skills执行
  → 存入 knowledge/learning_briefs/

阶段3 - planning/learning：
  → 制定4周学习计划
  → 阶段一：理解骨架（第1周）
  → 存入 knowledge/study_plans/

阶段4 - teach-plus/explain：
  → 讲解 skill-os-complete 的整体架构
  → 输出理解框架（核心概念、主线、卡点）

阶段5 - teach-plus/practice：
  → 生成今日学习单："阅读 CLAUDE.md 和 skill-rules.json"
  → 练习：手动追踪一个请求的完整路由路径
  → 保存 practice/daily/2026-06-20.md
  → 写入 task_ledger

阶段6 - task_ledger：
  → 记录学习任务，status=queued

...（一周后）...

阶段7 - teach-plus/review：
  → 读取本周 daily 文件和 ledger 记录
  → 输出周复盘报告
  → 保存 practice/reviews/2026-W25.md
```

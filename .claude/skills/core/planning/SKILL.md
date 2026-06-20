---
name: planning
description: "任务拆解与推进引擎：基于 briefing/上下文，把目标拆解为阶段+今日行动。支持 project（项目交付）和 learning（学习计划）两种模式。优先消费 summarize/briefing 的输出。"
---

# Planning Skill（任务拆解与推进引擎）

## 定位

> planning 是 Skill OS v3 的"任务拆解与推进引擎"。它只回答一个问题：**基于当前 briefing / 上下文，这件事应该如何拆解、分阶段推进、今天先做什么？**

## 职责边界

**负责：**
- 信息不足时先澄清（最多 3 轮，每轮 1 个问题附推荐答案）
- 把目标拆成阶段计划（2~5 个阶段）
- 每个阶段明确产出物
- 生成"今日最小行动"（≤30 分钟，具体可操作）
- 标注依赖和阻塞项
- 产出可写入 `task_ledger` 的任务条目

**不负责：**
- 知识提炼或输入整理（那是 `summarize` 的事）
- 执行具体任务（那是 `code_assistant` 的事）
- 诊断 bug（那是 `debug` 的事）
- 长期状态管理（那是 `task_ledger` 的事）
- 设计学习练习和复盘（那是 `teach-plus` 的事）
- 生成操作手册（那是 `sop` 的事）

## 两种模式

### 模式 A：`project`（项目交付）
- **用途**：仓库重构、功能开发、项目升级、任务拆解
- **输入**：目标 + briefing（来自 summarize/briefing）
- **输出协议**：`plan-protocol.md`
- **详细说明**：`project.md`

### 模式 B：`learning`（学习计划）
- **用途**：学习仓库、学习技能体系、学习技术主题
- **输入**：学习对象 + learning briefing（来自 summarize/briefing）
- **输出协议**：`plan-protocol.md` + 学习专属字段
- **详细说明**：`learning.md`

## 与 summarize 的关系

```
summarize/briefing（项目底稿 / 学习底稿）
        ↓
planning（读取 briefing → 拆解阶段 → 产出 plan）
        ↓
task_ledger（plan 中的行动项写入 tasks.json）
```

- `planning` **默认优先消费** `summarize/briefing` 的输出
- 如果没有 briefing，planning 可以自行从零开始，但需标注"缺少 briefing"
- `planning` 不替代 `summarize` — summarize 做知识提炼，planning 做任务拆解

## 与 task_ledger 的关系

- planning 产出的**每个阶段的关键任务** → 可写入 `task_ledger/tasks.json`
- planning 产出的**今日最小行动** → 对应 task 的 `next_action` 字段
- planning 自身**不负责状态追踪** — 那是 task_ledger 的职责

## 触发场景

关键词：`计划`、`规划`、`方案`、`怎么搞`、`roadmap`、`学习路线`、`拆解`、`阶段`、`steps`、`怎么做`、`从哪开始`

## 输入字段

```
目标（必填）：[要完成什么，可验证]
当前状态（选填）：[现在的起点是什么]
时间范围（选填）：[多久完成]
约束条件（选填）：[资源、限制]
模式（自动判定）：project / learning
briefing（推荐）：[来自 summarize/briefing 的输出]
```

## 行为规则

- **优先消费 briefing**：有 summarize/briefing 的输出 → 以此为输入基础
- **不确定任务类型时，先问用户确认** — 不猜
- **代码任务走 EnterPlanMode** — 先探索再规划
- **非代码任务直接输出** — 不走 Plan Mode
- **"今日最小行动"必须满足**：具体动作 + 时间可估 + 状态差也能做
- **阶段 2~5 个**：太少说明拆解不够，太多说明粒度太细
- **每个阶段必须有明确的产出物**：不能是"了解更多XX"这种模糊描述
- **阻塞项必须标注解决方案**：不只列问题，还要给建议

## 澄清模式规则

- **一次只问一个问题** — 不轰炸用户
- **每个问题附推荐答案** — 帮助快速决策
- **最多 3 轮澄清** — 第 3 轮后即使信息不完整也继续规划
- **澄清优先级**：任务类型 > 时间范围 > 当前状态 > 约束条件

## 目录结构

```
planning/
├── SKILL.md        ← 本文件
├── project.md       ← project 模式详细说明
└── learning.md      ← learning 模式详细说明
```

## 兼容说明

- 旧 `planner/SKILL.md` 保留在 `.claude/skills/planner/SKILL.md`
- 旧版路由规则（skill-rules.json 中 planner 条目）需更新为 `planning`
- 旧 planner 已具备 A/B 模式（代码任务/通用任务）的雏形，v3 升级为 project/learning 两模式
- 旧 planner 中 EnterPlanMode 的决策逻辑保留，移至 project 模式

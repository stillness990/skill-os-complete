# Study Resume Policy（断档恢复策略）— v4

## 版本

v4.0.0（Skill OS v4）

## 概述

定义学习中断后如何恢复的策略。teach-plus 在检测到学习断档时参照此文档决定恢复方式。

---

## 断档检测

teach-plus 每次被触发时，检查 learning_state 中：
- `last_activity_at` 距离当前时间的差值
- `current_stage` 当前所处阶段

根据间隔天数选择恢复策略。

---

## 恢复策略

### 1~2 天没学（轻度断档）

**判定**：`last_activity_at` 距今 1~2 天

**策略**：**直接继续当前阶段**

**操作**：
- 读取 learning_state.current_stage
- 读取 learning_state.next_action
- 从 next_action 继续推进
- 不需要特殊 review

**teach-plus 行为**：
- 提示："上次学习是 {N} 天前，继续从 {current_stage} 推进"
- 直接进入 practice 模式，生成当日学习单

---

### 3~5 天没学（中度断档）

**判定**：`last_activity_at` 距今 3~5 天

**策略**：**先做轻量 review，再继续**

**操作**：
1. 先花 5~10 分钟快速回顾上次学习内容
2. 检查是否还记得核心概念
3. 如果记忆清晰 → 继续当前阶段
4. 如果记忆模糊 → 回退到上一个阶段

**teach-plus 行为**：
- 提示："已 {N} 天没有学习，建议先做 5 分钟快速回顾"
- 生成回顾问题（基于上次学习的 topic）
- 根据用户回答决定是继续还是回退

**learning_state 更新**：
- 如果继续：不改变 current_stage，更新 last_activity_at
- 如果回退：current_stage 回退一步（如 independent_practice → guided_practice）

---

### 7 天以上没学（重度断档）

**判定**：`last_activity_at` 距今 7~13 天

**策略**：**先做主题复盘，再决定是否恢复原计划**

**操作**：
1. 先做一次轻量复盘（回顾学习目标 + 已完成内容 + 核心概念）
2. 评估当前知识的留存情况
3. 决定：
   - 继续原计划（知识留存 ≥ 60%）
   - 回退 1~2 个阶段（知识留存 30%~60%）
   - 重新开始（知识留存 < 30%）

**teach-plus 行为**：
- 提示："已超过一周没有学习，建议先做一次完整的主题复盘"
- 调用 teach-plus/review 的复盘能力
- 根据复盘结果调整计划

**learning_state 更新**：
- 可能标记为 `paused` → `restart_needed`
- 或回退 current_stage
- 更新 plan_ref（可能需要新计划）

---

### 14 天以上没学（严重断档）

**判定**：`last_activity_at` 距今 ≥ 14 天

**策略**：**标记 restart_needed，重新评估学习目标**

**操作**：
1. 标记 learning_state 为 `restart_needed`
2. 询问用户是否仍然想学这个主题
3. 如果是 → 建议重新走完整学习链路：
   - summarize/briefing（重新生成学习底稿）
   - planning/learning（重新制定学习计划）
   - teach-plus/explain（重新建立理解框架）
4. 如果否 → 标记 mastered（承认放弃，关闭学习主题）

**teach-plus 行为**：
- 提示："已 {N} 天没有学习这个主题，建议重新评估"
- 询问是否继续
- 如果继续 → 走完整 learning pipeline

---

## 恢复决策表

| 间隔天数 | 严重程度 | 动作 | learning_state 变更 |
|---------|---------|------|-------------------|
| 1~2 天 | 轻度 | 直接继续 | 更新 last_activity_at |
| 3~5 天 | 中度 | 轻量 review → 继续或回退一步 | 可能回退 current_stage |
| 7~13 天 | 重度 | 主题复盘 → 继续/回退/重来 | 可能 paused → restart_needed |
| ≥ 14 天 | 严重 | 重新评估 → 重来或放弃 | restart_needed 或 mastered |

---

## execution_guard 关联

- 如果 learning_state 被标记为 `stalled`（超时未学），execution_guard 在 done 检查时会警告
- learning 类任务 done 时，execution_guard 检查 last_activity_at 是否在合理范围内
- 断档超过 7 天的主题，进入 done 前需要额外确认

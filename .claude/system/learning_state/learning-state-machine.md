# Learning State Machine（学习状态机）— v4

## 版本

v4.0.0（Skill OS v4）

## 概述

定义 learning_state 中学习主题的状态流转规则。teach-plus 的 explain / practice / review 三种模式各自推动状态沿此状态机前进。

---

## 状态集合

### 正常推进状态

```
topic_new → understanding → guided_practice → independent_practice → consolidation → review_due → mastered
```

| 状态 | 含义 | teach-plus 模式 |
|------|------|----------------|
| `topic_new` | 新主题，尚未开始学习 | —（初始状态） |
| `understanding` | 正在建立理解框架 | `explain` 推动进入 |
| `guided_practice` | 引导练习阶段（有示范） | `practice` 推动进入 |
| `independent_practice` | 独立练习阶段（无提示） | `practice` 推动进入 |
| `consolidation` | 巩固整合阶段 | `practice` + `review` 推动 |
| `review_due` | 间隔重复/复盘到期 | `review` 推动进入 |
| `mastered` | 已掌握（终态） | `review` 确认进入 |

### 异常/暂停状态

| 状态 | 含义 | 触发条件 |
|------|------|---------|
| `paused` | 用户主动暂停 | 用户说"暂停学习XX" |
| `stalled` | 超时未学习 | 超过阈值未活动（见 study-resume-policy.md） |
| `restart_needed` | 断档太久需重来 | 超过 14 天未活动 |

---

## 合法流转

```
topic_new ──→ understanding ──→ guided_practice ──→ independent_practice
                                                        ↓
                                                  consolidation
                                                        ↓
                                                   review_due ──→ mastered
                                                        ↑            │
                                                        └────────────┘
                                                    （间隔重复循环）

任意非终态 → paused
任意非终态 → stalled（超时）
任意非终态 → restart_needed（断档太久）
paused → 回到之前状态
stalled → 回到之前状态（需确认恢复策略）
restart_needed → topic_new（重新开始）
```

---

## teach-plus 模式与状态推进

### explain 模式

```
触发条件：用户首次接触学习对象或需要建立整体理解
状态推进：topic_new → understanding
前置依赖：summarize/briefing 学习底稿（推荐）
产出：理解框架 → 写入 learning_state (current_stage=understanding)
```

### practice 模式

```
触发条件：已有学习计划，需要每日练习
状态推进路径1：understanding → guided_practice
状态推进路径2：guided_practice → independent_practice
状态推进路径3：independent_practice → consolidation
前置依赖：planning/learning 学习计划
产出：每日学习单 → 更新 learning_state (last_activity_at, next_action)
```

### review 模式

```
触发条件：一周学习结束或用户要求复盘
状态推进路径1：consolidation → review_due
状态推进路径2：review_due → mastered（确认掌握）
状态推进路径3：review_due → guided_practice（未掌握，回退练习）
前置依赖：task_ledger 学习任务记录 + learning_state 当前状态
产出：复盘报告 → 更新 learning_state (review_ref, next_review)
```

---

## execution_guard 检查点

当 learning 类任务进入 done 时，execution_guard 检查：
1. `learning_state` 是否已更新（current_stage / last_activity_at）
2. `next_action` 是否非空
3. 状态推进是否合理（如不能从 topic_new 直接跳到 mastered）

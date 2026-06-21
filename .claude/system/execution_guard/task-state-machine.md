# Task State Machine（任务状态机）— v4

## 版本

v4.0.0（Skill OS v4 execution_guard）

## 概述

定义 Skill OS v4 中所有任务的状态集合和合法流转规则。execution_guard 在执行任何状态变更时必须参照此文档校验。

---

## 状态集合

| 状态 | 类型 | 含义 |
|------|------|------|
| `queued` | 活动态 | 任务已创建，排队等待开始 |
| `planning` | 活动态 | 任务正在规划/拆解中 |
| `executing` | 活动态 | 任务正在执行中 |
| `blocked` | 活动态 | 任务被外部依赖阻塞，等待解除 |
| `retrying` | 活动态 | 任务执行失败后正在重试 |
| `stalled` | 活动态 | 任务长时间无更新，疑似卡住 |
| `done` | 终态 | 任务已完成，不可逆 |
| `cancelled` | 终态 | 任务已取消，不可逆 |

---

## 合法流转表

| 从 ↓ / 到 → | queued | planning | executing | blocked | retrying | stalled | done | cancelled |
|-------------|--------|----------|-----------|---------|----------|---------|------|-----------|
| **queued** | — | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **planning** | ❌ | — | ✅ | ✅ | ❌ | ❌ | ✅¹ | ✅ |
| **executing** | ❌ | ❌ | — | ✅ | ✅ | ❌ | ✅ | ✅ |
| **blocked** | ❌ | ✅ | ✅ | — | ❌ | ❌ | ❌ | ✅ |
| **retrying** | ❌ | ❌ | ✅ | ✅ | — | ❌ | ❌ | ✅ |
| **stalled** | ❌ | ✅ | ✅ | ❌ | ❌ | — | ❌ | ✅ |
| **done** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | — | ❌ |
| **cancelled** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | — |

> ¹ `planning → done` 仅当 `task_type = "plan_only"` 时合法。对于 delivery/debug/learning 类型任务，此流转非法。

---

## 合法流转详解

### 1. queued → planning
- **条件**：任务被领取，开始规划
- **guard 检查**：无特殊要求

### 2. queued → cancelled
- **条件**：用户在开始前取消任务
- **guard 检查**：记录取消原因

### 3. planning → executing
- **条件**：计划已就绪，开始执行
- **guard 检查**：是否存在 plan_ref（plan_only 除外）

### 4. planning → blocked
- **条件**：规划过程中发现阻塞项
- **guard 检查**：阻塞原因必须记录

### 5. planning → done（仅 plan_only）
- **条件**：任务本身就是"只产出计划，不落地执行"
- **guard 检查**：必须有明确的 plan artifact，不允许空完成
- **task_type 限制**：仅 `plan_only`

### 6. executing → done
- **条件**：执行完成，产物就绪
- **guard 检查**：按 artifact-requirements.md 检查最小产物

### 7. executing → blocked
- **条件**：执行中遇到阻塞
- **guard 检查**：阻塞原因 + 解除条件

### 8. executing → retrying
- **条件**：执行失败，需要重试
- **guard 检查**：记录失败原因 + 重试策略

### 9. retrying → executing
- **条件**：重试准备就绪，回到执行
- **guard 检查**：确认重试策略有效

### 10. retrying → blocked
- **条件**：重试也遇到阻塞
- **guard 检查**：记录阻塞原因

### 11. blocked → planning
- **条件**：阻塞解除，需要重新规划
- **guard 检查**：确认阻塞已解除

### 12. blocked → executing
- **条件**：阻塞解除，直接继续执行
- **guard 检查**：确认阻塞已解除

### 13. 任意活动态 → stalled
- **条件**：长时间无更新（见 stall-policy.md）
- **触发**：execution_guard 定期检查或手动标记

### 14. stalled → planning / executing
- **条件**：恢复活动
- **guard 检查**：确认恢复原因 + 更新 next_action

### 15. 任意活动态 → cancelled
- **条件**：用户主动取消
- **guard 检查**：记录取消原因

---

## 非法流转（execution_guard 必须拦截）

| 非法流转 | 原因 |
|---------|------|
| `queued → done` | 跳过 planning 和 executing，属于"跳步骤完成" |
| `queued → executing` | 跳过 planning，没有计划就开始执行 |
| `planning → done` (非 plan_only) | delivery/debug/learning 类任务必须经过 executing |
| `blocked → done` | 阻塞状态下不能直接完成，必须先恢复执行 |
| `retrying → done` | 重试状态下不能直接完成，必须回到 executing |
| `stalled → done` | 卡住的任务不能直接标完成，必须先恢复 |
| `done → *` | 终态不可逆 |
| `cancelled → *` | 终态不可逆 |

---

## 与 task_ledger 的协作

- task_ledger 负责存储任务状态
- execution_guard 负责在每次状态变更时校验合法性
- 如果 task-ops.py 收到非法状态变更请求，应拒绝并引用此文档

## 与 hook 层的协作

- `task-guard.py`：在任务状态更新时调用此状态机校验
- `completion-guard.py`：在任务进入 done 时调用此状态机 + artifact-requirements.md 联合校验

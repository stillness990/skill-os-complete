# Stall Policy（卡住/超时策略）— v4

## 版本

v4.0.0（Skill OS v4 execution_guard）

## 概述

定义任务在 planning / executing / retrying 状态下长时间未更新时的检测和恢复策略。

---

## 超时阈值

| 状态 | 阈值 | 判定 |
|------|------|------|
| `planning` | 超过 3 天未更新 | 标记 warning |
| `planning` | 超过 7 天未更新 | 标记 stalled |
| `executing` | 超过 3 天未更新 | 标记 warning |
| `executing` | 超过 7 天未更新 | 标记 stalled |
| `retrying` | 重试超过 3 次仍失败 | 标记 warning |
| `retrying` | 重试超过 5 次仍失败 | 标记 stalled |

> 阈值可根据项目实际情况调整。以上为默认值。

---

## stall 检测流程

```
1. 扫描 tasks.json
2. 筛选 status ∈ {planning, executing, retrying} 的任务
3. 计算 updated_at 距离当前时间的差值
4. 差值 > warning_threshold → 添加 guard_status.warning
5. 差值 > stall_threshold → 状态改为 stalled
6. 对于 retrying 任务 → 额外检查重试次数
```

---

## stalled 后的恢复策略

### 1. 回到 planning

**适用场景：**
- 原始计划已不再适用
- 任务目标发生变化
- 阻塞原因需要重新评估

**操作：**
- `stalled → planning`
- 更新 next_action：重新评估目标和计划
- 清除旧的 guard_status.warnings

### 2. 回到 executing

**适用场景：**
- 只是忘记更新状态，任务实际在推进
- 阻塞已自然解除

**操作：**
- `stalled → executing`
- 更新 next_action：当前要做的具体事
- 更新 updated_at

### 3. 写 next_step

**适用场景：**
- 任务卡在某个具体问题上
- 需要明确下一步突破方向

**操作：**
- 保持当前状态
- 更新 next_action：具体到可操作的步骤
- 清除 stall 标记（将 stalled 改回原状态 + 更新 updated_at）

### 4. 重新拆子任务

**适用场景：**
- 任务太大，需要进一步拆解
- 当前子任务粒度不足以推进

**操作：**
- 回到 planning
- 创建更小的子任务条目
- 原任务可保留为父任务或直接替换

### 5. 标记 blocked 并说明原因

**适用场景：**
- 卡住原因是外部依赖
- 等待他人/其他系统完成

**操作：**
- `stalled → blocked`
- 记录阻塞原因 + 预期解除条件
- 设置提醒时间

---

## warning 处理

warning 不等于 stalled，不需要改变状态。处理方式：

1. **planning warning**：在 task 的 guard_status.warnings 中添加 "planning 已超过 3 天未更新，建议确认计划是否仍然适用"
2. **executing warning**：添加 "executing 已超过 3 天未更新，建议更新进度"
3. **retrying warning**：添加 "已重试 3 次，建议分析失败模式，考虑替代方案"

---

## execution_guard 自动动作

| 检测到的情况 | 自动动作 |
|-------------|---------|
| warning 阈值触发 | 在 guard_status 中添加 warning 消息 |
| stall 阈值触发 | 状态改为 stalled，记录原因 |
| stalled 任务被用户关注 | 提示恢复选项（回到 planning / 继续 executing / 拆子任务 / 标 blocked） |

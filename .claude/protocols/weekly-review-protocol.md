# Weekly Review Protocol（每周复盘协议）

## 版本

v1.0.0（Phase 2）

## 用途

定义**每周学习复盘**的标准输出格式。服务于：
- `teach-plus/review`（生成周复盘报告）

## 协议字段

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `review_period` | object | 复盘周期 {start_date, end_date, week_number} |
| `learning_object` | string | 学习对象 |
| `current_phase` | string | 当前阶段 |
| `plan_vs_actual` | array | 本周计划 vs 实际完成对比 |
| `mastered` | array | 本周已掌握内容 |
| `unstable` | array | 本周仍不稳的点 |
| `next_week_strategy` | string | 下周核心策略（一句话） |

### 可选字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `bottleneck_analysis` | array | 卡点类型判断（理解问题/练习不足） |
| `exercise_stats` | object | 练习统计数据 |
| `adjustments` | object | 下周调整（保留/停止/增加/新增） |
| `need_rollback` | object | 是否需要回退到 explain/practice |
| `review_log_path` | string | 复盘报告保存路径 |

### plan_vs_actual 条目结构

```json
{
  "planned_item": "计划内容",
  "status": "done / partial / not_done",
  "actual_output": "实际产出",
  "notes": "备注/原因"
}
```

### bottleneck_analysis 条目结构

```json
{
  "bottleneck": "卡点描述",
  "type": "understanding / insufficient_practice",
  "evidence": "判断依据",
  "suggestion": "解决建议"
}
```

### adjustments 对象结构

```json
{
  "keep": ["继续做的有效方法"],
  "stop": ["暂停的效果不好的方法"],
  "increase": ["需要加强的内容"],
  "add": ["需要新增的内容"]
}
```

### need_rollback 对象结构

```json
{
  "to_explain": ["需要重新讲解的概念"],
  "to_practice": ["需要更多练习的技能"],
  "continue_next_phase": false
}
```

## 输出格式（Markdown）

见 `teach-plus/templates/weekly-review-template.md`。

## 与 task_ledger 的关系

review 应从 task_ledger 中读取数据：

```
筛选条件：
- task_type = "learning"
- created_at 在本周范围内

统计指标：
- 任务总数
- 完成数 (status = done)
- 进行中数 (status = in_progress)
- 未开始数 (status = queued)
- 阻塞数 (status = blocked)
```

## 与其他协议的关系

| 协议 | 关系 |
|------|------|
| `learning-plan-protocol.md` | review 的"本周目标"对照 learning plan 的阶段性目标 |
| `daily-study-protocol.md` | review 的"计划 vs 实际"基于本周 daily study 记录 |

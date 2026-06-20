# Daily Study Protocol（每日学习单协议）

## 版本

v1.0.0（Phase 2）

## 用途

定义**每日学习单**的标准输出格式。服务于：
- `teach-plus/practice`（生成每日学习单）
- `task_ledger`（学习任务记录的数据来源）

## 协议字段

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | string | 日期 YYYY-MM-DD |
| `topic` | string | 今日学习主题（一句话） |
| `minimal_goal` | string | 今日最小目标（可验证的结果） |
| `steps` | array | 步骤清单（至少1个） |
| `exercises` | array | 练习/输出任务（至少1个，最多3个） |
| `acceptance_criteria` | array | 验收标准（至少1个，可验证） |
| `estimated_total_minutes` | number | 预计总时长（分钟） |

### 可选字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `learning_object` | string | 学习对象 |
| `current_phase` | string | 当前阶段 |
| `source_plan` | string | 关联的学习计划名称 |
| `minimal_action` | string | 今日最小动作（原子习惯层，≤15分钟） |
| `self_test_questions` | array | 自测问题（1-3个） |
| `fallback` | object | 卡住时的 fallback 方案 |
| `next_day_bridge` | string | 明日衔接说明 |

### step 对象结构

```json
{
  "order": 1,
  "description": "具体操作描述",
  "estimated_minutes": 10
}
```

### exercise 对象结构

```json
{
  "name": "练习名称",
  "description": "具体操作",
  "estimated_minutes": 15,
  "output_artifact": "产出物描述或路径",
  "acceptance": "怎么判断做对了"
}
```

### fallback 对象结构

```json
{
  "if_stuck_at_step": "Step X",
  "alternative": "替代方案",
  "if_exercise_too_hard": "简化版替代练习",
  "if_no_time": "今天最不能跳过的一项"
}
```

## 输出格式（Markdown）

见 `teach-plus/templates/daily-study-template.md`。

## 与 task_ledger 的映射

daily study 产出的学习任务写入 task_ledger 时，字段映射如下：

| Daily Study 字段 | task_ledger 字段 |
|-----------------|-----------------|
| `date` | `created_at` |
| `topic` | `title` |
| `exercises[0].description` | `next_action` |
| `source_plan` | `source_plan` |
| `"practice"` | `study_mode` |

## 与其他协议的关系

| 协议 | 关系 |
|------|------|
| `learning-plan-protocol.md` | daily study 的输入来自 learning plan 的阶段目标和本周重点 |
| `weekly-review-protocol.md` | 一周的 daily study 记录是 review 的核心输入 |

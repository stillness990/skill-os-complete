# Learning Plan Protocol（学习计划协议）

## 版本

v1.0.0（Phase 2）

## 用途

定义**阶段学习计划**的标准输出结构。服务于：
- `planning` 的 learning 模式（产出阶段学习计划）
- `teach-plus` 的 explain / practice 模式（读取学习计划作为输入）

## 协议字段

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `learning_objective` | string | 学习对象名称（仓库/技能/技术领域） |
| `target_level` | enum | 学习目标：`can_use` / `can_modify` / `can_create` / `can_explain` |
| `current_level` | enum | 当前水平：`zero_basis` / `seen_some` / `know_some` |
| `total_duration` | string | 总时间范围，如 "4周" "8周" |
| `daily_time` | string | 每日投入，如 "30分钟" "1小时" |
| `phases` | array | 阶段列表（至少1个） |
| `created_at` | string | 创建日期 ISO8601 |

### 可选字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `prerequisites` | array | 前置知识清单 |
| `risks` | array | 风险/卡点提示 |
| `entry_conditions_for_practice` | array | 进入 practice 的条件 |

### phase 对象结构

```json
{
  "phase_id": 1,
  "name": "阶段名称",
  "day_range": "第1-7天",
  "objective": "这个阶段学完后能做什么",
  "core_content": ["内容项1", "内容项2"],
  "expected_output": ["产出物1", "产出物2"],
  "verification": "如何判断这个阶段完成了"
}
```

## 输出格式（Markdown）

见 `teach-plus/templates/learning-plan-template.md`。

## 与其他协议的关系

| 协议 | 关系 |
|------|------|
| `summary-protocol.md` | learning plan 的输入材料来自 summary 产出的 briefing |
| `daily-study-protocol.md` | learning plan 是 daily study 的上游输入 |
| `weekly-review-protocol.md` | learning plan 中的阶段目标作为 review 的对照基准 |

## 使用示例

### planning/learning → 产出 learning plan

```markdown
## 📚 学习计划

### 基本信息
- 学习对象：skill-os-complete
- 学习目标：can_modify（能改）
- 当前水平：seen_some（看过一点）
- 总时间范围：4周
- 每日投入：30分钟

### 阶段划分

#### 阶段一：理解系统骨架（第1-7天）
- 目标：能画出系统架构图，说清每个技能的职责
- 核心内容：
  1. 阅读 CLAUDE.md 和 CONTEXT.md
  2. 理解 skill-rules.json 路由规则
  3. 理解 workflow_templates.json 三条管线
- 预计产出：系统架构笔记 + 技能关系图
- 验收方式：能不看文档画出技能依赖关系图
```

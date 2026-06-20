# Planner → Planning 迁移说明

**旧版 `planner`**（本目录）→ **新版 `planning`** `.claude/skills/core/planning/`

## 变化

| 方面 | 旧版 planner | 新版 planning |
|------|-------------|--------------|
| 名称 | `planner` | `planning` |
| 位置 | `.claude/skills/planner/` | `.claude/skills/core/planning/` |
| 模式 | 代码任务/通用任务/学习计划 | project / learning |
| 输出协议 | 嵌在 SKILL.md 中 | 独立 `protocols/plan-protocol.md` |
| 与 summarize 关系 | 文字描述 | 明确优先消费 briefing |
| 与 task 层关系 | 无 | 明确写入 task_ledger |
| EnterPlanMode | 代码任务自动触发 | 保留，移至 project 模式 |

## 路由规则更新

需在 `skill-rules.json` 中：
1. 新增 `planning` 条目（复制旧 `planner` 规则）
2. 保留旧 `planner` 条目作为 alias（降低 priority 或标记 deprecated）

## 兼容性

- 旧版 SKILL.md 保留
- 旧路由仍可命中 `planner`，但推荐使用 `planning`
- 如果两者同时存在，router 应优先选择 `planning`

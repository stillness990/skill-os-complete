# Planning Mode: Project（项目交付模式）

## 适用场景

当用户有明确的项目任务需要拆解和推进时使用。

触发示例：
- "帮我规划这个仓库的重构"
- "设计一个用户登录系统的实现计划"
- "这个功能怎么分阶段做"
- router 检测到 intent 为 `project_delivery` 时自动触发

## 输入要求

| 字段 | 必填 | 说明 |
|------|------|------|
| 目标 | ✅ | 要完成什么（可验证） |
| 当前状态 | 选填 | 起点是什么 |
| 时间范围 | 选填 | 多久完成（默认 4 周） |
| 约束条件 | 选填 | 资源、技术栈、兼容性要求 |
| briefing | 推荐 | 来自 summarize/briefing 的项目底稿 |

## 输出协议

严格遵循 `plan-protocol.md`（见 `.claude/protocols/plan-protocol.md`）。

## 行为规则

- **优先消费 briefing**：如果有 summarize/briefing 的输出，以此为输入
- **不跳过澄清**：信息不足时先问（最多 3 轮，每轮 1 个问题附推荐答案）
- **代码任务走 EnterPlanMode**：涉及仓库/代码/文件的计划，先探索再规划
- **非代码任务直接输出**：纯架构/流程/方案设计，不走 Plan Mode
- **阶段 2~5 个**：太少拆不够，太多太碎
- **每个阶段必须有产出物**：不能是"了解更多"这种模糊描述
- **今日最小行动必须可执行**：具体动作 + 时间可估 + 状态差也能做

## 与 downstream 的关系

- `project` 产出的关键任务 → 写入 `task_ledger`
- 执行层面 → `code_assistant` / `sop`
- 审查 → `reviewer`
- 发布 → `changelog`

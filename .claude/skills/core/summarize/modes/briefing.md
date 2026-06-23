# Summarize Mode: Briefing（深度底稿模式）

## 适用场景

当用户需要**给下游技能准备输入**，或需要**深度理解一个东西的内部结构和逻辑**时使用。

触发示例：
- "帮我给 planning 准备一份项目底稿"
- "分析这个仓库的结构，我要做重构"
- "帮我总结，后面要给 teach-plus 用"
- router 检测到 intent 为 `project_delivery` / `debug_issue` / `learn_topic` 时自动触发

## 输入要求

| 字段 | 必填 | 说明 |
|------|------|------|
| 输入内容 | ✅ | 要分析的对象路径/内容 |
| 目标消费者 | ✅ | planning / debug / teach-plus |
| 深度要求 | 自动 | briefing 默认深度高于 basic |

## 输出协议

严格遵循 `briefing-protocol.md`（见 `.claude/protocols/briefing-protocol.md`）。

输出结构：
1. **对象** — 名称 + 类型标注
2. **背景** — 为什么做 + 当前阶段
3. **已知信息** — 已确认 vs 推测，按维度分组
4. **未知信息 / 风险** — 表格形式，标注严重程度
5. **关键结构 / 关键概念** — 核心工作流 + 3~8 个关键概念
6. **推荐后续工作流** — 明确 workflow + primary_skill + secondary_skills + 理由

## 行为规则

- 必须标注对象类型（仓库/技能/文档/项目/对话/日志）
- 必须区分"已确认"和"推测"信息
- 风险必须标注严重程度（低/中/高）
- 必须推荐后续 workflow，并给出理由
- 如果信息不足以做出有信心的推荐，在"未知信息"中标注

## Briefing → 下游消费

| 消费者 | 消费方式 | briefing 提供的价值 |
|--------|---------|-------------------|
| `planning` | 读取 briefing → 拆解阶段计划 | 关键结构 + 已知信息 + 风险 |
| `debug` | 读取 briefing → 诊断入口 | 背景 + 关键结构 + 未知信息 |
| `teach-plus` | 读取 briefing → 学习底稿 | 关键概念 + 结构 + 推荐 workflow |
| **`knowledge-asset`** | **briefing 完成后结构化沉淀** | **核心结论 + 关键知识 + 推荐工作流**（v5 强制） |

## v5：knowledge-asset 沉淀规则

- **briefing 完成后必须调用 `knowledge-asset` 沉淀**
- 模板选择：仓库/系统分析 → `architecture`；概念/知识整理 → `knowledge-note`
- 沉淀路径：`.claude/skills/knowledge-asset/knowledge/{template_dir}/`
- 沉淀后更新 `.claude/state/current-task.json` 的 `outputs.knowledge_asset_ref`

## 与其他模式的关系

- `basic` — 轻量摘要，快速了解
- `briefing` — 深度底稿，供下游技能消费 → 本模式

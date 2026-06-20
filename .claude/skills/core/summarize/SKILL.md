---
name: summarize
description: "知识整理中台：把任意输入提炼成结构化底稿。支持 basic（快速摘要）和 briefing（深度底稿，供 planning/debug/teach-plus 消费）两种模式。"
---

# Summarize Skill（知识整理中台）

## 定位

> summarize 是 Skill OS v3 的"输入结构化中台"。它不只是摘要器——它把任何输入转成标准化的结构化输出，供下游技能（planning/debug/teach-plus）直接消费。

## 职责边界

**负责：**
- 读取任意输入（对话、仓库目录、文档、技能、日志）并结构化提炼
- 产出 `basic` 摘要（快速了解，遵循 `summary-protocol`）
- 产出 `briefing` 深度底稿（供 planning/debug/teach-plus 消费，遵循 `briefing-protocol`）
- 识别核心模块、工作流、风险点
- 推荐后续 workflow 方向

**不负责：**
- 做具体任务拆解或阶段计划（那是 `planning` 的事）
- 诊断 bug 或定位根因（那是 `debug` 的事）
- 执行代码修改（那是 `code_assistant` 的事）
- 追踪任务状态（那是 `task_ledger` 的事）
- 设计学习练习（那是 `teach-plus` 的事）

## 两种模式

### 模式 A：`basic`（快速摘要）
- **用途**：快速了解一个东西是什么
- **触发**：用户说"总结"、"摘要"、"概括"、"梳理"
- **输出协议**：`.claude/protocols/summary-protocol.md`
- **详细说明**：`modes/basic.md`

### 模式 B：`briefing`（深度底稿）
- **用途**：给 planning/debug/teach-plus 准备结构化输入
- **触发**：用户明确说要给下游用，或 router 检测到 project_delivery / debug_issue / learn_topic intent
- **输出协议**：`.claude/protocols/briefing-protocol.md`
- **详细说明**：`modes/briefing.md`

## 模式选择逻辑

```
用户输入
    ↓
是否包含 "给 planning" / "底稿" / "深度分析" / "后面要用"？
    是 → briefing 模式
    否 → router 是否检测到 intent？
            是 → briefing 模式
            否 → basic 模式
```

## 触发场景

关键词：`总结`、`摘要`、`概括`、`读懂这个`、`分析仓库`、`提炼`、`整理`、`梳理`、`底稿`

## 输入字段

```
输入类型（自动识别）：对话 / 仓库 / 技能 / 文档 / 日志
输入内容：[粘贴内容 或 说明要读取的路径]
目标消费者（选填）：planning / debug / teach-plus / 无（快速了解）
输出模式（自动判定）：basic / briefing
```

## 输出结构

### basic 模式

严格遵循 `.claude/protocols/summary-protocol.md`：
- 📦 核心主题
- 🧩 关键模块 / 关键事实
- 📌 重要细节
- ⚠️ 风险 / 缺失点
- 👉 下一步建议

### briefing 模式

严格遵循 `.claude/protocols/briefing-protocol.md`：
- 🎯 对象（名称 + 类型）
- 📖 背景（2~4 句）
- ✅ 已知信息（已确认 vs 推测）
- ❓ 未知信息 / 风险（表格，标注严重程度）
- 🧱 关键结构 / 关键概念
- 🧭 推荐后续工作流（workflow + primary_skill + secondary_skills + 理由）

## 与下游技能的关系

| 下游技能 | 消费 summarize 的什么 | 典型流程 |
|---------|---------------------|---------|
| `planning` | briefing（项目底稿） | summarize/briefing → planning/project → task_ledger |
| `debug` | briefing（问题背景底稿） | summarize/briefing → debug → code_assistant → debug_archive |
| `teach-plus` | briefing（学习底稿） | summarize/briefing → planning/learning → teach-plus |

## 行为规则

- **先识别输入类型，再选择输出模式** — 不跳步
- **输出必须遵循对应协议** — 不自由发挥格式
- **basic 不深入分析** — 那是 briefing 的事
- **briefing 必须推荐后续 workflow** — 给出理由
- **未指定模式时** — 如果输入简短且无下游消费意图 → basic；如果输入复杂或有下游消费意图 → briefing
- **风险必须标注严重程度** — 低/中/高

## 目录结构

```
summarize/
├── SKILL.md          ← 本文件
├── modes/
│   ├── basic.md      ← basic 模式详细说明
│   └── briefing.md   ← briefing 模式详细说明
└── examples/         ← 示例（待补充）
```

## 兼容说明

- 旧 `summarize/SKILL.md` 保留在 `.claude/skills/summarize/SKILL.md`，作为兼容层
- 旧版已包含 A/B 模式的基础定义，v3 将其拆分为独立 mode 文件并新增协议
- 旧版的路由规则（skill-rules.json 中 summarize 条目）仍可正常工作

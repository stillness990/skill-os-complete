# Briefing Protocol（深度底稿协议）

`summarize/briefing` 模式的标准输出协议。是 `summary-protocol` 的"深度版本"，专供 `planning`/`debug`/`teach-plus` 等下游技能消费。

---

## 协议字段

### 对象
- 被分析的对象名称
- 类型标注：仓库 / 技能 / 文档 / 项目 / 对话 / 日志

### 背景
- 2~4 句交代背景
- 为什么需要这份 briefing
- 当前所处阶段

### 已知信息
- 列出所有已知事实
- 按维度分组（如：技术栈、架构、流程、人员）
- 区分"已确认"和"推测"

### 未知信息 / 风险
- 标注缺失信息及影响
- 标注已识别的风险及严重程度（低/中/高）
- 标注不确定的假设

### 关键结构 / 关键概念
- 核心数据流、工作流或模块拓扑
- 3~8 个关键概念及一句话解释

### 推荐后续工作流
- 明确推荐使用哪个 workflow
- 推荐 primary skill
- 推荐 secondary skills（如有）
- 给出理由

---

## 输出模板

```markdown
## 🎯 对象
- 名称：[xxx]
- 类型：仓库 / 技能 / 文档 / 项目 / 对话 / 日志

## 📖 背景
[2~4 句背景说明]

## ✅ 已知信息
### 已确认
- [事实 1]
- [事实 2]

### 推测（待验证）
- [推测 1]

## ❓ 未知信息 / 风险
| 未知/风险 | 严重程度 | 影响 |
|-----------|---------|------|
| [xxx] | 低/中/高 | [xxx] |

## 🧱 关键结构 / 关键概念
- **[概念 1]**：[一句话解释]
- **[概念 2]**：[一句话解释]

### 核心数据流 / 工作流
```
[A] → [B] → [C] → [D]
```

## 🧭 推荐后续工作流
- **推荐 workflow**：`delivery_pipeline` / `debug_pipeline` / `learning_pipeline`
- **primary_skill**：`planning` / `debug` / `teach-plus`
- **secondary_skills**：`task_ledger` / `code_assistant`
- **理由**：[为什么推荐这个链路]
```

---

## 使用场景

| 场景 | 触发条件 |
|------|---------|
| 给 planning 的项目底稿 | 即将做项目拆解/重构/开发 |
| 给 debug 的问题背景 | 复杂问题需要先理解上下文 |
| 给 teach-plus 的学习底稿 | 即将开始系统学习 |

## 与其他协议的关系

- `summary-protocol.md` — basic 模式的轻量输出
- `plan-protocol.md` — planning 消费 briefing 后产出 plan
- `debug-protocol.md` — debug 消费 briefing 后产出诊断

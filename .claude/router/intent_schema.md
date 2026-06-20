# Intent Schema（意图分类协议）

Skill OS v3 的路由器从"关键词→技能"升级为"输入→intent→workflow→skills"。

## 三类 Intent

### 1. `project_delivery`（项目交付）

**适用范围：**
- 项目重构/升级
- 功能拆解/开发
- 方案设计/架构
- 任务规划/拆解

**典型输入模式：**
- "给我一个计划..."
- "怎么实现..."
- "帮我规划..."
- "重构..."
- "设计一个..."
- "拆解..."

**推荐 workflow：** `delivery_pipeline`

### 2. `debug_issue`（问题诊断）

**适用范围：**
- 报错/异常
- 行为异常
- 环境故障
- 运行失败
- 性能问题

**典型输入模式：**
- "报错..."
- "为什么不工作..."
- "行为异常..."
- "帮我排查..."
- "诊断..."
- "卡住了..."

**推荐 workflow：** `debug_pipeline`

### 3. `learn_topic`（学习主题）

**适用范围：**
- 学某个仓库
- 学某个技能体系
- 学某个技术主题
- 学习路线规划

**典型输入模式：**
- "我想学..."
- "教我..."
- "学习路线..."
- "入门..."
- "系统学习..."

**推荐 workflow：** `learning_pipeline`

## Intent 判定逻辑

```
输入文本
    ↓
提取关键词 + 正则匹配
    ↓
如果匹配 debug 类关键词较多 → debug_issue
如果匹配 learn 类关键词较多 → learn_topic
如果匹配 plan/project 类关键词较多 → project_delivery
如果都没有 → fallback（单 skill 模式，兼容旧逻辑）
```

## Fallback 机制

当 intent 不明确或输入非常简单时（如"echo xxx"、"帮我写个函数"），回退到旧版的"单 skill 最高分命中"模式，保证向后兼容。

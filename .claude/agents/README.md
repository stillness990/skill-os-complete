# Agent Definitions（代理定义）— Phase 4 扩展

## 版本

v4.0.0（Skill OS v4 — 结构占位）

## 定位

多代理扩展层的代理定义目录。Phase 4 实现时，此目录将包含：

- `agent_definitions.json` — 子代理的角色、能力和工具定义
- `complexity_detector.py` — 任务复杂度检测器
- `orchestrator.py` — 多代理编排器

## 当前状态

本轮（v4 升级）不实现。目录作为结构占位。

## 预留代理角色（参考）

| 代理 | 角色 | 触发条件 |
|------|------|---------|
| `explorer` | 代码库探索和理解 | 大范围代码搜索 |
| `implementer` | 代码编写和修改 | 实施类任务 |
| `reviewer_agent` | 代码审查 | 质量检查 |
| `test_writer` | 测试编写 | 测试覆盖 |
| `doc_writer` | 文档编写 | 文档更新 |

## 实现原则（Phase 4）

1. 每个代理有明确的 role + responsibility
2. 代理之间通过 orchestrator 协调
3. 所有代理的输出统一写入 task_ledger
4. execution_guard 也约束多代理任务的完成质量

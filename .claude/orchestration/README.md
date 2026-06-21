# Orchestration Layer（多代理编排层）— Phase 4 扩展

## 版本

v4.0.0（Skill OS v4 — 结构占位）

## 定位

> 多代理编排层是 Skill OS v4 的 **Phase 4 扩展层**。当前仓库以单代理 Skill OS 主骨架为主，多代理能力作为扩展预留。

## 当前状态：结构占位

本轮（Phase 2→v4 升级）不实现多代理大规模重写。只做目录结构预留和接口定义。

## 计划内容（Phase 4+）

| 模块 | 用途 | 状态 |
|------|------|------|
| `complexity_detector` | 检测任务复杂度，决定是否启动多代理 | 待实现 |
| `orchestrator` | 多代理任务编排和结果合并 | 待实现 |
| `agent_definitions` | 各子代理的角色和能力定义 | 待实现 |

## 目录结构

```
orchestration/
├── README.md           ← 本文件
├── schema/             ← 编排相关 schema（run-schema, agent-output-schema, merge-schema）
├── runs/               ← 编排运行记录
└── artifacts/          ← 编排产出物
```

## 架构原则

1. **先单后多**：单代理 Skill OS 主骨架稳定后，再接入多代理
2. **不喧宾夺主**：多代理是扩展，不是主链
3. **接口预留**：目录和 schema 占位为后续开发留出清晰接入点

## 与其他层的关系

- 多代理可以调用 Core Skills（summarize / planning / debug）
- 多代理的产出应写入 task_ledger
- 多代理的任务完成受 execution_guard 约束
- 多代理的复杂度检测发生在 router 检测 intent 之后

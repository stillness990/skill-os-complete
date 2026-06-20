# Debug Pipeline（诊断工作流）

## 版本

v1.0.0（Phase 2 文档归一化）

## 概述

Debug Pipeline 是 skill-os-complete 的**问题诊断标准链路**。
从报错到修复归档，定义每个阶段的技能调度。

## 标准链路

```text
用户报错/异常
    ↓
summarize/briefing（问题背景底稿，可选）
    ↓
debug（完整诊断流程）
    ↓
code_assistant（代码修复，按需）
    ↓
debug_log（排查记录归档，按需）
```

## 各阶段说明

| 阶段 | 技能 | 模式 | 产出 | 是否必须 |
|------|------|------|------|---------|
| summarize | summarize | briefing | 问题背景底稿 | 可选 |
| diagnose | debug | full | 诊断报告 | ✅ |
| fix | code_assistant | on_demand | 代码修复 | 按需 |
| archive | debug_log | on_demand | 排查记录归档 | 按需 |

## debug 技能的固定诊断流程

debug 技能内部遵循固定流程：现象 → 最小复现 → 假设 → 验证 → 修复 → 回归检查。

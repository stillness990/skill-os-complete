# Debug Pipeline（诊断工作流）— v4

## 版本

v4.0.0（Skill OS v4）

## 概述

Debug Pipeline 是 Skill OS v4 的**问题诊断标准链路**。
从报错到修复归档，定义每个阶段的技能调度和 execution_guard 检查点。

## 标准链路

```text
用户报错/异常
    ↓
summarize/briefing（问题背景底稿，可选）
    ↓
debug（完整诊断流程：现象→假设→验证→修复建议→回归清单）
    ↓
code_assistant（代码修复，按需）
    ↓
knowledge-asset / troubleshooting（排查记录结构化沉淀）
    ↓
execution_guard（完成检查：debug_report_ref + root_cause + regression checklist）
```

## 各阶段说明

| 阶段 | 技能 | 模式 | 产出 | 是否必须 |
|------|------|------|------|---------|
| summarize | summarize | briefing | 问题背景底稿 | 可选 |
| diagnose | debug | full | 诊断报告 | ✅ |
| fix | code_assistant | on_demand | 代码修复 | 按需 |
| archive | knowledge-asset | troubleshooting | 排查记录归档 | 按需 |
| guard | execution_guard | auto | 完成检查 | ✅ |

## debug 技能的固定诊断流程

debug 技能内部遵循固定流程：现象 → 最小复现 → 假设 → 验证 → 修复 → 回归检查。

## execution_guard 检查点

进入 done 前必须通过以下检查：
- **debug_report_ref**：是否存在诊断报告引用
- **root_cause**：是否明确了根因
- **fix_ref 或 diagnosis-only**：是否有修复引用，或明确标注"仅诊断不修复"
- **regression_checklist_ref**：是否有回归检查清单

## debug 与 code_assistant 的边界

- `debug` = 诊断、定位、修复建议（不写代码）
- `code_assistant` = 根据 debug 的修复建议真正修改代码
- debug 诊断完成后明确标注需交给 code_assistant 的改动点（文件 + 内容）

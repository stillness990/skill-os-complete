# Delivery Pipeline（项目交付工作流）— v4

## 版本

v4.0.0（Skill OS v4）

## 概述

Delivery Pipeline 是 Skill OS v4 的**项目交付标准链路**。
从需求到发布，定义每个阶段的技能调度、产出物和 execution_guard 检查点。

## 标准链路

```text
用户项目请求
    ↓
summarize/briefing（项目底稿）
    ↓
planning/project（阶段计划 + 今日行动）
    ↓
task_ledger（任务条目写入）
    ↓
code_assistant（代码变更，按需）
    ↓
reviewer（审查意见，按需）
    ↓
changelog（变更日志，按需）
    ↓
execution_guard（完成检查：artifact 验证 + 状态流转合法性）
```

## 各阶段说明

| 阶段 | 技能 | 模式 | 产出 | 是否必须 |
|------|------|------|------|---------|
| understand | summarize | briefing | 项目底稿 | ✅ |
| plan | planning | project | 阶段计划 + 今日行动 | ✅ |
| track | task_ledger | auto | 任务条目写入 | ✅ |
| execute | code_assistant | on_demand | 代码变更 | 按需 |
| review | reviewer | on_demand | 审查意见 | 按需 |
| release | changelog | on_demand | 变更日志 | 按需 |
| guard | execution_guard | auto | 完成检查 | ✅ |

## execution_guard 检查点

进入 done 前必须通过以下检查：
- **plan_ref**：是否存在 planning 产出的计划引用
- **changed_files**：实施类任务是否有实际文件变更
- **artifact**：是否有有效产出物引用（不允许空完成）
- **状态流转**：是否从合法状态流转到 done

## 辅助技能

- `sanitize`：发布前脱敏
- `knowledge-asset`（sop 模式）：生成标准操作流程文档

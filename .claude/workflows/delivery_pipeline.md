# Delivery Pipeline（项目交付工作流）

## 版本

v1.0.0（Phase 2 文档归一化）

## 概述

Delivery Pipeline 是 skill-os-complete 的**项目交付标准链路**。
从需求到发布，定义每个阶段的技能调度和产出物。

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

## 辅助技能

- `sanitize`：发布前脱敏
- `sop`：生成操作手册

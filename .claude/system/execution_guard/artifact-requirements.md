# Artifact Requirements（产物要求）— v5

## 版本

v5.0.0（Skill OS v5 execution_guard — 新增 knowledge_asset_ref 要求）

## 概述

定义不同任务类型进入 `done` 状态时的最小产物要求。execution_guard 在任务完成时必须按此文档逐项检查。

v5 核心变化：所有产生长期知识的 task_type 新增 `knowledge_asset_ref` 要求（L0 Knowledge Bus 闭环）。

## 核心原则

> **done 必须带 artifact。不允许只改状态不留证据。**

---

## 1. delivery / implementation 类任务

**task_type**：`delivery`
**workflow**：`delivery_pipeline`

### 最小 artifact 组合（必须满足以下至少 3 项）

| artifact | 说明 | 必选 |
|----------|------|------|
| `plan_ref` | 指向 planning 产出的计划文档 | ✅ 必选 |
| `implementation_ref` | 指向实现文档或说明 | 推荐 |
| `changed_files` | 实际变更的文件列表 | ✅ 必选（实施类） |
| `knowledge_asset_ref` | knowledge-asset 沉淀引用 (project-plan) | ✅ 必选（施工类）/ 推荐（方案类） |
| `changelog_ref` | 变更日志引用 | 按需 |
| `review_ref` | 代码审查意见引用 | 按需 |
| `result_summary` | 结果摘要 | ✅ 必选 |

### 特殊规则

- **实施型 delivery**：必须有 `changed_files` 或明确的文档更新结果。不允许只有口头说"已完成"。
- **方案型 delivery（plan_only）**：允许 `planning → done`，但必须有明确的 plan artifact。

### 施工类任务特别约束

如果任务类型是"仓库实施 / 改代码 / 改文档 / 重构"，done 前至少要有：
- `changed_files`：非空文件列表
- `result_summary`：至少一句话描述改了什么
- 不允许只有"我已经完成"的口头说明

---

## 2. debug 类任务

**task_type**：`debug`
**workflow**：`debug_pipeline`

### 最小 artifact 组合

| artifact | 说明 | 必选 |
|----------|------|------|
| `debug_report_ref` | 诊断报告引用 | ✅ 必选 |
| `knowledge_asset_ref` | knowledge-asset 沉淀引用 (troubleshooting) | ✅ 必选（v5 新增） |
| `root_cause` | 根因描述 | ✅ 必选 |
| `fix_recommendation` | 修复建议 | ✅ 必选 |
| `fix_ref` | 修复引用（如实际修了） | 按需 |
| `diagnosis_only` | 标注"仅诊断不修复" | 按需（如果无 fix_ref） |
| `regression_checklist_ref` | 回归检查清单引用 | ✅ 必选 |

### 特殊规则

- 如果只诊断不修复：必须明确标注 `diagnosis_only: true`，并说明原因
- 如果诊断 + 修复：必须有 `fix_ref` 指向实际修复内容
- `root_cause` 不能为空或"待定"

---

## 3. learning 类任务

**task_type**：`learning`
**workflow**：`learning_pipeline`

### 最小 artifact 组合

| artifact | 说明 | 必选 |
|----------|------|------|
| `study_plan_ref` | 学习计划引用 | 推荐 |
| `practice_log_ref` | 练习日志引用 | 推荐 |
| `review_log_ref` | 复盘日志引用 | 推荐 |
| `knowledge_asset_ref` | knowledge-asset 沉淀引用 (knowledge-note) | ✅ 必选（v5 新增） |
| `learning_state_update` | 学习状态已更新 | ✅ 必选 |
| `next_action` | 下一步学习建议 | ✅ 必选 |
| `next_review` | 下次复盘日期 | 推荐 |

### 特殊规则

- learning 任务 done 时，`learning_state` 必须已更新（current_stage / last_activity_at / next_action）
- 如果 learning 任务被标记为 done 但 learning_state 未更新，execution_guard 应警告

---

## 4. plan_only 类任务

**task_type**：`plan_only`

### 最小 artifact 组合

| artifact | 说明 | 必选 |
|----------|------|------|
| `plan_ref` | 计划文档路径 | ✅ 必选 |

### 特殊规则

- `plan_only` 是唯一允许 `planning → done` 直接完成的任务类型
- 但 plan 本身不能为空——必须有实际产出的计划文档
- 如果 plan_ref 指向的文件不存在或为空，不允许 done

---

## 5. knowledge_asset_ref 验证规则（v5 新增）

### 5.1 验证流程

```
任务请求 done
    ↓
检查 task_type 是否需要 knowledge_asset_ref
    ↓
[强制类型] → knowledge_asset_ref 非空? → 引用文件存在? → 通过
[推荐类型] → knowledge_asset_ref 非空? → 记录为 bonus ✓
[不适用]   → 跳过
```

### 5.2 各 task_type 的 knowledge_asset_ref 要求

| task_type | 要求级别 | 模板 | 写入路径 |
|-----------|---------|------|---------|
| `debug` | ✅ 强制 | `troubleshooting` | `knowledge/troubleshooting/` |
| `learning` | ✅ 强制 | `knowledge-note` | `knowledge/knowledge-notes/` |
| `delivery` (施工类) | ✅ 强制 | `project-plan` | `knowledge/project-plans/` |
| `delivery` (plan_only) | 推荐 | `project-plan` | `knowledge/project-plans/` |
| `code_assistant` | 可选 | `architecture` | `knowledge/architecture/` |
| `reviewer` / `changelog` | 不适用 | — | — |

### 5.3 引用路径验证

`knowledge_asset_ref` 指向的路径必须满足以下条件之一：
- 相对于项目根目录存在（如 `knowledge/troubleshooting/2026-06-21_xxx.md`）
- 基于 `.claude/skills/knowledge-asset/` 的完整路径存在
- 路径格式合理（非占位符，非空字符串）

---

## 6. 通用 done 规则（所有 task_type 适用）

1. **artifacts 数组不能为空**：至少要有 1 个有效 artifact
2. **artifact_refs 中至少有一个字段被填充**：不能所有字段都为 null
3. **result_summary 不能为空或过于简短**：至少 10 个字符
4. **不能只有"已完成"等口头描述**：必须有文件路径或具体引用

---

## execution_guard 检查流程

```
任务请求进入 done
    ↓
1. 检查 task_type
    ↓
2. 按 task_type 加载对应的 artifact 要求
    ↓
3. 逐项检查 artifact_refs 是否满足最小要求
    ↓
4. [v5 新增] 检查 knowledge_asset_ref（L0 Knowledge Bus 闭环）
    ↓
5. 检查通用 done 规则
    ↓
6. [v5 新增] 验证 state/ 文件更新（L4 State 闭环）
    ↓
7. 全部通过 → 允许 done
   任一失败 → 拒绝 done，返回缺少的 artifact 清单
```

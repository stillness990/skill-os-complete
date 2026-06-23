# Skill OS v5 — 执行链路

> 版本：v5.0.0 | 生成：2026-06-22 | Phase 8 最终交付

---

## 一、概述

Skill OS v5 的执行链路从用户输入开始，经过 L1 Router 分发 → L3 Workflow 编排 → L2 Core 执行 → L0 Knowledge Bus 沉淀 → L4 State 更新 → L5 Guard 校验，形成完整闭环。

### 端到端流程

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ L1 Router                                               │
│   PromptNormalizer → RuleRouter → SemanticRouter        │
│   → intent + workflow + primary skill                   │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ L3 Workflow                                             │
│   delivery_pipeline / debug_pipeline / learning_pipeline │
│   → 按 pipeline 编排 skill 执行顺序                      │
└──────────────────────────┬──────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │summarize │    │ planning │    │  debug   │  ← L2 Core
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌─────────┐ ┌───────┐ ┌─────────┐
         │ L0      │ │ L4    │ │ L5      │
         │Knowledge│ │State  │ │Guard    │
         │ Bus     │ │       │ │         │
         └─────────┘ └───────┘ └─────────┘
              │          │          │
              └──────────┼──────────┘
                         │
                         ▼
                   Next Step / User
```

---

## 二、三条 Pipeline

### 2.1 Delivery Pipeline（项目交付）

**触发**：项目规划、重构、开发、代码修改等 `project_delivery` intent。

**完整链路**（8 stages）：

```
Stage 1: summarize
    │  输入: 用户需求描述
    │  输出: briefing (结构化需求摘要)
    │  L0:   可选 → knowledge-asset (knowledge-note/architecture)
    │  Guard: 无 (stage 未完成不触发)
    │
    ▼
Stage 2: planning
    │  输入: briefing
    │  输出: plan + 今日最小行动
    │  L0:   可选 → knowledge-asset (project-plan)
    │  Guard: plan_ref 非空检查
    │
    ▼
Stage 3: task_ledger
    │  输入: plan
    │  输出: task entries (queued)
    │  L4:   写入 state/current-task.json
    │  Guard: task 创建成功检查
    │
    ▼
Stage 4: code_assistant
    │  输入: task + plan
    │  输出: 代码变更
    │  L0:   可选 → knowledge-asset (architecture, 重大改动)
    │  L4:   更新 current-task.json (status: executing)
    │  Guard: changed_files 检查 (施工类)
    │
    ▼
Stage 5: reviewer
    │  输入: changed_files
    │  输出: review 意见
    │  L0:   不入沉淀 (即时反馈)
    │  Guard: review_ref 可选
    │
    ▼
Stage 6: changelog
    │  输入: changed_files + review
    │  输出: 变更日志
    │  L0:   不入沉淀
    │  Guard: 无
    │
    ▼
Stage 7: knowledge-asset
    │  输入: 全部产出
    │  输出: knowledge_asset_ref
    │  L0:   写入 knowledge/project-plans/ (施工类强制)
    │  Guard: knowledge_asset_ref 非空检查 (施工类)
    │
    ▼
Stage 8: execution_guard
    │  输入: 全部产出 + state
    │  输出: validation_result (pass/fail)
    │  L4:   更新 execution-state.json (guard_status)
    │  L5:   5 层校验
    │
    ▼
Done → task → state/task-history.json
```

**最小产物要求**：
- `plan_ref` ✅
- `changed_files` ✅ (实施类)
- `knowledge_asset_ref` ✅ (施工类) / 推荐 (方案类)
- `result_summary` ✅

---

### 2.2 Debug Pipeline（故障诊断）

**触发**：报错、异常、行为异常等 `debug_issue` intent。

**完整链路**（5 stages）：

```
Stage 1: summarize (可选)
    │  输入: 错误描述
    │  输出: 结构化错误摘要
    │  L0:   可选
    │
    ▼
Stage 2: debug
    │  输入: 错误摘要 + 复现步骤
    │  输出: 诊断报告 (root_cause + fix_recommendation + regression_checklist)
    │  L0:   强制 → knowledge-asset (troubleshooting)
    │  Guard: debug_report_ref + root_cause 检查
    │
    ▼
Stage 3: code_assistant
    │  输入: 诊断报告 + fix_recommendation
    │  输出: 修复代码
    │  L4:   更新 current-task.json
    │  Guard: changed_files 检查
    │
    ▼
Stage 4: knowledge-asset
    │  输入: 诊断报告 + 修复记录
    │  输出: knowledge_asset_ref (troubleshooting)
    │  L0:   写入 knowledge/troubleshooting/
    │  Guard: knowledge_asset_ref 非空 + 文件存在
    │
    ▼
Stage 5: execution_guard
    │  输入: 全部产出
    │  输出: validation_result
    │  L5:   5 层校验 (debug 特有: root_cause + regression_checklist)
    │
    ▼
Done → task → state/task-history.json
```

**最小产物要求**：
- `debug_report_ref` ✅
- `knowledge_asset_ref` ✅ (troubleshooting)
- `root_cause` ✅
- `fix_recommendation` ✅
- `regression_checklist_ref` ✅

**诊断流程**（debug skill 内部）：
```
确认现象 → 最小复现 → 假设 → 验证 → 根因 → 修复建议 → 回归清单 → knowledge-asset 沉淀
```

---

### 2.3 Learning Pipeline（学习工作流）

**触发**：学习、教程、复盘、练习等 `learn_topic` intent。

**完整链路**（9 stages）：

```
Stage 1: summarize
    │  输入: 学习主题
    │  输出: 学习底稿 (learning brief)
    │  L0:   可选 → knowledge-asset (knowledge-note)
    │
    ▼
Stage 2: planning
    │  输入: 学习底稿
    │  输出: 学习计划 (阶段 + 里程碑 + 每日任务)
    │  L0:   可选 → knowledge-asset (project-plan)
    │
    ▼
Stage 3: teach-plus/explain
    │  输入: 学习计划 + 学习底稿
    │  输出: 概念讲解 + 示例
    │  L0:   强制 → knowledge-asset (knowledge-note)
    │  L4:   创建 learning-state topic (topic_new → understanding)
    │  Guard: learning_state 更新检查
    │
    ▼
Stage 4: teach-plus/practice
    │  输入: 讲解内容
    │  输出: 练习结果 + 练习日志
    │  L0:   强制 → knowledge-asset (knowledge-note)
    │  L4:   更新 learning-state (current_stage / last_activity_at)
    │  Guard: learning_state 已更新检查
    │
    ▼
Stage 5: task_ledger
    │  输入: 练习结果
    │  输出: 学习任务记录
    │  L4:   更新 current-task.json
    │
    ▼
Stage 6: learning_state
    │  输入: 所有学习活动
    │  输出: 状态更新 (understanding → guided_practice → independent_practice)
    │  L4:   更新 state/learning-state.json
    │  Guard: 状态流转合法性
    │
    ▼
Stage 7: teach-plus/review
    │  输入: 学习记录 + learning_state
    │  输出: 复盘报告 + next_action + next_review
    │  L0:   强制 → knowledge-asset (knowledge-note)
    │  L4:   更新 review_ref / next_review
    │  Guard: next_action 非空检查
    │
    ▼
Stage 8: knowledge-asset
    │  输入: 全部学习产出
    │  输出: knowledge_asset_ref (knowledge-note)
    │  L0:   写入 knowledge/knowledge-notes/
    │  Guard: knowledge_asset_ref 非空 + 文件存在
    │
    ▼
Stage 9: execution_guard
    │  输入: 全部产出 + learning_state
    │  输出: validation_result
    │  L5:   5 层校验 (learning 特有: learning_state + next_action)
    │
    ▼
Done → task → state/task-history.json
```

**最小产物要求**：
- `knowledge_asset_ref` ✅ (knowledge-note)
- `learning_state` 更新 ✅
- `next_action` ✅
- `next_review` 推荐

---

## 三、Guard 检查点

### 3.1 每 Stage 后的检查

| 检查时机 | 检查内容 | 执行者 |
|---------|---------|--------|
| Stage 完成后 | artifact 产出 | completion-guard (Layer 2-3) |
| 状态变更时 | 流转合法性 | task-guard |
| Pipeline 推进时 | 当前 stage 完成条件 | completion-guard |
| 任务 done 前 | 5 层完整校验 | completion-guard |
| 会话开始时 | stall 检测 + 上下文注入 | task-guard |

### 3.2 5 层校验详情

```
completion-guard.py 校验顺序:

Layer 1: validate_state_transition()
  ├── 检查: queued→done? planning→done (非plan_only)?
  ├── 检查: 终态(done/cancelled)不可逆
  └── 违规: 拒绝 done, 返回非法流转说明

Layer 2: check_artifacts()
  ├── 检查: artifacts 数组非空
  ├── 检查: result_summary ≥ 10 字符
  ├── 检查: 施工类 changed_files 非空
  └── 违规: 拒绝 done, 返回缺失 artifact 清单

Layer 3: check_task_type_artifacts()
  ├── debug: debug_report_ref + root_cause
  ├── delivery: plan_ref
  ├── learning: next_action
  └── 违规: 拒绝 done, 返回缺失项

Layer 4: check_knowledge_asset_ref() [v5 新增]
  ├── debug: troubleshooting 模板 → knowledge_asset_ref 强制
  ├── learning: knowledge-note 模板 → knowledge_asset_ref 强制
  ├── delivery: project-plan 模板 → 施工强制/方案推荐
  ├── 引用文件存在性验证
  └── 违规: 强制类型缺少 → 拒绝 done; 推荐类型缺少 → warning

Layer 5: check_state_update() [v5 新增]
  ├── execution-state.json 存在且反映当前任务
  ├── learning 任务: learning-state.json topic 已更新
  ├── 最近 7 天活动记录 (learning)
  └── 违规: learning 任务 → 拒绝 done; 其他 → warning
```

---

## 四、状态流转

### 4.1 Task 状态流转

```
queued → planning → executing → done
            ↓         ↓
        blocked ←──────+────→ retrying
            ↓              ↓
            +──→ stalled ←─+
                   ↓
            planning / executing (恢复后)

任意活动态 → cancelled (用户取消)
```

**关键约束**：
- `planning → done` 仅 `plan_only` 类型合法
- `queued → done` 非法（跳步骤）
- `blocked/retrying/stalled → done` 非法（未恢复执行）
- 终态不可逆

### 4.2 Learning Topic 状态流转

```
topic_new → understanding → guided_practice → independent_practice
                                                 ↓
                                           consolidation
                                                 ↓
                                            review_due
                                                 ↓
                                             mastered
```

**异常状态**：`paused`, `stalled`, `restart_needed`

### 4.3 Pipeline 状态流转

```
not_started → in_progress → completed
                        ↘ failed → retrying → in_progress
                                 ↘ safe_mode → degraded_completed
```

---

## 五、异常处理与恢复

### 5.1 Stall 检测

| 检测源 | 阈值 | 动作 |
|--------|------|------|
| `current-task.json` 3 天未更新 | warning | 提示更新进度 |
| `current-task.json` 7 天未更新 | stalled | 标记 stalled |
| `learning-state.json` 3 天未活动 | warning | 提示恢复学习 |
| `learning-state.json` 7 天未活动 | stalled | 标记断档 |
| retry_count ≥ 3 | warning | 分析失败模式 |
| retry_count ≥ 5 | stalled | 标记 stalled |

### 5.2 Checkpoint 恢复

```
恢复流程:
  1. 读取 state/execution-state.json → 确定 workflow + current stage
  2. 读取 state/current-task.json → 确定 task 进度
  3. 验证 knowledge_asset_ref 存在性
  4. 找到最近 checkpoint → 恢复状态快照
  5. resume 或 rollback 到最近合法状态
```

### 5.3 Safe Mode

当连续失败或检测到异常时，系统进入 safe_mode：
- 暂停高风险操作
- 强制 checkpoint
- 降低自动化级别
- 需要用户明确确认后才能继续

---

## 六、Hook 执行时序

```
会话生命周期中的 hook 触发点:

1. UserPromptSubmit
   ├── skill-router.py    → intent → workflow → skill 指令注入
   └── task-guard.py      → stall 检测 + 上下文注入

2. PreToolUse (状态变更时)
   └── task-guard.py      → 状态流转校验

3. 任务 done 前
   └── completion-guard.py → 5 层校验

4. 会话空闲 / 定时
   └── task-guard.py      → 定期 stall 扫描
```

---

## 七、文件索引

| 文件 | 内容 |
|------|------|
| `.claude/workflows/delivery_pipeline.md` | Delivery pipeline 详细说明 |
| `.claude/workflows/debug_pipeline.md` | Debug pipeline 详细说明 |
| `.claude/workflows/learning_pipeline.md` | Learning pipeline 详细说明 |
| `.claude/hooks/skill-router.py` | Router hook |
| `.claude/hooks/task-guard.py` | Task guard hook (stall + context) |
| `.claude/hooks/completion-guard.py` | Completion guard hook (5-layer validation) |
| `.claude/system/execution_guard/task-state-machine.md` | Task 状态机定义 |
| `.claude/system/execution_guard/stall-policy.md` | Stall 检测策略 |
| `.claude/state/execution-state.json` | Pipeline 进度 (运行时) |
| `.claude/state/current-task.json` | 活跃任务 (运行时) |

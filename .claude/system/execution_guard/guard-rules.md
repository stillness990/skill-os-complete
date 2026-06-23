# Guard Rules（监督规则）— v5

## 版本

v5.0.0（Skill OS v5 execution_guard — 从 v4 5 条规则扩展到 v5 7 条规则）

## 概述

execution_guard 的 7 条核心监督规则。v4 的 5 条规则（artifact/流转/产物/落地/超时）全部保留，v5 新增 2 条闭环规则（L0 Knowledge Bus + L4 State）。每一条都是强制性的，不可跳过。

---

## Rule 1：done 必须带 artifact

> 任何任务进入 `done`，必须有至少一个有效 artifact 引用。

**检查项：**
- `artifacts` 数组非空
- `artifact_refs` 中至少有一个字段非空
- `result_summary` 非空且长度 ≥ 10 字符

**不同 task_type 的细化约束：** 见 `artifact-requirements.md`

**违规后果：** 拒绝 done 请求，返回"缺少 artifact"提示

---

## Rule 2：状态流转必须合法

> 所有任务状态更新都必须符合 `task-state-machine.md`。

**检查项：**
- 来源状态 → 目标状态是否在合法流转表中
- `planning → done` 只在 task_type 为 `plan_only` 时合法
- 终态（done/cancelled）不可逆

**违规后果：** 拒绝状态变更，返回"非法状态流转：{from} → {to}"提示

---

## Rule 3：workflow 最小产物检查

> 不同 workflow 至少要满足最小产物要求。

**检查项：**

| workflow | 最小要求 |
|----------|---------|
| `delivery_pipeline` | plan_ref + changed_files（实施类）或 plan_ref（方案类） |
| `debug_pipeline` | debug_report_ref + root_cause + regression_checklist_ref |
| `learning_pipeline` | learning_state 更新 + next_action |

**违规后果：** 拒绝 done，返回缺少的具体产物项

---

## Rule 4：施工任务必须有落地证据

> 如果 task_type 为 `delivery` 且涉及仓库实施/改代码/改文档/重构，done 前至少要有 changed_files 或明确的文档更新结果。

**判断逻辑：**
1. 检查 task_type 是否为 `delivery`
2. 检查 title / description 是否包含"实施""重构""修改""创建""部署"等关键词
3. 如果是施工类 → 必须有 changed_files（非空）或文档更新证明
4. 如果只是方案类 → task_type 必须是 `plan_only`，不能伪装成 `delivery`

**违规后果：** 拒绝 done，提示"施工任务必须有落地证据，不能只有口头完成。如果是纯方案任务请标记 task_type=plan_only"

---

## Rule 5：超时未更新处理

> 超过阈值未更新的任务，标记 stalled 或 warning。

**检查项：** 见 `stall-policy.md`

**处理流程：**
1. execution_guard 定期扫描任务
2. 检测 planning / executing / retrying 状态的任务
3. 超过阈值 → 标记 stalled 或添加 warning
4. 向用户提示卡住的任务

---

## Rule 6：knowledge-asset 强制沉淀（v5 L0 Knowledge Bus 闭环）

> 任何产生长期知识的任务，done 前必须通过 knowledge-asset 引擎沉淀结构化产出。

**适用 task_type：**

| task_type | 是否强制 | 模板 | 说明 |
|-----------|---------|------|------|
| `debug` | ✅ 强制 | `troubleshooting` | 诊断报告必须通过 knowledge-asset 沉淀 |
| `learning` | ✅ 强制 | `knowledge-note` | 学习笔记必须通过 knowledge-asset 沉淀 |
| `delivery`（施工类） | ✅ 强制 | `project-plan` | 实施完成后必须沉淀计划/总结 |
| `delivery`（纯方案 plan_only） | 推荐 | `project-plan` | 方案完成后建议沉淀 |
| `code_assistant` | 可选 | `architecture` | 重大架构变更时建议沉淀 |
| `reviewer` / `changelog` | 不适用 | — | 即时反馈型，不入沉淀 |

**检查项：**
- `outputs.knowledge_asset_ref` 是否非空（针对强制类型）
- 引用的 knowledge-asset 文件是否实际存在
- knowledge-asset 输出是否符合 9-section schema
- 写入路径是否在 `.claude/skills/knowledge-asset/knowledge/` 下

**违规后果：**
- 强制类型缺少 knowledge_asset_ref：拒绝 done
- 引用文件不存在：拒绝 done，返回"knowledge_asset_ref 指向文件不存在"
- 可选类型缺少：warning，不阻塞 done

**禁止项：**
- ❌ 任何 skill 直接写入 `knowledge/*` 或 `docs/*`（绕过 knowledge-asset）
- ❌ 用口头描述代替结构化沉淀（如"已排查完毕"而不写 troubleshooting doc）

---

## Rule 7：state/ 更新检查（v5 L4 State 闭环）

> 任务完成时，必须同步更新 `state/` 中的状态文件，确保状态层反映最新进展。

**检查项：**

| state 文件 | 触发条件 | 要求 |
|-----------|---------|------|
| `state/current-task.json` | 所有任务 | `status` 已更新为 `done`；`outputs` 字段完整 |
| `state/execution-state.json` | delivery/debug pipeline | `pipeline_progress` 当前 stage 标记 completed；`guard_status` 更新 |
| `state/learning-state.json` | learning 任务 | 对应 topic 的 `current_stage` / `last_activity_at` / `knowledge_assets` 已更新 |
| `state/task-history.json` | 所有任务 | 任务归档至 history（由 execution_guard 自动完成） |

**验证流程：**
1. 读取 `state/current-task.json` → 确认 task 存在且 status 合法
2. 读取 `state/execution-state.json` → 确认 pipeline 进度已推进
3. 对 learning 任务 → 额外读取 `state/learning-state.json` → 确认 topic 已更新
4. done 通过后 → 自动将 task 从 `current-task.json` 移至 `task-history.json`

**违规后果：**
- state/ 文件不存在：拒绝 done（系统未初始化）
- learning 任务 state 未更新：拒绝 done
- 其他任务 state 未更新：warning + 提示建议更新

---

## v4 → v5 规则对照

| v4 规则 | v5 规则 | 变化 |
|---------|---------|------|
| Rule 1: artifact | Rule 1: artifact | 不变 |
| Rule 2: 状态流转 | Rule 2: 状态流转 | 不变 |
| Rule 3: workflow 产物 | Rule 3: workflow 产物 | v5 增加 knowledge_asset_ref 要求 |
| Rule 4: 施工落地 | Rule 4: 施工落地 | 不变 |
| Rule 5: 超时处理 | Rule 5: 超时处理 | v5 扩展检测范围至 state/ 三文件 |
| — | **Rule 6: knowledge-asset 沉淀** | v5 新增 — L0 Knowledge Bus 闭环 |
| — | **Rule 7: state/ 更新** | v5 新增 — L4 State 闭环 |

---

## execution_guard 与各层的协作

| 协作层 | 方式 | 说明 |
|--------|------|------|
| `state/` (v5) | 读取/校验/写入 | guard 读取 `state/current-task.json` 和 `state/execution-state.json`，校验后回写 guard_status 和 checkpoint |
| `knowledge-asset` (v5 L0) | 读取/校验 | guard 验证 `knowledge_asset_ref` 存在性和路径合法性 |
| `task_ledger` (v4 legacy) | 读取/校验 | ~~guard 读取 ledger 中的任务状态和 artifact，校验后回写 guard_status~~ → v5 已迁移至 `state/` |
| `hook 层` | 触发点 | task-guard.py 在状态变更时调用，completion-guard.py 在 done 时调用 |
| `router` | 预留 | router 可在注入指令中加入 guard 状态提示 |
| `summarize` | 消费 guard 提示 | summarize 可读取 guard_status 来识别风险 |
| `planning` | 基准参照 | planning 的 plan 定义了产物期望，guard 据此检查 |

> **v5 注意**：状态读写已统一至 `.claude/state/`。execution_guard 的 primary source 现在是 `state/current-task.json` + `state/execution-state.json`。旧 `system/task_ledger/tasks.json` 仅保留为 legacy 参考。v5 新增 knowledge-asset 检查（Rule 6）和 state/ 检查（Rule 7），形成 L0 → L4 → L5 三层闭环。

# Guard Rules（监督规则）— v4

## 版本

v4.0.0（Skill OS v4 execution_guard）

## 概述

execution_guard 的 5 条核心监督规则。每一条都是强制性的，不可跳过。

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

## execution_guard 与各层的协作

| 协作层 | 方式 | 说明 |
|--------|------|------|
| `task_ledger` | 读取/校验 | guard 读取 ledger 中的任务状态和 artifact，校验后回写 guard_status |
| `hook 层` | 触发点 | task-guard.py 在状态变更时调用，completion-guard.py 在 done 时调用 |
| `router` | 预留 | router 可在注入指令中加入 guard 状态提示 |
| `summarize` | 消费 guard 提示 | summarize 可读取 guard_status 来识别风险 |
| `planning` | 基准参照 | planning 的 plan 定义了产物期望，guard 据此检查 |

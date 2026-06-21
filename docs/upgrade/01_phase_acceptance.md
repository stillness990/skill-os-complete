# 01 Phase Acceptance — 自动验收清单

> 本文件定义 Claude 在每个 Phase 完成后必须执行的自动检查项。  
> 每个检查项必须标记为：
>
> - `PASS`
> - `FAIL`
> - `PARTIAL`
>
> 若任何**关键项（Critical）**未通过，则该阶段必须判定为 `NO-GO`。

---

# Phase 1 — 仓库审计 + 改造映射 + 升级骨架

## 验收项

### P1-1 仓库结构已完整读取（Critical）
必须识别并列出：
- skills
- router / orchestration 逻辑
- execution_guard
- task_ledger / state
- docs / tests / config

### P1-2 已输出仓库审计文档（Critical）
必须至少包含：
- 仓库当前模块结构
- 主链路入口
- 现有 skills 列表
- guard / ledger / router 现状

### P1-3 已输出升级映射表（Critical）
映射表至少包含：
- summarize
- planning
- debug
- ask
- router
- execution_guard
- task_ledger
- workflow entry

并且每项至少说明：
- 当前文件
- 当前职责
- 存在问题
- 升级动作
- 升级后落点

### P1-4 已输出风险清单（Critical）
至少包含：
- 假升级风险
- 主链断裂风险
- SAFE MODE 未接通风险
- rollback 越界删除风险
- self-healing 失控风险

### P1-5 已创建升级文档骨架（Critical）
至少存在：
- `docs/upgrade/02_phase_report_template.md`
- `docs/architecture/`
- `docs/validation/`
- `docs/failure/`

### P1-6 本轮未提前大改业务主链（Critical）
不得：
- 重写 execution 主流程
- 切换主入口
- 删除旧 router
- 重写技能链

---

# Phase 2 — 协议层 + Schema + Ledger 升级

## 验收项

### P2-1 RoutePlan 协议层已落地（Critical）
必须支持至少：
- route_id
- workflow
- confidence
- intent
- stages
- expected_artifacts
- task_actions
- guard_policy

### P2-2 workflow_state 已落地（Critical）
必须能表达：
- 当前 route / workflow
- 当前 stage
- execution status
- safe_mode status
- retry / failure state

### P2-3 orchestration_types 已落地（Critical）

### P2-4 ledger_schema 已升级（Critical）
必须支持：
- task_id
- route_id
- workflow
- intent
- stage_id
- stage_status
- execution_status
- expected_artifacts
- artifact_paths
- retry_count
- same_failure_type_count
- failure_type
- next_action
- safe_mode
- updated_at

### P2-5 task_ledger 已支持 route/stage/artifact/retry/safe_mode（Critical）

### P2-6 artifact_paths 已纳入安全规则（Critical）
必须满足：
- 使用 repo-root 相对路径存储
- 禁止 `../`
- rollback 前可 resolve 到 repo-root 内
- 越界路径可被拒绝

### P2-7 若存在旧 ledger，已定义兼容策略（Recommended）

### P2-8 本轮至少有最小测试或自检（Recommended）

---

# Phase 3 — prompt-normalizer + rule-router + routing assets

## 验收项

### P3-1 prompt-normalizer 已实现（Critical）
必须支持：
- `/plan /debug /task /next`
- repo_analysis / planning / debug / learning / construction_prompt
- multi-intent

### P3-2 rule-router 已实现（Critical）

### P3-3 routing_assets 已落地（Critical）
至少包括：
- `route_examples.json`
- `workflow_cards.json`
- `skill_cards.json`

### P3-4 以下场景可通过 rule path 正确路由（Critical）
1. 读取项目并评估功能，再给升级方案 → `delivery_pipeline`
2. 生成 Claude 施工单 → `delivery_pipeline`
3. docker compose up 报 permission denied → `debug_pipeline`
4. 学习类请求 → `learning_pipeline`

### P3-5 暂时不依赖 embedding 也能跑通基本路由（Critical）

### P3-6 本轮有 normalizer/router 测试或示例输出（Recommended）

---

# Phase 4 — semantic-router + workflow-resolver

## 验收项

### P4-1 semantic-router 已接入（Critical）

### P4-2 embedding health check 已实现（Critical）
至少检查：
- 服务可达性
- 模型可调用性
- 超时
- 失败时返回 degraded 状态

### P4-3 semantic-router 能读取 routing_assets（Critical）

### P4-4 workflow-resolver 已实现（Critical）

### P4-5 resolver 能融合以下输入（Critical）
- normalized input
- rule candidates
- semantic candidates
- safe_mode state

### P4-6 resolver 能输出唯一合法 RoutePlan（Critical）

### P4-7 三大场景 RoutePlan 正确（Critical）
1. 读取项目并评估功能，再给升级方案  
   → `delivery_pipeline`  
   → 至少包含 `summarize -> planning`

2. 生成 Claude 施工单  
   → `delivery_pipeline`  
   → 至少包含 `summarize -> planning -> ask`

3. docker compose up 报 permission denied  
   → `debug_pipeline`  
   → 至少包含 `debug(diagnose)`

### P4-8 semantic-router 失败时系统不会崩（Critical）

---

# Phase 5 — skill-router + execution_guard + rollback + self-healing + safe_mode

## 验收项

### P5-1 skill-router 已按 RoutePlan 执行（Critical）
必须：
- 按 stage 顺序执行
- 不重新做路由决策
- 将 stage 状态写入 ledger
- 收集 artifact_paths

### P5-2 execution_guard 已实现（Critical）
必须检查：
- required stages
- stage 顺序
- expected_artifacts
- ledger 更新
- no-op completion

### P5-3 pipeline 专项校验已接入（Critical）
必须检查：
- delivery_pipeline 不得跳 summarize / planning
- construction_prompt 不得缺 ask
- debug_pipeline 不得缺 diagnose

### P5-4 self-healing 已实现并有限制（Critical）
必须满足：
- retry_count ≤ 3
- same_failure_type_count ≤ 2
- embedding_fail → immediate fallback
- 不可递归调用自己
- 每次 retry 新 route_id

### P5-5 rollback 已真实读取 ledger 的 artifact_paths（Critical）

### P5-6 rollback 已实现 repo-root 路径安全清理（Critical）
必须：
- normalize
- resolve
- boundary check
- 越界拒绝删除并记录错误

### P5-7 safe_mode 基础逻辑已接入（Critical）
至少包括：
- safe_mode 状态存储
- safe_mode 切换入口
- resolver / router / healing 对 safe_mode 响应

### P5-8 失败路径会写 ledger（Critical）

---

# Phase 6 — 全量测试 + 故障注入 + SAFE MODE 真触发 + 最终报告

## 验收项

### P6-1 已执行路由测试（Critical）
至少覆盖：
- prompt-normalizer
- rule-router
- semantic-router
- workflow-resolver

### P6-2 已执行执行链测试（Critical）
至少覆盖：
- skill-router
- execution_guard
- task_ledger

### P6-3 已执行恢复与降级测试（Critical）
至少覆盖：
- self-healing
- rollback
- safe_mode

### P6-4 三大场景端到端测试已跑通（Critical）
1. 读取项目并评估功能，再给升级方案
2. 生成 Claude 施工单
3. docker compose up 报 permission denied

### P6-5 已进行 embedding 不可用故障注入（Critical）

### P6-6 SAFE MODE 已真实触发（Critical）
必须证明：
1. 系统不崩
2. semantic-router 被禁用或跳过
3. workflow-resolver 退化为 basic mode
4. self-healing 被禁用或收缩
5. ledger / logs / validation report 中记录 SAFE MODE 已进入

### P6-7 rollback 已通过安全验证（Critical）
必须证明：
1. rollback 真实读取 artifact_paths
2. 做了 repo-root 边界校验
3. 仓库内 artifact 被清理
4. 越界路径不会被删除，并有安全异常记录

### P6-8 已生成最终报告（Critical）
至少生成：
- architecture report
- validation report
- failure report（若有失败）

### P6-9 最终完成定义全部满足（Critical）
- workflow-resolver 正确输出 RoutePlan
- skill-router 只执行不决策
- execution_guard 可验证执行链
- task_ledger 状态正确
- rollback 路径安全有效
- self-healing 有上限
- SAFE MODE 真触发完成
- 三大场景全部正确

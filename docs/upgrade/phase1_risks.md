# Phase 1 Risk Inventory — 风险清单

> 审计日期：2026-06-21
> 风险等级定义：🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low

---

## R1: 假升级风险 🔴 Critical

### 描述
创建了文件/目录/文档但主链未接入，形式上"已完成"但系统行为无变化。

### 当前暴露面
- `execution_guard/` 下有 5 份完整规则文档，但 task-guard.py 和 completion-guard.py 均为 Phase 1 stub，不执行任何实际拦截
- `completion-guard.py` 的 `check_done_conditions()` 函数已编写但从未被调用（死代码）
- `skill_index.json` 中 `execution_guard.auto_trigger: true` 但无任何代码触发
- `orchestration/` 目录已在 `.claude/` 下存在但仅有 README 和空子目录，无实际编排代码
- `agents/` 目录仅有 README 占位

### 升级中的防范措施
- 每个 Phase 的验收项要求**代码实际接入主链**
- Phase 5 必须让 RoutePlan 驱动现有 skills 执行
- Phase 6 必须做端到端测试验证真实行为变化
- 禁止只写 TODO / placeholder（runbook §3.1）

---

## R2: 主链断裂风险 🔴 Critical

### 描述
升级过程中破坏了当前可工作的路由/执行链，导致系统不可用。

### 当前暴露面
- `routing_rules.py` → `skill-router.py` → Claude 执行的链路是**唯一**可工作的主链
- 若 Phase 3 拆分 routing_rules.py 时未保持向后兼容，路由将完全中断
- skill-router.py 是唯一的 UserPromptSubmit hook，若 Phase 5 替换它时出错，整个系统无 prompt 注入

### 升级中的防范措施
- Phase 1 禁止改 execution 主流程（runbook §Phase 1 本轮禁止）
- 每个阶段保留旧文件/旧行为不动
- 新增模块以 adapter / wrapper 模式接入，不直接替换
- Phase 3 rule-router 从 routing_rules.py **提取**而非重写
- 遵循 `03_safe_mode_and_rollback.md` 的回滚规范

---

## R3: SAFE MODE 未接通风险 🔴 Critical

### 描述
SAFE MODE 规范已写好但无代码实现，故障时系统无降级路径。

### 当前暴露面
- `03_safe_mode_and_rollback.md` 定义了完整的 SAFE MODE 进入条件、行为和验证要求
- 但当前仓库**零行代码**实现 SAFE MODE 进入/退出/降级
- semantic-router 尚不存在（Phase 4 才做），所以 embedding 不可用时的降级路径无法测试
- self-healing 不存在，无法在自愈失控时进入 SAFE MODE

### 升级中的防范措施
- Phase 5 必须实现 safe_mode 基础逻辑（P5-7 验收项）
- Phase 6 必须做 SAFE MODE 真触发验证（P6-6）
- safe_mode 状态必须写入 ledger/logs
- 任何 SAFE MODE 进入/退出都受 `03_safe_mode_and_rollback.md` §3 约束

---

## R4: rollback 越界删除风险 🔴 Critical

### 描述
rollback 时若 artifact_paths 未做 repo-root 边界校验，可能误删系统文件。

### 当前暴露面
- 当前仓库无 rollback 机制，所有删除操作依赖人工判断
- artifact_paths 存储格式尚未定义（Phase 2 才做）
- 若 artifact_paths 允许绝对路径或 `../` 遍历，回滚可能越界
- task-ops.py 无 artifact_paths 字段支持

### 升级中的防范措施
- Phase 2 P2-6 验收项：artifact_paths 必须使用 repo-root 相对路径，禁止 `../`，越界可被拒绝
- Phase 5 P5-5/P5-6 验收项：rollback 必须真实读取 ledger artifact_paths + 做 normalize → resolve → boundary check
- `03_safe_mode_and_rollback.md` §5-§6 定义了完整的路径安全规则
- 越界路径拒绝删除并记录 security error

---

## R5: self-healing 失控风险 🟠 High

### 描述
自愈逻辑无上限限制，同类型错误无限重试，消耗资源并放大故障。

### 当前暴露面
- self-healing 模块尚未创建
- 当前 routing_rules.py 的 fallback 逻辑是单次返回，无重试
- 但一旦 Phase 5 引入自愈，若无硬限制，可能在 embedding 故障时无限重试

### 升级中的防范措施
- Phase 5 P5-4 验收项：retry_count ≤ 3, same_failure_type_count ≤ 2, embedding_fail → immediate fallback
- 不可递归调用 self-healing
- 每次 retry 必须生成新的 route_id
- `03_safe_mode_and_rollback.md` §7 定义了完整的自愈约束
- 自愈失控时触发 SAFE MODE

---

## R6: 状态词汇分裂风险 🟠 High

### 描述
v1 和 v4 两套状态词汇并存，不同模块使用不同词汇集，导致状态校验失效。

### 当前暴露面
- `task-ops.py` 使用 v1 词汇：`queued, in_progress, blocked, done, retry`
- execution_guard 文档使用 v4 词汇：`queued, planning, executing, blocked, retrying, stalled, done, cancelled`
- `task-guard.py` 使用 v4 词汇检测停滞但仅检查 `planning/executing`
- `schema.md` 的转移表格混用两套词汇

### 升级中的防范措施
- Phase 2 升级 ledger_schema 时统一为 v4 词汇
- Phase 2 重写 task-ops.py 的 status 验证为 v4 词汇
- 所有新增代码只使用 v4 词汇
- 旧 task 数据的 migration 逻辑将 v1 词汇映射为 v4

---

## R7: embedding 依赖风险 🟡 Medium

### 描述
Phase 4 引入 semantic-router 后，若 embedding 服务不可用，系统必须降级而非崩溃。

### 当前暴露面
- embedding 服务尚未接入（nomic-embed-text 或其他）
- 当前系统不依赖 embedding，但 Phase 4 后会依赖
- 无 embedding health check 机制

### 升级中的防范措施
- Phase 4 P4-2：必须实现 embedding health check（可达性/模型可调用/超时/fail→degraded）
- Phase 4 P4-8：semantic-router 失败时系统不能崩溃
- semantic-router 只能给候选，不能做最终决策（resolver 做融合）
- SAFE MODE 下 semantic-router 被禁用或跳过

---

## R8: 跨 Phase 依赖链断裂风险 🟡 Medium

### 描述
Phase 2-5 各自构建上游依赖，若某个 Phase 交付物质量不足，下游 Phase 无法正常工作。

### 当前暴露面
- Phase 2 (schema) → Phase 3 (normalizer) → Phase 4 (resolver) → Phase 5 (execution) 是严格的依赖链
- 若 Phase 2 的 RoutePlan schema 字段不完整，Phase 4 的 resolver 无法输出完整的 RoutePlan
- 若 Phase 3 的 routing_assets 覆盖不足，Phase 4 的 semantic-router 候选质量差

### 升级中的防范措施
- 每个 Phase 的验收检查（01_phase_acceptance.md）确保交付物质量
- Gate = GO 才进入下一阶段
- 不允许"边补边进下一轮"（runbook §6.3）
- 每个阶段的报告必须列出"Next Phase Prerequisites"

---

## R9: 旧 skill 兼容性破坏风险 🟡 Medium

### 描述
升级过程中若删除或破坏现有 skill 目录/文件，现有功能不可用。

### 当前暴露面
- 4 个 legacy shim 目录 (planner/summarize/debug/task_manager) 与新版并存
- skill-rules.json 中同时注册了新旧名称
- 若 Phase 2-5 修改了 skill 调用方式而未兼容旧路径，旧名称将无法工作

### 升级中的防范措施
- runbook §3.2 禁止直接删除现有 skills
- 不删除旧 router/guard/ledger
- 旧 skill 保留 MIGRATION.md + adapter/wrapper
- CLAUDE.md 明确 legacy 兼容策略

---

## R10: 单代理架构限制风险 🟢 Low

### 描述
整个系统设计为 Claude Code 单代理执行，无真实多代理机制。Phase 4 orchestration/agents 仍为占位。

### 当前暴露面
- orchestrator / agent_definitions 仅有 README 占位
- 无多代理调度器
- CLAUDE.md 明确声明"不要在当前任务中启动多代理 workflow"

### 升级中的防范措施
- Phase 6 orchestration/agents 保持 Phase 4 占位状态
- 本次升级不改变单代理架构
- 仅预留扩展接口

---

## 风险矩阵汇总

| 风险 ID | 风险名称 | 等级 | 影响 Phase | 缓解状态 |
|---------|---------|------|-----------|---------|
| R1 | 假升级 | 🔴 Critical | 全部 | 验收项 + 端到端测试 |
| R2 | 主链断裂 | 🔴 Critical | 3, 4, 5 | 向后兼容 + adapter 模式 |
| R3 | SAFE MODE 未接通 | 🔴 Critical | 5, 6 | P5-7 + P6-6 验收 |
| R4 | rollback 越界删除 | 🔴 Critical | 2, 5, 6 | P2-6 + P5-5/6 + §5-6 规则 |
| R5 | self-healing 失控 | 🟠 High | 5, 6 | P5-4 + §7 硬上限 |
| R6 | 状态词汇分裂 | 🟠 High | 2, 5 | Phase 2 统一 |
| R7 | embedding 依赖 | 🟡 Medium | 4, 5, 6 | P4-2 + P4-8 + SAFE MODE |
| R8 | 跨 Phase 依赖链 | 🟡 Medium | 2-5 | Gate 机制 |
| R9 | 旧 skill 兼容 | 🟡 Medium | 2-5 | 不删除旧目录 + adapter |
| R10 | 单代理限制 | 🟢 Low | 全部 | 保持现状 |

# 00 Master Runbook — Production-Safe Workflow OS Upgrade

> 适用对象：Claude Code / Claude CLI  
> 目标仓库：`skill-os-complete`  
> 目标：把现有 skill system 升级为 **Production-Safe Workflow OS**，并且实现：
>
> - 分阶段施工
> - 每阶段完成后自动检查
> - 验收通过才进入下一阶段
> - 失败自动停机（NO-GO）
> - 支持 SAFE MODE / rollback / self-healing / ledger / execution guard

---

# 1. 使用方式（Claude 必须遵守）

Claude 在开始执行前，必须先读取以下四个文件：

- `docs/upgrade/00_master_runbook.md`
- `docs/upgrade/01_phase_acceptance.md`
- `docs/upgrade/02_phase_report_template.md`
- `docs/upgrade/03_safe_mode_and_rollback.md`

然后必须先输出以下固定声明：

> 本轮结束后必须严格按 `docs/upgrade/02_phase_report_template.md` 输出阶段报告；缺少任一字段，视为本轮未完成，不允许进入下一轮。

---

# 2. 总执行规则（硬约束）

## 2.1 只允许按 Phase 顺序推进

必须按以下顺序执行，禁止跳阶段：

1. Phase 1 — 仓库审计 + 改造映射 + 骨架建立
2. Phase 2 — 协议层 + Schema + Ledger 升级
3. Phase 3 — prompt-normalizer + rule-router + routing assets
4. Phase 4 — semantic-router + workflow-resolver
5. Phase 5 — skill-router + execution_guard + rollback + self-healing + safe_mode
6. Phase 6 — 全量测试 + 故障注入 + SAFE MODE 真触发 + 最终报告

---

## 2.2 每个 Phase 必须严格执行以下流程

每个 Phase 都必须按下面的固定顺序执行：

### Step A — 声明当前阶段
Claude 必须先明确：

- 当前是哪个 Phase
- 本轮目标是什么
- 本轮允许修改哪些内容
- 本轮禁止提前做哪些内容

### Step B — 执行当前阶段施工
- 只实现当前阶段要求
- 不允许提前大规模实现后续 Phase 功能
- 尽量保持最小可运行
- 不允许破坏已有兼容性

### Step C — 自动检查当前阶段
施工完成后，Claude **不能直接宣布完成**，必须读取：

- `docs/upgrade/01_phase_acceptance.md`

然后对当前 Phase 的每一条验收项逐项检查，并输出：

- PASS
- FAIL
- PARTIAL

不允许跳过验收项。

### Step D — 输出阶段报告
必须严格按：

- `docs/upgrade/02_phase_report_template.md`

输出完整报告。

### Step E — 做 Gate 决策
- 如果当前阶段所有**关键验收项**都满足 → `GO`
- 如果任一关键验收项不满足 → `NO-GO`

若 `NO-GO`：
- 必须停止
- 输出阻塞问题
- 给出修复建议
- 不允许进入下一阶段

若 `GO`：
- 说明下一阶段依赖哪些产物
- 再进入下一阶段

---

# 3. 绝对禁止的行为

以下任一情况都视为阶段失败：

## 3.1 假升级
- 创建了文件，但主链未接入
- semantic-router 文件存在，但 resolver 不读取
- SAFE MODE 代码存在，但没有真实接入状态流
- rollback 存在，但不读取 ledger 的 artifact_paths
- self-healing 存在，但没有硬上限
- 只改文档不改代码
- 只写 TODO / placeholder

## 3.2 粗暴破坏现有系统
- 直接删除现有 skills
- 直接重写整套系统而不兼容现有仓库
- 删除旧 router / guard / ledger 而不做迁移
- 把旧 skill 全部作废但没有 adapter / wrapper

## 3.3 跳阶段施工
例如：
- Phase 2 直接做 semantic-router
- Phase 3 直接做 rollback
- Phase 4 直接做 skill-router 执行链

---

# 4. 目录约束（建议落点）

若仓库中不存在，可逐步创建以下目录：

```text
docs/upgrade/
docs/architecture/
docs/validation/
docs/failure/

orchestration/
ledger/
routing_assets/
tests/
```

---

# 5. 六个阶段的目标与施工范围

---

# Phase 1 — 仓库审计 + 改造映射 + 升级骨架

## 目标
看清楚仓库当前结构，建立后续施工边界。

## 必须完成
1. 读取整个仓库结构
2. 识别现有：
   - skills
   - router / orchestration 逻辑
   - execution_guard
   - task_ledger / state / task files
   - docs / tests / configs
3. 输出：
   - 仓库审计文档
   - 升级映射表
   - 风险清单
4. 创建升级文档骨架
5. 不允许大规模业务重构

## 本轮允许修改
- 新建 `docs/upgrade/*`
- 新建 `docs/architecture/`、`docs/validation/`、`docs/failure/`
- 轻量级补充 README / 注释 / TODO 索引
- 建立 `orchestration/` / `ledger/` / `routing_assets/` / `tests/` 骨架目录（如缺失）

## 本轮禁止
- 改 execution 主流程
- 切换主入口
- 重写 skill
- 删除旧 router

---

# Phase 2 — 协议层 + Schema + Ledger 升级

## 目标
固定系统“怎么描述工作流”和“怎么记账”。

## 必须完成
1. 落地 RoutePlan / RouteStage / GuardPolicy
2. 落地 workflow_state
3. 落地 orchestration_types
4. 升级 ledger_schema
5. 升级 task_ledger，支持：
   - route / workflow / intent
   - stage / execution 状态
   - expected_artifacts / artifact_paths
   - retry / failure / safe_mode
6. 将 artifact_paths 安全规则纳入 schema 与实现

## 推荐文件
- `orchestration/route_plan.*`
- `orchestration/workflow_state.*`
- `orchestration/orchestration_types.*`
- `ledger/ledger_schema.*`
- `ledger/task_ledger.*`

## 本轮禁止
- 不要做 semantic-router
- 不要做 skill-router 执行链
- 不要做 SAFE MODE 故障注入

---

# Phase 3 — prompt-normalizer + rule-router + routing assets

## 目标
先把**不依赖 embedding 的基础路由链**跑起来。

## 必须完成
1. prompt-normalizer
2. rule-router
3. routing_assets：
   - `route_examples.json`
   - `workflow_cards.json`
   - `skill_cards.json`
4. 让以下场景通过 rule path 跑通：
   - 读取项目并评估功能，再给升级方案 → delivery_pipeline
   - 生成 Claude 施工单 → delivery_pipeline
   - docker compose up 报 permission denied → debug_pipeline
   - learning 类请求 → learning_pipeline

## prompt-normalizer 必须识别
- `/plan /debug /task /next`
- `repo_analysis / planning / debug / learning / construction_prompt`
- multi-intent

## 本轮禁止
- 不要依赖 embedding 作为主链
- 不要做 workflow-resolver 最终决策融合
- 不要做执行链

---

# Phase 4 — semantic-router + workflow-resolver

## 目标
引入 embedding 语义候选层，并由 resolver 输出唯一 RoutePlan。

## 必须完成
1. semantic-router
2. embedding health check
3. semantic-router 能读取 routing_assets
4. workflow-resolver
5. resolver 融合：
   - normalized input
   - rule candidates
   - semantic candidates
   - safe_mode state
6. 输出唯一合法 RoutePlan

## semantic-router 强制要求
- 优先支持 `nomic-embed-text:latest`
- embedding 不可用时不能崩溃
- 必须返回 degraded / fallback 状态
- 只能给候选，不能做最终决策

## 本轮禁止
- 不要求做 SAFE MODE 真触发
- 不要求完成执行链

---

# Phase 5 — skill-router + execution_guard + rollback + self-healing + safe_mode

## 目标
把路由结果真正执行起来，并打通失败恢复链。

## 必须完成
1. skill-router
2. execution_guard
3. rollback_manager
4. self_healing
5. safe_mode 基础实现
6. 让 RoutePlan 驱动现有 skills 执行
7. 让失败链路写入 ledger

## skill-router 要求
- 只执行 RoutePlan，不允许重新路由
- 按 stage 顺序执行
- stage running/success/failed 写 ledger
- artifact_paths 写 ledger

## execution_guard 要求
检查：
- required stages 是否完整
- stage 顺序是否正确
- expected_artifacts 是否存在
- ledger 是否更新
- 是否存在 no-op completion
- delivery_pipeline 是否跳 summarize/planning
- construction prompt 是否缺 ask
- debug_pipeline 是否缺 diagnose

## self-healing 要求
- retry_count ≤ 3
- same_failure_type_count ≤ 2
- embedding_fail → immediate fallback
- 不允许递归自愈
- 每次 retry 必须生成新 route_id

## rollback 要求
- 从 ledger 读取 artifact_paths
- 做 repo-root 路径边界校验
- 安全删除 artifact
- 清理 route cache
- 写 rollback 结果

---

# Phase 6 — 全量测试 + 故障注入 + SAFE MODE 真触发 + 最终报告

## 目标
完成端到端验证，不再以写新功能为主。

## 必须完成
1. 路由测试
2. 执行测试
3. 恢复与降级测试
4. 三大场景端到端测试
5. embedding 不可用故障注入
6. SAFE MODE 真触发验证
7. rollback 安全验证
8. architecture / validation / failure report

## SAFE MODE 真触发必须证明
1. 系统没有崩溃
2. semantic-router 被禁用或跳过
3. workflow-resolver 退化为 basic mode
4. self-healing 被禁用或收缩
5. ledger / logs / validation report 中明确记录 SAFE MODE 已进入

---

# 6. 自动推进机制（关键）

Claude 必须实现以下推进规则：

## 6.1 一个阶段结束时，必须先跑自动检查
Claude 必须根据 `01_phase_acceptance.md` 当前阶段清单，逐项给出：
- PASS
- FAIL
- PARTIAL

## 6.2 只有在关键项全部 PASS 时，Gate 才能是 GO
如果任一关键项失败，必须：
- 输出 `Gate Result: NO-GO`
- 停止
- 列出 blocking issues
- 列出 must-fix items

## 6.3 Gate = GO 后，才允许进入下一阶段
不得“边补边进下一轮”。

---

# 7. 最终完成定义

只有以下全部满足，才允许宣告升级完成：

- semantic routing 正常
- workflow-resolver 输出正确 RoutePlan
- skill-router 只执行不决策
- execution_guard 可验证执行链
- task_ledger 状态正确
- rollback 能按 repo-root 安全清理 artifact
- self-healing 有上限
- SAFE MODE 已真实触发验证
- 三大核心场景全部正确跑通

---

# 8. Claude 每轮必须输出的固定结尾

每轮结束必须输出：

## Gate Check
- Gate Result: GO / NO-GO
- Reason:
- Blocking Issues:
- Must Fix Before Next Phase:
- Next Phase Prerequisites:
- Remaining Risks:

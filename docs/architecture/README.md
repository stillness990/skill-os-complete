# Architecture Report — Skill OS v4 Workflow OS

> 最终架构报告 — Phase 6 完成
> 日期: 2026-06-21

---

## 六层架构 (Final)

```
Layer 1: Router（路由层）        — 输入→intent→workflow→RoutePlan
Layer 2: Core Skills（核心基座）  — summarize / planning / debug
Layer 3: Workflow（工作流控制）   — delivery / debug / learning pipeline
Layer 4: System（系统状态）       — task_ledger / learning_state / knowledge
Layer 5: Execution Guard（监督层）— execution_guard / safe_mode / rollback / self_healing
Layer 6: Extension（扩展层）      — orchestration / agents
```

## 数据流

```
User Input
  → PromptNormalizer (标准化 + intent 识别)
  → RuleRouter (关键词规则路由)
  → SemanticRouter (embedding 语义候选, 可选/可降级)
  → WorkflowResolver (融合决策 → 唯一 RoutePlan)
  → SkillRouter (按 RoutePlan 逐 stage 执行)
  → ExecutionGuard (每个 stage 后检查)
  → TaskLedger (写入任务状态 + artifact_paths)
  → [Stage 成功] → 下一 stage
  → [Stage 失败] → SelfHealing (retry/fallback/safe_mode/stop)
  → [Workflow 完成] → ExecutionGuard 最终检查
```

## 模块清单

### orchestration/ (编排层)

| 文件 | 行数 | 职责 |
|------|------|------|
| orchestration_types.py | 215 | 统一枚举类型 (Intent, Workflow, TaskStatus, StageStatus, etc.) |
| route_plan.py | 422 | RoutePlan/RouteStage/GuardPolicy 数据结构 |
| workflow_state.py | 252 | WorkflowState 状态追踪 (RetryState, safe_mode) |
| workflow_resolver.py | 315 | 多源融合决策器 (rule + semantic + safe_mode → RoutePlan) |
| skill_router.py | 388 | RoutePlan 执行器 (逐 stage, guard, ledger) |
| execution_guard.py | 305 | 执行监督 (6 checks, 3 verdicts, pipeline-specific) |
| safe_mode.py | 152 | 安全模式管理器 (trigger, record, degraded actions) |
| rollback_manager.py | 294 | 回滚管理 (5-step, path safety, real delete) |
| self_healing.py | 210 | 自愈管理 (retry≤3, same_failure≤2, anti-recursion) |

### routing_assets/ (路由资产)

| 文件 | 行数 | 职责 |
|------|------|------|
| prompt_normalizer.py | 259 | 输入标准化 (slash commands, intent detection, multi-intent) |
| rule_router.py | 307 | 规则路由 (keyword-weighted, slash→skill mapping) |
| semantic_router.py | 346 | 语义路由 (embedding health, candidate search, degraded mode) |
| route_examples.json | — | 20 条标注路由示例 |
| workflow_cards.json | — | 3 workflow 定义 |
| skill_cards.json | — | 10 skill 定义 |

### ledger/ (账本模块)

| 文件 | 行数 | 职责 |
|------|------|------|
| ledger_schema.py | 388 | Python schema (LedgerTask, ArtifactRefs, artifact_paths 安全) |
| task_ledger.py | 459 | 任务 CRUD + 状态转移 + safe_mode/retry 支持 |
| ledger_api.py | 146 | 公开查询接口 |

## Pipeline 定义

### delivery_pipeline: summarize → planning → task_ledger → code_assistant → reviewer → changelog
### debug_pipeline: summarize(optional) → debug(diagnose) → code_assistant → debug_log
### learning_pipeline: ask(optional) → summarize → planning → teach-plus(explain) → teach-plus(practice) → task_ledger → teach-plus(review)

## 安全边界

- artifact_paths: repo-root 相对路径, 禁止 ../, 禁止绝对路径, normalize→resolve→boundary check
- safe_mode: 7 triggers, semantic/router/healing 联动降级
- self_healing: retry≤3, same_failure≤2, embedding→immediate fallback, anti-recursion
- rollback: 5-step process, path safety enforced, malicious paths rejected with security errors
- execution_guard: 6 checks + 3 pipeline-specific rules + no-op detection

## 测试覆盖

- 73 tests, 100% pass rate
- 3 scenarios end-to-end verified
- Embedding fault injection: system gracefully degrades
- SAFE MODE: 5 proofs
- Rollback security: 4 proofs

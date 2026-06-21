# Phase 5 Report — skill-router + execution_guard + rollback + self-healing + safe_mode

> 日期：2026-06-21
> 状态：Completed

## 1. Current Phase
- Phase Name: Phase 5 — skill-router + execution_guard + rollback + self-healing + safe_mode
- Goal: 把路由结果真正执行起来，并打通失败恢复链
- Status: Completed

## 2. Files Modified
- orchestration/execution_guard.py (原 `.claude/hooks/completion-guard.py` 保留，此为 Python 模块版)
- orchestration/skill_router.py (原 `.claude/hooks/skill-router.py` 保留，此为 Python 模块版)

## 3. Files Added
- orchestration/safe_mode.py (152 lines) — 安全模式管理器
- orchestration/execution_guard.py (305 lines) — 执行监督层
- orchestration/rollback_manager.py (294 lines) — 回滚管理器
- orchestration/self_healing.py (210 lines) — 自愈管理器
- orchestration/skill_router.py (388 lines) — 技能路由执行器
- tests/test_phase5_modules.py (889 lines, 38 tests)

## 4. What Was Completed

### 4.1 safe_mode.py
- SafeModeManager 全局单例
- 7 种触发原因 (embedding_unavailable, semantic_router_init_failed, rollback_path_out_of_bounds, rollback_security_error, self_healing_limit_exceeded, execution_guard_critical, manual_trigger)
- 状态机: INACTIVE → TRIGGERED → ACTIVE → INACTIVE (release)
- SafeModeRecord 记录触发时间/原因/route_id/workflow/stage_id/degraded_actions
- 模块查询接口: should_disable_semantic(), should_shrink_healing(), is_rollback_conservative()
- Ledger 写入回调注入
- to_dict() 序列化

### 4.2 execution_guard.py
- 6 项检查: required_stages, stage_order, expected_artifacts, ledger_update, noop_completion, pipeline_specific
- Guard 三级判定: PASS / WARN / BLOCK
- Pipeline 专项检查: delivery 需要 summarize+planning, debug 需要 diagnose, learning 需要 summarize+plan
- No-op completion 检测: 所有 stage pending 但 workflow 标记完成 → BLOCK
- Artifact 存在性检查 + 路径安全验证
- GuardResult 结构化输出 + to_dict() 序列化

### 4.3 rollback_manager.py
- 5 步执行流程 (读取 → 校验 → 删除 → 清理 → 写回)
- 路径安全校验: normalize → resolve → boundary check
- 禁止 ../, 禁止绝对路径, 禁止越出 repo-root
- 越界路径拒绝删除并记录 security_error
- dry_run 模式 (安全预览)
- 真实文件/目录删除 (含 shutil.rmtree)
- RollbackResult 结构化输出 + to_dict() 序列化

### 4.4 self_healing.py
- HealingConfig: max_retry_count=3, max_same_failure_type_count=2
- 决策优先级: retry → fallback → safe_mode → stop
- 不可重试类型: EMBEDDING_UNAVAILABLE, ROLLBACK_SECURITY, ILLEGAL_TRANSITION
- 可重试类型: STAGE_TIMEOUT, ARTIFACT_MISSING, GUARD_REJECTED
- 防递归: _healing_in_progress 标志位
- 每次 retry 生成新 route_id (uuid4)
- classify_failure() 从错误消息自动分类 FailureType
- can_retry() 快速检查接口

### 4.5 skill_router.py
- RoutePlan 驱动执行: 逐 stage 按顺序执行
- 不重新做路由决策 (execute 方法不引用 WorkflowResolver)
- Stage 状态流转: PENDING → RUNNING → SUCCESS/FAILED/SKIPPED
- SafeMode 下跳过 optional stages
- 每个 stage 完成后: execution_guard 检查 → ledger 写入
- 失败后: self_healing 决策 → retry/fallback/safe_mode/stop
- continue_from 中断恢复支持
- 执行上下文传递 (route_id, workflow, stage_phase, safe_mode 等)
- Skill 执行回调和 Ledger 写入回调可注入
- RouterExecutionResult 结构化输出 + to_dict() 序列化

## 5. What Was Preserved / Kept Compatible
- 原有 `.claude/hooks/skill-router.py` 保留不变 (hook 层)
- 原有 `.claude/hooks/task-guard.py` 保留不变
- 原有 `.claude/hooks/completion-guard.py` 保留不变
- orchestration/ 下所有新模块是 Python 库，由 hook 层或外部调用使用
- 与 Phase 2 orchestration_types 完全兼容 (共享枚举)
- 与 Phase 2 route_plan/workflow_state 完全兼容
- 与 Phase 4 workflow_resolver 完全兼容 (RoutePlan 是桥梁)

## 6. Acceptance Check Results

- P5-1 (Critical): skill-router 已按 RoutePlan 执行 → **PASS**
  - 按 stage 顺序执行 (test: execution_order = ['understand', 'plan', 'track'])
  - 不重新做路由决策 (test: SkillRouter.execute 不引用 WorkflowResolver)
  - Stage 状态写入 ledger (test: 3 stages → 3 ledger writes)
  - 收集 artifact_paths (test: all_artifacts = ['output/understand.md', ...])

- P5-2 (Critical): execution_guard 已实现 → **PASS**
  - Required stages 检查完整 (guard blocks missing diagnose/summarize/planning)
  - Stage 顺序检查 (stage_order_violation when wrong order)
  - Expected artifacts 检查 (blocks on nonexistent artifacts, passes on real ones)
  - Ledger 更新检查 (warns on ledger_state=None, checks status field)
  - No-op completion 检测 (blocks when all pending but workflow completes)

- P5-3 (Critical): pipeline 专项校验已接入 → **PASS**
  - delivery 缺少 summarize → BLOCK ("delivery_pipeline 缺少 summarize")
  - delivery 缺少 planning → BLOCK ("delivery_pipeline 缺少 planning")
  - debug 缺少 diagnose → BLOCK ("debug_pipeline 缺少 diagnose")
  - learning 缺少 summarize/plan → BLOCK

- P5-4 (Critical): self-healing 已实现并有限制 → **PASS**
  - retry_count ≤ 3 (test: retry_count=3 → safe_mode)
  - same_failure_type_count ≤ 2 (test: count=2 → safe_mode)
  - embedding_fail → immediate fallback (test: EMBEDDING_UNAVAILABLE → fallback)
  - 不可递归调用 (test: _healing_in_progress=True → stop)
  - 每次 retry 新 route_id (test: 3 unique route_ids)

- P5-5 (Critical): rollback 已真实读取 ledger 的 artifact_paths → **PASS**
  - rollback_route() 从 ledger dict 读取 artifact_paths
  - execute() 从 artifact_paths list 读取
  - Result 包含 cleaned/rejected 计数

- P5-6 (Critical): rollback 已实现 repo-root 路径安全清理 → **PASS**
  - normalize → resolve → boundary check 流程完整
  - ../ 路径拒绝 (test: rejected with "路径包含 '..'")
  - 绝对路径拒绝 (test: rejected with "不允许绝对路径")
  - 真实文件删除验证 (test: file deleted, not exists on disk)
  - dry_run 模式不实际删除

- P5-7 (Critical): safe_mode 基础逻辑已接入 → **PASS**
  - 状态存储: SafeModeManager (INACTIVE/TRIGGERED/ACTIVE)
  - 触发入口: trigger() + confirm()
  - resolver 响应: should_disable_semantic() → True in safe_mode
  - router 响应: optional stages 在 safe_mode 下跳过
  - healing 响应: should_shrink_healing() → True in safe_mode

- P5-8 (Critical): 失败路径会写 ledger → **PASS**
  - skill_router 每个 stage 完成后写 ledger (成功或失败都写)
  - 失败时 healing 决策记录
  - 失败类型分类写入 workflow_state

## 7. Test Results
- tests executed: 38 (5 safe_mode + 8 execution_guard + 7 rollback + 9 self_healing + 8 skill_router + 1 integration)
- tests passed: 38/38 (100%)
- tests failed: 0
- failure reason: N/A
- fixtures / mocks used: Mock executor and ledger writer; real filesystem for rollback tests; tempfile for file creation/deletion

## 8. Risks / Known Issues
- 5 个模块通过 sys.path 操作导入 (orchestration/ 未配备 __init__.py) — 与 Phase 2-4 一致
- SkillRouter 的 skill 执行回调和 ledger 写入回调默认是 no-op — 实际集成需要 hook 层注入
- ExecutionGuard 的 ledger 检查依赖外部传入 ledger_state dict — hook 层负责组装
- RollbackManager 的 cache 清理 (Step 4) 目前是占位 — 需 Phase 6 确定 cache 存储方式后完整实现
- 各模块的 safe_mode_manager 通过全局单例通信 — 测试时需显式 reset

## 9. Output Artifacts
- docs generated: reports/phase5_report.md (this file)
- schemas generated: none (使用 Phase 2 的 orchestration_types)
- route assets: none (Phase 5 是执行层)
- test fixtures: tests/test_phase5_modules.py (38 tests)
- validation outputs: all 38 tests PASS

## 10. Gate Check
- Gate Result: **GO**
- Reason: All 8 critical acceptance items PASS. 38/38 tests passing. Skill router executes RoutePlan correctly, execution guard blocks invalid workflows, rollback enforces path safety, self-healing respects all limits, safe_mode controls all dependent modules.
- Blocking Issues: none
- Must Fix Before Next Phase: none
- If GO, prerequisites for next phase:
  - All Phase 2-5 modules available
  - All test suites passing across Phases 3-5
  - routing_assets JSON files ready for embedding test
  - .claude/hooks/ layer ready for skill-router integration
- Remaining Risks: Real embedding server not tested (Phase 6); hook-layer integration pending (Phase 6); SAFE MODE on real failure not yet triggered (Phase 6 fault injection)

## 11. Next Phase Plan
- next target: Phase 6 — 全量测试 + 故障注入 + SAFE MODE 真触发 + 最终报告
- files expected to change:
  - tests/ (Phase 6 integration tests, fault injection tests)
  - docs/architecture/ (final architecture report)
  - docs/validation/ (final validation report)
  - docs/failure/ (failure reports if any)
- expected validation focus:
  - Routing tests (normalizer + rule + semantic + resolver) — 已有，需全量运行
  - Execution tests (skill_router + guard + ledger) — 已有，需全量运行
  - Recovery tests (healing + rollback + safe_mode) — 已有，需全量运行
  - 3 大场景端到端测试
  - Embedding 不可用故障注入
  - SAFE MODE 真触发验证 (崩溃保护, semantic 禁用, resolver 退化, healing 收缩, ledger 记录)
  - Rollback 安全验证 (真实 artifact_paths, boundary check, 越界拒绝)
  - Final reports (architecture + validation + failure)

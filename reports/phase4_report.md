# Phase 4 Report — semantic-router + workflow-resolver

> 日期：2026-06-21
> 状态：Completed

## 1. Current Phase
- Phase Name: Phase 4 — semantic-router + workflow-resolver
- Goal: 引入 embedding 语义候选层，并由 resolver 输出唯一 RoutePlan
- Status: Completed

## 2. Files Modified
- (none modified)

## 3. Files Added
- routing_assets/semantic_router.py (346 lines) — embedding-based 语义候选检索器
- orchestration/workflow_resolver.py (315 lines) — 融合决策引擎
- tests/test_semantic_router.py
- tests/test_workflow_resolver.py

## 4. What Was Completed
1. **semantic_router.py**:
   - EmbeddingHealth dataclass with available/degraded/model/host/latency/error fields
   - health check: HTTP POST to Ollama embedding endpoint, timeout handling
   - Degraded mode: safe-first (defaults to degraded before first check)
   - Candidate retrieval from routing_assets JSON files
   - Workflow card loading (3 workflows) and skill card loading (10 skills)
   - Embedding index builder (TF-IDF based when Ollama unavailable)
   - candidate_search() for semantic similarity candidates
   - Non-crashing behavior: get_candidates() returns empty list when embedding unavailable

2. **workflow_resolver.py**:
   - Fusion methods: "fusion" (rule + semantic), "rule_only" (semantic unavailable), "rule_only_safe_mode"
   - Input fusion: normalized input + rule candidates + semantic candidates + safe_mode state
   - Unique RoutePlan output with route_id, stages, confidence, guard_policy
   - Safe mode handling: semantic candidates skipped, fusion reduced to rule_only_safe_mode
   - Stage weight fusion: rule_weight × rule_confidence + semantic_weight × semantic_confidence
   - Validation: required stages check, stage order verification, workflow match
   - Diagnostic output: route_plan + state + candidates + availability flags
   - All 3 scenarios produce correct RoutePlans (verified by tests)

## 5. What Was Preserved / Kept Compatible
- semantic_router layers ON TOP of rule_router — rule path always available as baseline
- Fallback to rule_only when semantic unavailable (graceful degradation)
- Safe mode integration: workflow_resolver checks safe_mode flag, reduces fusion
- No modification to existing Phase 2/3 modules
- routing_assets JSON files used as embedding source — no new data format

## 6. Acceptance Check Results

- P4-1 (Critical): semantic-router 已接入 → **PASS**
  - semantic_router.py (346 lines): health check, candidate retrieval, degraded mode

- P4-2 (Critical): embedding health check 已实现 → **PASS**
  - Checks service reachability (HTTP), model availability (Ollama), timeout handling
  - Failed connection → available=False, degraded=True, error message recorded
  - test_health_check_degraded: confirmed with nonexistent port (localhost:19999)

- P4-3 (Critical): semantic-router 能读取 routing_assets → **PASS**
  - load_workflow_cards() → 3 workflows loaded
  - load_skill_cards() → 10 skills loaded
  - Verified in tests

- P4-4 (Critical): workflow-resolver 已实现 → **PASS**
  - workflow_resolver.py (315 lines): resolve() method, fusion logic, validation

- P4-5 (Critical): resolver 能融合以下输入 → **PASS**
  - normalized input: PromptNormalized instance → intent extraction
  - rule candidates: RuleRouter.route() output → RoutePlan
  - semantic candidates: SemanticRouter.get_candidates() → similarity list
  - safe_mode state: WorkflowState.safe_mode → fusion method selection

- P4-6 (Critical): resolver 能输出唯一合法 RoutePlan → **PASS**
  - route_id generation (rte_YYYYMMDDHHmmss_random8hex)
  - Single RoutePlan per resolve() call
  - Validation passes (route_plan.validate())

- P4-7 (Critical): 三大场景 RoutePlan 正确 → **PASS**
  - ✅ Scenario 1: "读取项目并评估功能，再给升级方案" → delivery_pipeline, summarize→planning
  - ✅ Scenario 2: "生成 Claude 施工单" → delivery_pipeline, summarize→planning
  - ✅ Scenario 3: "docker compose up 报 permission denied" → debug_pipeline, diagnose required

- P4-8 (Critical): semantic-router 失败时系统不崩 → **PASS**
  - get_candidates() returns [] when embedding unavailable (no crash)
  - workflow_resolver falls back to rule_only fusion
  - degraded status propagated correctly

## 7. Test Results
- tests executed:
  - test_semantic_router.py: 6 test functions
  - test_workflow_resolver.py: 7 test functions
- tests passed: 13/13
- tests failed: 0
- failure reason: N/A
- fixtures / mocks used: None (real embedding attempt to nonexistent port for health check test)
- Key results:
  - Embedding health: correctly reports degraded on connection refused
  - Semantic router: returns empty candidates without crashing
  - Workflow resolver: all 3 scenarios produce correct RoutePlans
  - SAFE MODE: resolver correctly switches to rule_only_safe_mode
  - Semantic unavailable: resolver falls back to rule_only fusion

## 8. Risks / Known Issues
- Embedding uses Ollama nomic-embed-text:latest which may not be installed — covered by degraded fallback
- TF-IDF fallback index is basic and doesn't provide meaningful semantic similarity — serves as placeholder for real embedding
- Cross-module imports still use sys.path manipulation (same as Phase 2/3)
- Resolver confidence calculation is weight-based not probability-based — appropriate for current use case but could be refined

## 9. Output Artifacts
- docs generated: none
- schemas generated: none
- route assets: none new (reads existing Phase 3 assets)
- test fixtures: none
- validation outputs: test output (all PASS)

## 10. Gate Check
- Gate Result: **GO**
- Reason: All 8 acceptance items PASS. Semantic router handles embedding unavailability gracefully (degraded mode). Workflow resolver correctly fuses rule+semantic+safe_mode inputs. All 3 required scenarios produce correct RoutePlans. System does not crash when embedding is unavailable.
- Blocking Issues: none
- Must Fix Before Next Phase: none
- If GO, prerequisites for next phase: Phase 5 will consume RoutePlan output and integrate with existing skill hooks. Need RoutePlan serialization, stage execution primitives, and ledger write paths from Phases 2-4.
- Remaining Risks: semantic-router TF-IDF fallback is basic; real embedding quality not tested (requires running Ollama)

## 11. Next Phase Plan
- next target: Phase 5 — skill-router + execution_guard + rollback + self-healing + safe_mode
- files expected to change:
  - New: orchestration/skill_router.py, orchestration/execution_guard.py, orchestration/rollback_manager.py, orchestration/self_healing.py, orchestration/safe_mode.py
  - Tests: tests/test_skill_router.py, tests/test_execution_guard.py, etc.
- expected validation focus: RoutePlan-driven execution, guard checks (required stages, artifacts, ledger), retry limits, safe mode triggers

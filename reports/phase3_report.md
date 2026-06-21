# Phase 3 Report — prompt-normalizer + rule-router + routing assets

> 日期：2026-06-21
> 状态：Completed

## 1. Current Phase
- Phase Name: Phase 3 — prompt-normalizer + rule-router + routing assets
- Goal: 先把不依赖 embedding 的基础路由链跑起来
- Status: Completed

## 2. Files Modified
- (none modified)

## 3. Files Added
- routing_assets/prompt_normalizer.py (259 lines) — 输入标准化器
- routing_assets/rule_router.py (307 lines) — 规则路由引擎
- routing_assets/route_examples.json — 20 条标注路由示例
- routing_assets/workflow_cards.json — 3 条 workflow 卡片
- routing_assets/skill_cards.json — 10 条 skill 卡片
- tests/test_prompt_normalizer.py (131 lines)
- tests/test_rule_router.py (219 lines)

## 4. What Was Completed
1. **prompt_normalizer.py**:
   - Slash command detection (/plan, /debug, /task, /next)
   - Intent type detection (repo_analysis, planning, debug, learning, construction_prompt)
   - Multi-intent detection with primary/secondary split
   - Unknown intent fallback with zero confidence
   - Singleton access pattern (get_normalizer())

2. **rule_router.py**:
   - Rule-based RoutePlan generation from normalized input
   - Slash command → skill mapping (/plan → planning, /debug → debug, /task|/next → task_ledger)
   - Intent → Workflow mapping via orchestration_types.workflow_for_intent()
   - Confidence scoring based on matched keyword weight
   - RoutePlan generation with correct stage sequences per workflow
   - Keyword tables for each intent type and skill name

3. **routing_assets**:
   - route_examples.json: 20 examples covering all 3 workflows + unknown
   - workflow_cards.json: delivery/debug/learning workflow definitions
   - skill_cards.json: 10 skill definitions with keywords

4. **Test results**: All tests pass (see Section 7)

## 5. What Was Preserved / Kept Compatible
- No existing files modified — pure additive
- Rule router reads from orchestration_types (Phase 2), not modifying it
- slash command keywords match existing .claude/skill-rules.json entries
- No embedding dependency — rule path works standalone

## 6. Acceptance Check Results

- P3-1 (Critical): prompt-normalizer 已实现 → **PASS**
  - Handles /plan, /debug, /task, /next
  - Detects repo_analysis, planning, debug, learning, construction_prompt
  - Multi-intent detection works (e.g., "诊断并制定修复计划")
  - Unknown input → unknown intent with 0.0 confidence

- P3-2 (Critical): rule-router 已实现 → **PASS**
  - rule_router.py (307 lines): keyword-weighted routing, slash command routing, RoutePlan generation

- P3-3 (Critical): routing_assets 已落地 → **PASS**
  - route_examples.json (20 examples), workflow_cards.json (3 workflows), skill_cards.json (10 skills)

- P3-4 (Critical): 4 scenarios 通过 rule path 正确路由 → **PASS**
  - ✅ "读取项目并评估功能，再给升级方案" → delivery_pipeline (confidence 1.0)
  - ✅ "生成 Claude 施工单" → delivery_pipeline (confidence 0.47)
  - ✅ "docker compose up 报 permission denied" → debug_pipeline (confidence 0.4)
  - ✅ "我想学 Docker 网络原理" → learning_pipeline (confidence 0.53)

- P3-5 (Critical): 不依赖 embedding 也能跑通 → **PASS**
  - RuleRouter works without any embedding service
  - route_source = "rule" for all rule-based routing
  - test_no_embedding_dependency PASS

- P3-6 (Recommended): 有 normalizer/router 测试 → **PASS**
  - test_prompt_normalizer.py: 5 test functions all PASS
  - test_rule_router.py: 8 test functions all PASS, 20/20 route examples correct

## 7. Test Results
- tests executed: 13 test functions (5 normalizer + 8 router)
- tests passed: 13/13
- tests failed: 0
- failure reason: N/A
- fixtures / mocks used: route_examples.json (20 labeled examples)
- Key metrics:
  - Route examples accuracy: 20/20 (100%)
  - 4 required scenarios: all correctly routed
  - Slash commands: /plan, /debug, /task, /next all correct
  - Multi-intent detection: working
  - Unknown input fallback: working

## 8. Risks / Known Issues
- Keyword-based routing is coarse — some edge cases may route to delivery_pipeline when debug_issue is more appropriate. Semantic router (Phase 4) addresses this.
- Chinese keyword matching works for tested phrases but may miss uncommon expressions
- Confidence values are weight-based not probability-based — should not be compared across different normalizer instances

## 9. Output Artifacts
- docs generated: none
- schemas generated: none
- route assets: route_examples.json (20), workflow_cards.json (3), skill_cards.json (10)
- test fixtures: route_examples.json doubles as test fixture
- validation outputs: test output (all PASS)

## 10. Gate Check
- Gate Result: **GO**
- Reason: All 5 critical acceptance items PASS. Normalizer and rule router fully implemented, all 4 scenarios route correctly, route_examples 20/20 accuracy, no embedding dependency.
- Blocking Issues: none
- Must Fix Before Next Phase: none
- If GO, prerequisites for next phase: semantic-router will layer on top of rule-router output; routing_assets JSON files needed as semantic index source
- Remaining Risks: Keyword-only routing may struggle with ambiguous inputs — Phase 4 semantic layer addresses this

## 11. Next Phase Plan
- next target: Phase 4 — semantic-router + workflow-resolver
- files expected to change: routing_assets/semantic_router.py, orchestration/workflow_resolver.py
- expected validation focus: embedding health check + degrade, resolver fusion (rule + semantic + safe_mode), 3 scenarios RoutePlan correctness

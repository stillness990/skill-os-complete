# Skill OS v4 — Architecture Report

> Generated: 2026-06-21 | Phase 6 final

---

## 1. System Architecture (Six-Layer Model)

```
Layer 1: Router            — 输入→intent→workflow→primary skill
Layer 2: Core Skills       — summarize / planning / debug
Layer 3: Workflow          — delivery / debug / learning pipeline
Layer 4: System            — task_ledger / learning_state / knowledge / debug_archive
Layer 5: Execution Guard   — 状态流转 / artifact / stall / audit
Layer 6: Extension         — orchestration / agents (multi-agent)
```

---

## 2. Routing Flow (Complete)

```
User Input (raw text)
    │
    ▼
PromptNormalizer (orchestration/prompt_normalizer.py)
    │  - strip /commands
    │  - detect intent types (repo_analysis/planning/debug/learning/construction_prompt)
    │  - detect multi-intent
    │  - output: NormalizedInput
    │
    ▼
RuleRouter (orchestration/rule_router.py)
    │  - keyword + regex matching
    │  - slash command exact routing
    │  - 4 high-confidence rules
    │  - output: list[RuleMatch]
    │
    ├──► SemanticRouter (orchestration/semantic_router.py)
    │      - embedding similarity search
    │      - EmbeddingProvider health check
    │      - graceful degradation on failure
    │      - output: list[SemanticCandidate]
    │
    ▼
WorkflowResolver (orchestration/workflow_resolver.py)
    │  - Multi-source fusion (rule + semantic)
    │  - SAFE MODE → rule_only
    │  - Degraded → rule_only
    │  - Fusion → weighted combination
    │  - output: unique RoutePlan
    │
    ▼
SkillRouter (orchestration/skill_router.py)
    │  - Execute stages in order
    │  - Collect artifacts
    │  - Write ledger
    │  - Invoke execution_guard
    │  - Call self_healing on failure
    │
    ├──► ExecutionGuard (orchestration/execution_guard.py)
    │      - Required stages check
    │      - Stage order check
    │      - Artifact existence check
    │      - No-op completion check
    │      - Pipeline-specific checks
    │
    ├──► SelfHealingManager (orchestration/self_healing.py)
    │      - retry ≤ 3
    │      - same_failure ≤ 2
    │      - embedding_fail → immediate fallback
    │      - anti-recursion guard
    │
    └──► SafeModeManager (orchestration/safe_mode.py)
           - Trigger on critical failures
           - Disable semantic router
           - Shrink healing
           - Conservative rollback
```

---

## 3. Workflow Templates

| Workflow | Required Stages | Skills |
|----------|----------------|--------|
| `delivery_pipeline` | understand (summarize), plan (planning), track (task_ledger) | summarize, planning, task_ledger, code_assistant, reviewer, changelog |
| `debug_pipeline` | diagnose (debug) | summarize, debug, code_assistant, debug_log |
| `learning_pipeline` | summarize, plan | ask, summarize, planning, teach-plus (×3), task_ledger |

---

## 4. Module Responsibilities

### Orchestration Layer (`orchestration/`)

| Module | Responsibility | Phase |
|--------|---------------|-------|
| `orchestration_types.py` | Enums: Intent, Workflow, TaskStatus, StageStatus, ExecutionStatus, SafeModeStatus, TaskType, RouteSource, FailureType | P2 |
| `route_plan.py` | RoutePlan + RouteStage dataclasses, GuardPolicy, create_route_plan_from_template | P2 |
| `workflow_state.py` | WorkflowState runtime state tracker | P2 |
| `prompt_normalizer.py` | Input normalization: slash commands, intent detection, multi-intent | P3 |
| `rule_router.py` | Rule-based routing: keywords, regex, slash commands | P3 |
| `embedding_provider.py` | Ollama embedding service wrapper: health check, get_embedding | P4 |
| `semantic_router.py` | Semantic routing: embedding index, cosine similarity, candidate retrieval | P4 |
| `workflow_resolver.py` | Multi-source fusion: rule + semantic + safe_mode → unique RoutePlan | P2-P4 |
| `skill_router.py` | Stage execution engine: execute plan, collect artifacts, invoke guard/healing | P5 |
| `execution_guard.py` | 6 rule checks: required stages, order, artifacts, ledger, no-op, pipeline-specific | P5 |
| `self_healing.py` | Retry limits, failure classification, healing decisions | P5 |
| `rollback_manager.py` | Safe artifact cleanup: path validation, ../ rejection, dry_run | P5 |
| `safe_mode.py` | Global safety switch: trigger, confirm, release, should_disable_semantic | P5 |

### System Layer (`ledger/`)

| Module | Responsibility |
|--------|---------------|
| `ledger_schema.py` | TaskEntry, TaskLedger dataclasses, v1→v4 migration, artifact path validation |
| `task_ledger.py` | TaskLedgerManager: CRUD, state transitions, persistence to tasks.json |

### Routing Assets (`routing_assets/`)

| Asset | Content |
|-------|---------|
| `workflow_cards.json` | 3 workflow definitions with trigger keywords and patterns |
| `skill_cards.json` | 10+ skill definitions with keywords and intents |
| `route_examples.json` | 20 labeled routing examples for testing |

### Production Hook

| File | Role |
|------|------|
| `.claude/hooks/skill-router.py` | Production entry point: intent→workflow→skill dispatch (preserved, not modified) |
| `.claude/router/routing_rules.py` | Production keyword+intent routing rules (preserved, not modified) |

---

## 5. Skill Compatibility Strategy

```
Old Hook (.claude/hooks/skill-router.py)
    │
    │  ←─ Coexists with new orchestration modules
    │  ←─ Not modified during Phase 3-6 upgrade
    │
    ▼
New Orchestration (orchestration/*.py)
    │
    │  ←─ Fully compatible import chain
    │  ←─ Can be adopted incrementally
    │  ←─ routing_assets/*.py preserved as reference copies
    ▼
Future: Old hook routes → New WorkflowResolver → SkillRouter
```

---

## 6. Data Flow Summary

```
Input → Normalize → Route (Rule + Semantic) → Fuse → Resolve → Execute → Guard → Heal → Complete
  │                                                         │         │        │
  │                                                         ▼         ▼        ▼
  │                                                    SkillRouter  Guard  SelfHealing
  │                                                         │
  └────────────────── SafeMode ←────────────────────────────┘
                              (global safety switch)
```

---

## 7. Test Coverage by Phase

| Phase | Test Files | Test Groups |
|-------|-----------|-------------|
| P3 | test_prompt_normalizer.py, test_rule_router.py | 13 |
| P4 | test_semantic_router.py, test_workflow_resolver.py | 14 |
| P5 | test_integration.py, test_rollback.py, test_safe_mode.py, test_ledger.py | 36 |
| P6 | Full regression + E2E + SAFE MODE + Rollback verification | 63 total |

---

## 8. Key Design Decisions

1. **Graceful degradation over crashing**: embedding unavailable → rule_only mode, never crashes
2. **Safe-first defaults**: EmbeddingHealth.degraded=True by default, SafeModeManager starts INACTIVE
3. **Path safety**: RollbackManager validates all paths against repo-root, rejects `../` and absolute paths
4. **Hard limits on retries**: SelfHealingManager max_retry=3, max_same_failure=2
5. **Separation of concerns**: Normalizer → Router → Resolver → Executor → Guard → Healer (each with single responsibility)
6. **Singleton pattern**: PromptNormalizer, RuleRouter, SemanticRouter, WorkflowResolver all provide get_*() singletons

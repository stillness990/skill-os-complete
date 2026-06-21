# Tests

> Skill OS Workflow OS 测试目录
> Phase 1 骨架建立 — 后续 Phase 逐步填充

## 目录结构

```
tests/
├── README.md                  # 本文件
├── test_prompt_normalizer.py  # [Phase 3] normalizer 单元测试
├── test_rule_router.py        # [Phase 3] rule-router 单元测试
├── test_semantic_router.py    # [Phase 4] semantic-router 单元测试
├── test_workflow_resolver.py  # [Phase 4] resolver 单元测试
├── test_skill_router.py       # [Phase 5] skill-router 单元测试
├── test_execution_guard.py    # [Phase 5] guard 单元测试
├── test_rollback.py           # [Phase 5] rollback 安全测试
├── test_self_healing.py       # [Phase 5] self-healing 单元测试
├── test_safe_mode.py          # [Phase 5] SAFE MODE 单元测试
├── test_integration.py        # [Phase 6] 集成测试
├── test_e2e.py                # [Phase 6] 端到端测试
├── test_fault_injection.py    # [Phase 6] 故障注入测试
└── fixtures/                  # 测试 fixtures
```

## Phase 填充计划

| Phase | 新建测试 |
|-------|---------|
| Phase 2 | 无（schema 自检在模块内完成） |
| Phase 3 | test_prompt_normalizer.py, test_rule_router.py |
| Phase 4 | test_semantic_router.py, test_workflow_resolver.py |
| Phase 5 | test_skill_router.py, test_execution_guard.py, test_rollback.py, test_self_healing.py, test_safe_mode.py |
| Phase 6 | test_integration.py, test_e2e.py, test_fault_injection.py |

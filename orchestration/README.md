# Orchestration Module

> Skill OS Workflow OS 编排模块
> Phase 1 骨架建立 — Phase 2 起逐步实现

## 目录结构

```
orchestration/
├── README.md                  # 本文件
├── route_plan.py              # [Phase 2] RoutePlan + RouteStage 数据结构
├── workflow_state.py          # [Phase 2] workflow 运行时状态
├── orchestration_types.py     # [Phase 2] 编排类型定义
├── workflow_resolver.py       # [Phase 4] 多源融合 → 唯一 RoutePlan
├── skill_router.py            # [Phase 5] RoutePlan 执行器
├── execution_guard.py         # [Phase 5] 执行链 guard 检查
├── guard_policy.py            # [Phase 5] guard 策略定义
├── rollback_manager.py        # [Phase 5] 回滚管理器
├── self_healing.py            # [Phase 5] 自愈模块
└── safe_mode.py               # [Phase 5] SAFE MODE 状态管理
```

## Phase 填充计划

| Phase | 新建文件 |
|-------|---------|
| Phase 2 | route_plan.py, workflow_state.py, orchestration_types.py |
| Phase 4 | workflow_resolver.py |
| Phase 5 | skill_router.py, execution_guard.py, guard_policy.py, rollback_manager.py, self_healing.py, safe_mode.py |

"""
Orchestration Package — Skill OS v5 编排层

多源融合路由系统：prompt_normalizer → rule_router → semantic_router → workflow_resolver

子模块:
- orchestration_types: 统一类型定义 (Intent, Workflow, ExecutionStatus, etc.)
- route_plan: 核心路由计划数据结构
- workflow_state: workflow 运行时状态追踪
- prompt_normalizer: 输入标准化器
- rule_router: 规则路由引擎
- semantic_router: 语义路由候选层
- embedding_provider: embedding 服务接口层
- workflow_resolver: 多源融合决策器 (主入口)
- execution_guard: 执行监督层
- rollback_manager: 回滚管理器
- safe_mode: 安全模式
- self_healing: 自愈引擎
- skill_router: 技能路由编排
"""

__version__ = "5.0.0"

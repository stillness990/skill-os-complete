# Phase 1 Mapping — 升级映射表

> 每个模块至少包含：当前文件、当前职责、存在问题、升级动作、升级后落点

---

## M1: summarize（知识整理与 briefing 生成器）

| 维度 | 内容 |
|------|------|
| **当前文件** | `.claude/skills/core/summarize/SKILL.md`, `modes/basic.md`, `modes/briefing.md` |
| **当前职责** | 读取输入 → 提炼结构化摘要 → 产出 basic 或 briefing |
| **存在问题** | 无重大问题；功能完整，协议完整 |
| **升级动作** | Phase 2 将其接入 RoutePlan 的 stage schema（作为 understand stage 的标准实现）；Phase 5 通过 skill-router 按 RoutePlan 调用 |
| **升级后落点** | 保持现有路径不变；新增 `orchestration/route_plan_stages.py` 中注册为 `"summarize"` stage handler |

---

## M2: planning（任务拆解与执行计划生成器）

| 维度 | 内容 |
|------|------|
| **当前文件** | `.claude/skills/core/planning/SKILL.md`, `project.md`, `learning.md` |
| **当前职责** | 基于 briefing 拆阶段 → 标依赖/风险/优先级 → 产出 plan + 今日最小行动 |
| **存在问题** | 无重大问题；双模式 (project/learning) 功能完整 |
| **升级动作** | Phase 2 将其输出格式化为符合 RoutePlan stage schema；Phase 5 通过 skill-router 按 RoutePlan 顺序调用 |
| **升级后落点** | 保持现有路径不变；在 `orchestration/route_plan_stages.py` 中注册为 `"planning"` stage handler |

---

## M3: debug（诊断引擎）

| 维度 | 内容 |
|------|------|
| **当前文件** | `.claude/skills/core/debug/SKILL.md`, `diagnosis.md`, `regression.md` |
| **当前职责** | 确认现象 → 最小复现 → 假设 → 验证 → 根因 → 修复建议 → 回归清单 |
| **存在问题** | 无重大问题；8 步流程完整 |
| **升级动作** | Phase 2 将其输出格式化为符合 RoutePlan stage schema；Phase 5 通过 skill-router 按 RoutePlan 调用 |
| **升级后落点** | 保持现有路径不变；在 `orchestration/route_plan_stages.py` 中注册为 `"debug"` stage handler |

---

## M4: ask（需求澄清）

| 维度 | 内容 |
|------|------|
| **当前文件** | `.claude/skills/ask/SKILL.md` |
| **当前职责** | 模糊需求澄清，max 3 questions，不做代码操作 |
| **存在问题** | 当前仅在 delivery_pipeline 中被引用为可选阶段，但 routing_rules.py 的 detect_intent 不识别 "需要澄清" 的中间态 |
| **升级动作** | Phase 3 在 prompt-normalizer 中增加 "fuzzy_intent" 识别；Phase 4 workflow-resolver 可将 ask 作为 RoutePlan 的首个 stage |
| **升级后落点** | 保持现有路径；在 routing_assets/skill_cards.json 中增加 stage_hint |

---

## M5: Router（路由层）

| 维度 | 内容 |
|------|------|
| **当前文件** | `.claude/router/routing_rules.py`, `skill_index.json`, `workflow_templates.json`, `intent_schema.md`; `.claude/hooks/skill-router.py`; `.claude/skill-rules.json` |
| **当前职责** | 关键词评分 + 意图检测 → workflow 选择 → 注入 skill 指令 |
| **存在问题** | ① 路由决策与执行耦合在同一 hook 中（skill-router.py 既做路由又注入指令）；② 无 prompt 标准化层；③ 仅支持关键词+regex，无语义候选；④ 无 workflow-resolver 融合决策；⑤ mode_routing (learning) 无代码实现 |
| **升级动作** | **Phase 3**: 新建 `routing_assets/prompt_normalizer.py` (标准化输入) + `routing_assets/rule_router.py` (规则路由，从 routing_rules.py 提取纯规则部分) + `routing_assets/route_examples.json` / `workflow_cards.json` / `skill_cards.json`；**Phase 4**: 新建 `routing_assets/semantic_router.py` + `orchestration/workflow_resolver.py`；**Phase 5**: 新建 `orchestration/skill_router.py` (执行链) |
| **升级后落点** | `routing_assets/` 目录承载标准化 + 规则路由 + 语义候选；`orchestration/` 目录承载 resolver + skill-router；`hooks/skill-router.py` 简化为调用 resolver → skill-router 的薄层 |

---

## M6: execution_guard（执行监督层）

| 维度 | 内容 |
|------|------|
| **当前文件** | `.claude/system/execution_guard/` (5 文档); `.claude/hooks/task-guard.py`, `completion-guard.py` |
| **当前职责** | 文档定义 5 条规则；hook 仅做停滞警告和静态清单注入 |
| **存在问题** | ① task-guard.py 声明 Phase 1 stub，不拦截非法状态转移；② completion-guard.py 的 check_done_conditions() 是死代码；③ completion-guard.py 的 changed_files 字段路径错误（读顶层而非 artifact_refs 内）；④ 无 pipeline 专项校验代码；⑤ 无 SAFE MODE 联动 |
| **升级动作** | **Phase 5**: 重写 task-guard.py（真正校验状态转移合法性）；重写 completion-guard.py（真正检查 artifact + 调用 check_done_conditions）；新增 pipeline 专项校验模块；新增与 safe_mode 的联动逻辑 |
| **升级后落点** | `.claude/hooks/task-guard.py` (升级版), `.claude/hooks/completion-guard.py` (升级版); 新增 `orchestration/execution_guard.py` (可独立调用的 guard 检查函数); 新增 `orchestration/guard_policy.py` (guard 策略定义) |

---

## M7: task_ledger（任务账本）

| 维度 | 内容 |
|------|------|
| **当前文件** | `.claude/system/task_ledger/schema.md`, `tasks.json`, `task-ops.py`, `learning-task-schema.md` |
| **当前职责** | 任务 CRUD + 状态跟踪 + CLI 操作 |
| **存在问题** | ① task-ops.py 状态验证用 v1 词汇 (in_progress/retry)，不支持 v4 新增状态 (planning/executing/stalled/cancelled)；② tasks.json version 错标 "1.0.0"；③ add 命令缺少 --task-type、--expected-artifacts、--route-id 等 v4 字段；④ 无 ledger 查询 API（仅 CLI） |
| **升级动作** | **Phase 2**: 升级 ledger_schema（新增 route_id/workflow/intent/stage_id/stage_status/expected_artifacts/artifact_paths/retry_count/safe_mode 等字段）；重写 task-ops.py（支持 v4 全状态 + 新字段读写）；新增 `ledger/ledger_api.py`（可编程查询接口，供 resolver/guard/healing 调用） |
| **升级后落点** | `.claude/system/task_ledger/` 保持现有文件并升级内容；新增 `ledger/ledger_schema.py` (Python schema 定义); 新增 `ledger/ledger_api.py` (查询 API); 新增 `ledger/task_ledger.py` (主模块) |

---

## M8: workflow entry（工作流入口）

| 维度 | 内容 |
|------|------|
| **当前文件** | `.claude/workflows/delivery_pipeline.md`, `debug_pipeline.md`, `learning_pipeline.md` |
| **当前职责** | 定义 3 条 pipeline 的阶段顺序和 guard 检查点 |
| **存在问题** | ① 仅为文档，无程序化执行；② 阶段是否必须执行的判断依赖 Claude 自行阅读文档后决定；③ 无 workflow state 运行时追踪；④ 无 RoutePlan 结构化的阶段定义 |
| **升级动作** | **Phase 2**: 将 workflow 文档的结构化信息抽取到 `orchestration/workflow_state.py` + `orchestration/route_plan.py`；**Phase 4**: workflow-resolver 读取这些结构化定义输出 RoutePlan；**Phase 5**: skill-router 按 RoutePlan 的 stages 顺序执行 |
| **升级后落点** | `.claude/workflows/` 文档保留（人类可读参考）；结构化定义迁移到 `orchestration/route_plan.py` + `orchestration/workflow_state.py` + `routing_assets/workflow_cards.json` |

---

## 汇总表

| 模块 | 当前状态 | 升级紧急度 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 |
|------|---------|-----------|---------|---------|---------|---------|---------|
| summarize | ✅ 完整 | 低 | 接入 stage schema | — | — | 按 RoutePlan 执行 | 端到端测试 |
| planning | ✅ 完整 | 低 | 接入 stage schema | — | — | 按 RoutePlan 执行 | 端到端测试 |
| debug | ✅ 完整 | 低 | 接入 stage schema | — | — | 按 RoutePlan 执行 | 端到端测试 |
| ask | ✅ 完整 | 中 | — | fuzzy_intent 识别 | 作为 stage 候选 | 按 RoutePlan 执行 | — |
| router | ⚠️ 需重构 | **高** | — | 拆分为 normalizer + rule-router | semantic-router + resolver | skill-router 执行链 | 全量路由测试 |
| execution_guard | ⚠️ 仅文档 | **高** | guard_policy schema | — | — | 真正实现拦截逻辑 | 故障注入验证 |
| task_ledger | ⚠️ 版本滞后 | **高** | schema + ops 升级 | — | — | API 接入 guard/healing | 状态正确性验证 |
| workflow entry | ⚠️ 仅文档 | **高** | workflow_state + route_plan schema | — | resolver 融合 | skill-router 执行 | 端到端验证 |

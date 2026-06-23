# Skill OS v5 — 仓库操作手册

> 本文档面向在此仓库中工作的 Claude Code 智能体。说明仓库分层、workflow 使用规则、技能边界和完成约束。

---

## 仓库正式分层（6+1 层架构）

```
L0: Knowledge Bus（知识总线）    — knowledge-asset 唯一知识出口，横切所有层
L1: Router（路由层）             — prompt_normalizer → rule_router → semantic_router → workflow_resolver
L2: Core Skills（核心基座）      — summarize / planning / debug
L3: Workflow（工作流控制）       — delivery / debug / learning
L4: State（统一状态层）          — .claude/state/ (4 JSON + checkpoint)
L5: Execution Guard（监督层）    — 7 条强制规则 + 5 层校验引擎
L6: Extension（扩展层）          — orchestration / agents（预留）
```

---

## 什么时候走哪个 workflow

| 用户意图 | intent | workflow | primary skill |
|---------|--------|----------|---------------|
| 项目规划/重构/开发/拆解 | `project_delivery` | `delivery_pipeline` | `planning` |
| 报错/异常/排查/诊断 | `debug_issue` | `debug_pipeline` | `debug` |
| 学习/教程/复盘/练习 | `learn_topic` | `learning_pipeline` | `teach-plus` |
| 知识沉淀/SOP/留档 | `knowledge_asset` | L0 Knowledge Bus | `knowledge-asset` |
| 意图不明确 | — | fallback 单 skill | 最高分 skill |

> **v5 关键变化**：所有 pipeline 末端强制经过 `knowledge-asset` (L0 Knowledge Bus)。`sop` 和 `debug_log` 已标记为 legacy compatibility only，功能合并入 `knowledge-asset`。状态管理统一在 `.claude/state/`。

---

## summarize / planning / debug 的边界

### summarize（知识整理与 briefing 生成器）

- **做**：读取输入 → 提炼结构化摘要 → 产出 basic 或 briefing
- **不做**：任务拆解（planning）、诊断（debug）、写代码（code_assistant）、状态管理（task_ledger）
- **位置**：`.claude/skills/core/summarize/`
- **协议**：`summary-protocol.md` / `briefing-protocol.md`

### planning（任务拆解与执行计划生成器）

- **做**：基于 briefing 拆阶段 → 标依赖/风险/优先级 → 产出 plan + 今日最小行动
- **不做**：知识整理（summarize）、诊断（debug）、写代码（code_assistant）、学习练习（teach-plus）
- **位置**：`.claude/skills/core/planning/`
- **协议**：`plan-protocol.md` / `learning-plan-protocol.md`
- **与 execution_guard 关系**：planning 的 plan 是 guard 检查 done 条件的基准
- **v5 L0 接入**：可选接入 knowledge-asset（project-plans 模板）

### debug（诊断引擎）

- **做**：确认现象 → 最小复现 → 假设 → 验证 → 根因 → 修复建议 → 回归清单
- **不做**：直接写代码修复（那是 code_assistant 的事）
- **位置**：`.claude/skills/core/debug/`
- **协议**：`debug-protocol.md`
- **与 code_assistant 交接**：debug 在修复建议中明确标注需交给 code_assistant 的文件和改动点

---

## teach-plus 与 learning_state 的关系

teach-plus 是 Learning Workflow Controller，不是独立教学技能：

```
teach-plus 依赖链（v5）：
  summarize（学习底稿）→ planning（学习计划）→ teach-plus（explain/practice/review）
      ↕
  learning_state（状态追踪，.claude/state/learning-state.json）↔ task_ledger（任务记录）
      ↕
  knowledge-asset（L0 知识出口，knowledge-notes 模板）
      ↕
  execution_guard（完成约束）
```

| teach-plus 模式 | learning_state 操作 |
|----------------|-------------------|
| explain | 创建/更新 state，推进 topic_new → understanding |
| practice | 更新 current_stage / last_activity_at / next_action |
| review | 更新 review_ref / next_review，推进或回退 stage |

**断档检测**：practice 进入前检查 last_activity_at，按 `study-resume-policy.md` 恢复。

---

## task_ledger 是正式任务入口

- `task_ledger` 是系统层正式任务账本（`.claude/system/task_ledger/`）
- 旧 `task_manager` 是兼容 alias（`.claude/skills/task_manager/`）
- 所有文档和代码引用统一使用 `task_ledger`
- 任务状态（v5 扩展）：queued / planning / executing / blocked / retrying / stalled / done / cancelled
- 完整状态机见 `.claude/system/execution_guard/task-state-machine.md`
- **v5 变更**：任务状态同步写入 `.claude/state/current-task.json`（统一状态层）

---

## execution_guard 如何约束任务完成

7 条强制规则（详见 `.claude/system/execution_guard/guard-rules.md`）：

1. **done 必须带 artifact**：artifacts 非空 + result_summary 有意义
2. **状态流转必须合法**：符合 task-state-machine.md，禁止 queued→done 等跳步骤
3. **workflow 最小产物检查**：delivery 要有 plan_ref+changed_files，debug 要有 debug_report_ref+root_cause，learning 要有 learning_state 更新
4. **施工任务必须有落地证据**：changed_files 非空，不允许"口头完成"
5. **超时未更新处理**：planning/executing 超过 3 天 warning，超过 7 天 stalled
6. **knowledge-asset 强制沉淀**（v5 新增 L0）：debug/learning 强制沉淀，delivery 施工类强制
7. **state/ 更新检查**（v5 新增 L4）：任务完成前必须写入 state/ 统一状态层

5 层校验引擎（`completion-guard.py`）：
```
state_transition → artifacts → task_type → L0_ka → L4_state
```

两个 hook 检查点：
- `task-guard.py`：任务状态变更时校验 + stall 检测 + pipeline 上下文注入
- `completion-guard.py`：任务进入 done 时 5 层校验

---

## legacy skill 兼容策略

| 旧名称 | 新名称 | 兼容方式 |
|--------|--------|---------|
| `planner` | `planning` | 旧 SKILL.md 保留 + MIGRATION.md；skill-rules.json 中两条都可命中 |
| `summarize`（旧目录） | `core/summarize` | 旧目录保留，内容指向新版 |
| `debug`（旧目录） | `core/debug` | 同上 |
| `task_manager` | `task_ledger` | skill-rules.json 中保留 task_manager 条目作为 alias；正式文档只用 task_ledger |
| `sop` | `knowledge-asset` | **v5 已标记为 legacy compatibility only**，功能合并入 knowledge-asset (sop 模式) |
| `debug_log` | `knowledge-asset` | **v5 已标记为 legacy compatibility only**，功能合并入 knowledge-asset (troubleshooting 模式) |
| `system/learning_state/` | `state/` | **v5 已迁移**，`.claude/state/learning-state.json` 为新的唯一状态源 |
| `system/task_ledger/` | `state/` | **v5 配合使用**，任务状态引用 state/ 统一状态层 |

---

## 多代理：Phase 4 扩展层，不要滥用

- 多代理（orchestrator / complexity_detector / agent_definitions）目前只做结构占位
- **不要**在当前任务中启动多代理 workflow
- **不要**把单代理能做的事推给多代理
- 目录位置：`.claude/orchestration/` + `.claude/agents/`

---

## knowledge-asset（L0 Knowledge Bus — v5 唯一知识出口）

- **做**：接收所有 skill 的知识产出 → 匹配 5 类模板 → 9-section 结构化 → 写入 `knowledge/{type}/`
- **不做**：直接写代码、诊断、教学
- **位置**：`.claude/skills/knowledge-asset/`
- **5 类模板**：SOP / Troubleshooting / Architecture / Knowledge Note / Project Plan
- **强制闭环**：debug/learning 强制沉淀，delivery 施工类强制
- **禁止绕过**：任何 skill 不得直接写入 `knowledge/*` 或 `docs/*`
- **已收编**：`sop`（SOP 模式）、`debug_log`（Troubleshooting 模式）

---

## 施工注意事项

1. **先读现状再改**：修改前先扫描相关文件和目录
2. **遵循协议**：summarize/planning/debug 输出必须遵循对应 protocol
3. **不要跳过 execution_guard**：任务完成前自检 7 条规则 + 5 层校验
4. **强制走 L0**：知识产出必须通过 knowledge-asset，禁止直接写 knowledge/ 或 docs/
5. **更新 state/**：任务状态变更需同步写入 `.claude/state/`
6. **不要删除旧目录**：legacy shim 目录保留，只标记不删除
7. **更新后同步文档**：改完结构和 skill 后检查 README/CLAUDE/rules 是否同步

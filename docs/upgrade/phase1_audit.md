# Phase 1 Audit — 仓库结构审计报告

> 审计时间：2026-06-21
> 仓库：skill-os-complete (Skill OS v4.0.0)
> 审计方式：全量文件遍历 + 关键文件深度阅读

---

## 1. 仓库整体结构

```
skill-os-complete/
├── .claude/                         # 核心系统目录
│   ├── agents/                      # [Phase 4 占位] 多代理定义
│   │   └── README.md
│   ├── hooks/                       # [活跃] 3 个 hook 脚本
│   │   ├── skill-router.py          #   UserPromptSubmit → 路由决策注入
│   │   ├── task-guard.py            #   [Phase 1 stub] 任务状态校验
│   │   └── completion-guard.py      #   [Phase 1 stub] 任务完成校验
│   ├── orchestration/               # [Phase 4 占位] 多代理编排
│   │   ├── artifacts/               #   空目录
│   │   ├── runs/                    #   空目录
│   │   ├── schema/                  #   空目录
│   │   └── README.md
│   ├── protocols/                   # [完成] 7 个输出协议
│   │   ├── summary-protocol.md
│   │   ├── briefing-protocol.md
│   │   ├── plan-protocol.md
│   │   ├── learning-plan-protocol.md
│   │   ├── debug-protocol.md
│   │   ├── daily-study-protocol.md
│   │   └── weekly-review-protocol.md
│   ├── router/                      # [活跃] 路由层
│   │   ├── intent_schema.md         #   意图定义 (3 intents + fallback)
│   │   ├── routing_rules.py         #   核心路由引擎
│   │   ├── skill_index.json         #   16 技能索引
│   │   └── workflow_templates.json  #   3 条 workflow 模板
│   ├── skills/                      # [活跃] 14 技能 + 4 legacy shim
│   │   ├── core/                    #   核心基座 (summarize/planning/debug)
│   │   ├── teach-plus/              #   学习工作流控制器
│   │   ├── ask/ changelog/ code_assistant/ debug_log/
│   │   ├── dify_kb_search/ echo/ reviewer/ sanitize/ sop/
│   │   └── debug/ planner/ summarize/ task_manager/ (legacy)
│   ├── system/                      # [活跃] 系统层
│   │   ├── task_ledger/             #   任务账本 (schema + ops + tasks.json)
│   │   ├── learning_state/          #   学习状态追踪 (7 阶段状态机)
│   │   ├── execution_guard/         #   执行监督 (5 规则 + 完整文档)
│   │   ├── knowledge/               #   知识存储 (结构已定义)
│   │   └── debug_archive/           #   诊断归档 (Phase 1 占位)
│   ├── workflows/                   # [完成] 3 条 workflow 文档
│   │   ├── delivery_pipeline.md
│   │   ├── debug_pipeline.md
│   │   └── learning_pipeline.md
│   ├── settings.json                # Hook 注册 (仅 UserPromptSubmit)
│   └── skill-rules.json             # 18 条路由关键词规则
├── docs/
│   └── upgrade/                     # 升级规范文档 (4 个)
│       ├── 00_master_runbook.md
│       ├── 01_phase_acceptance.md
│       ├── 02_phase_report_template.md
│       └── 03_safe_mode_and_rollback.md
├── CLAUDE.md                        # 仓库操作手册
├── README.md                        # 项目 README (v4.0.0)
├── install.sh                       # 安装脚本 (含 22 路由测试)
├── deploy.sh                        # 升级/部署脚本
├── uninstall.sh                     # 卸载脚本
└── .gitignore
```

---

## 2. 主链路入口

| 入口 | 类型 | 路径 | 说明 |
|------|------|------|------|
| UserPromptSubmit Hook | Python | `.claude/hooks/skill-router.py` | 每次用户输入触发，调用 routing_rules.build_router_decision() |
| 路由引擎 | Python | `.claude/router/routing_rules.py` | 关键词评分 + 意图检测 + workflow 选择 |
| 路由规则 | JSON | `.claude/skill-rules.json` | 18 技能的关键词和 intentPatterns |
| 技能索引 | JSON | `.claude/router/skill_index.json` | 16 技能的元数据索引 |
| Workflow 模板 | JSON | `.claude/router/workflow_templates.json` | 3 条 pipeline 的阶段定义 |

**当前路由链**: `用户输入 → skill-router.py → routing_rules.py → 注入 skill 指令 → Claude 执行`

---

## 3. 现有 Skills 完整列表

### 3.1 核心基座 (Layer 2)

| Skill | 路径 | 状态 | 职责 |
|-------|------|------|------|
| `summarize` | `skills/core/summarize/` | ✅ 完整 | 知识整理 / briefing 生成器，basic + briefing 双模式 |
| `planning` | `skills/core/planning/` | ✅ 完整 | 任务拆解 / 执行计划生成器，project + learning 双模式 |
| `debug` | `skills/core/debug/` | ✅ 完整 | 诊断引擎，diagnosis + regression 子流程 |

### 3.2 学习工作流控制器

| Skill | 路径 | 状态 | 职责 |
|-------|------|------|------|
| `teach-plus` | `skills/teach-plus/` | ✅ 完整 | 学习工作流控制器，explain/practice/review 三模式 |

### 3.3 执行层 Skills

| Skill | 路径 | 状态 | 职责 |
|-------|------|------|------|
| `ask` | `skills/ask/` | ✅ 完整 | 需求澄清 (max 3 questions) |
| `code_assistant` | `skills/code_assistant/` | ✅ 完整 | 代码编写/修复/重构 |
| `reviewer` | `skills/reviewer/` | ✅ 完整 | 代码审查 (只读) |
| `changelog` | `skills/changelog/` | ✅ 完整 | 变更日志生成 |
| `sanitize` | `skills/sanitize/` | ✅ 完整 | 脱敏扫描 (含 636 行 Python 实现) |
| `sop` | `skills/sop/` | ✅ 完整 | 标准操作手册生成 |
| `debug_log` | `skills/debug_log/` | ✅ 完整 | 排查记录归档 |

### 3.4 工具 Skills

| Skill | 路径 | 状态 | 职责 |
|-------|------|------|------|
| `echo` | `skills/echo/` | ✅ 完整 | 原样返回输入 |
| `dify_kb_search` | `skills/dify_kb_search/` | ✅ 完整 | 电工知识库检索 |

### 3.5 Legacy Shim (兼容别名)

| Skill | 路径 | 迁移目标 | 状态 |
|-------|------|---------|------|
| `planner` | `skills/planner/` | `core/planning` | MIGRATION.md 已标注 |
| `summarize` (旧) | `skills/summarize/` | `core/summarize` | MIGRATION.md 已标注 |
| `debug` (旧) | `skills/debug/` | `core/debug` | MIGRATION.md 已标注 |
| `task_manager` | `skills/task_manager/` | `system/task_ledger` | MIGRATION.md 已标注 |

---

## 4. Guard / Ledger / Router 现状

### 4.1 Router（路由层）

| 组件 | 状态 | 亮点 | 问题 |
|------|------|------|------|
| `routing_rules.py` | ⚠️ 部分可用 | 关键词评分 + 意图检测 + workflow 选择链路完整 | `load_skill_rules()` 引用 `.claude/skill-rules.json`（旧路径），当前仓库实际文件是 `.claude/skill-rules.json`；`detect_intent` 硬编码 skill 名而非从 index 读取 |
| `skill_index.json` | ✅ 完整 | 16 技能完整索引 | `execution_guard.auto_trigger: true` 无实现；`dify_kb_search.intents` 为空数组 |
| `workflow_templates.json` | ✅ 完整 | 3 pipeline 阶段定义完整 | `learning_pipeline.mode_routing` 无代码实现 |
| `skill-rules.json` | ✅ 完整 | 18 条规则 + intentPatterns | 部分 intentPattern 正则可能匹配过宽 |
| `skill-router.py` | ⚠️ 部分可用 | 路由注入链路完整 | 无错误恢复（除 stdin 解析外）；teach-plus 指令与 workflow_templates.json 定义重复 |

### 4.2 Execution Guard（执行监督层）

| 组件 | 状态 | 亮点 | 问题 |
|------|------|------|------|
| `guard-rules.md` | ✅ 文档完整 | 5 条核心规则 + 协作矩阵 | 无代码实现（仅有文档） |
| `task-state-machine.md` | ✅ 文档完整 | 8 状态 + 完整转移矩阵 | 无代码强制执行 |
| `artifact-requirements.md` | ✅ 文档完整 | 按 task_type 定义产物要求 | 无自动检查 |
| `stall-policy.md` | ✅ 文档完整 | 3 天/7 天双阈值 | `task-guard.py` 未检查 retrying 状态 |
| `audit-checklist.md` | ✅ 文档完整 | A/B/C 三级检查项 | 无自动化执行 |
| `task-guard.py` | ⚠️ Phase 1 stub | 停滞检测基本可用 | 声明"Phase 4+ 完整逻辑"；仅检查 planning/executing 停滞，忽略 retrying；状态词汇与 schema 不一致 |
| `completion-guard.py` | ⚠️ Phase 1 stub | `check_done_conditions()` 逻辑已写 | **死代码**：main() 从不调用它；`changed_files` 字段路径错误 |

### 4.3 Task Ledger（任务账本）

| 组件 | 状态 | 亮点 | 问题 |
|------|------|------|------|
| `schema.md` | ✅ 文档完整 | v4 扩展 schema (20+ 字段) | 状态表格混用 v1/v4 词汇 |
| `tasks.json` | ⚠️ 数据不一致 | 基本结构正确 | version 标记 "1.0.0" 应为 "4.0.0"；现有 task 缺少 task_type/artifact_refs/guard_status |
| `task-ops.py` | ⚠️ 版本滞后 | CLI 基本可用 | 状态验证用旧词汇 (in_progress/retry)，不支持 v4 新增状态 (planning/executing/stalled/cancelled)；add 命令缺少 --task-type |
| `learning-task-schema.md` | ✅ 完整 | learning task 扩展定义完整 | 无代码实现 |

### 4.4 Learning State（学习状态追踪）

| 组件 | 状态 | 亮点 | 问题 |
|------|------|------|------|
| `learning-state-machine.md` | ✅ 文档完整 | 7 正常 + 3 异常状态 | 无代码驱动状态转移 |
| `learning-state-schema.md` | ✅ 文档完整 | topic 数据结构完整 | schema 示例与实际 state.json 不一致 |
| `study-resume-policy.md` | ✅ 文档完整 | 4 级断档恢复策略 | **零代码实现**：无自动检测/提示/状态变更 |
| `state.json` | ✅ 数据正确 | version "4.0.0" + 空 topics | 正常（无学习活动） |

---

## 5. 协议层现状

| 协议 | 版本 | 完整性 | 下游消费者 |
|------|------|--------|-----------|
| `summary-protocol.md` | v4 | ✅ | planning, debug |
| `briefing-protocol.md` | v4 | ✅ | planning, debug, teach-plus |
| `plan-protocol.md` | v4 | ✅ | task_ledger, teach-plus |
| `learning-plan-protocol.md` | v1 (Phase 2) | ✅ | teach-plus/practice, teach-plus/review |
| `debug-protocol.md` | v4 | ✅ | code_assistant, debug_archive, task_ledger |
| `daily-study-protocol.md` | v1 (Phase 2) | ✅ | weekly-review-protocol |
| `weekly-review-protocol.md` | v1 (Phase 2) | ✅ | learning_state, task_ledger |

---

## 6. 文档/测试/配置现状

| 类别 | 现状 |
|------|------|
| **项目文档** | README.md (310 行, v4.0.0), CLAUDE.md (134 行) — 完整 |
| **升级文档** | docs/upgrade/ 下 4 个规范性文档 — 完整 |
| **架构文档** | ❌ 缺失 `docs/architecture/` |
| **验证文档** | ❌ 缺失 `docs/validation/` |
| **故障文档** | ❌ 缺失 `docs/failure/` |
| **测试目录** | ❌ 无独立 `tests/` 目录；install.sh 内含 22 路由测试；无单元/集成测试 |
| **配置** | settings.json (1 hook), skill-rules.json (18 rules) — 完整 |

---

## 7. 关键发现汇总

### 7.1 跨模块状态词汇不一致（3 套词汇并存）

| 词汇集 | 使用者 | 状态列表 |
|--------|--------|---------|
| v1 旧词汇 | `task-ops.py` | queued, in_progress, blocked, done, retry |
| v4 新词汇 | execution_guard docs, task-guard.py | queued, planning, executing, blocked, retrying, stalled, done, cancelled |
| schema.md 混合 | schema.md | 表格中混用 in_progress 和 executing |

### 7.2 钩子逻辑缺口

| 钩子 | 问题 |
|------|------|
| `task-guard.py` | Phase 1 stub，不做状态转移拦截 |
| `completion-guard.py` | `check_done_conditions()` 是死代码；字段路径错误 |

### 7.3 无代码实现的关键能力

| 能力 | 规范状态 | 实现状态 |
|------|---------|---------|
| mode_routing (learning_pipeline) | workflow_templates.json 已定义 | ❌ 无代码 |
| execution_guard 规则强制执行 | 5 规则 + 审计清单完整 | ❌ 仅文档 |
| learning_state 状态驱动 | 7 阶段状态机完整 | ❌ 无驱动代码 |
| study-resume 断档恢复 | 4 级策略完整 | ❌ 零代码 |
| auto_trigger execution_guard | skill_index 声明 | ❌ 无触发机制 |

### 7.4 技术债务

| 问题 | 位置 | 严重度 |
|------|------|--------|
| `changed_files` 字段路径错误 | completion-guard.py:58 | 高 |
| task-ops.py 状态词汇过时 | task-ops.py:cmd_status/cmd_next | 高 |
| tasks.json version 错标 | tasks.json meta.version | 中 |
| skill-rules.json 路径引用 | routing_rules.py:21 | 中 |
| 中英文混用 | skill-router.py, completion-guard.py | 低 |
| ISO 8601 Z 后缀兼容 | tasks.json, task-guard.py | 低 |

---

## 8. 缺失目录清单

以下目录在 runbook 中定义但仓库中不存在：

| 目录 | 用途 | 优先级 |
|------|------|--------|
| `docs/architecture/` | 架构文档 | Phase 1 |
| `docs/validation/` | 验证文档 | Phase 1 |
| `docs/failure/` | 故障报告 | Phase 1 |
| `orchestration/` (根目录) | 编排模块 | Phase 1 (骨架) |
| `ledger/` (根目录) | 新 ledger 模块 | Phase 1 (骨架) |
| `routing_assets/` (根目录) | 路由资产 | Phase 1 (骨架) |
| `tests/` (根目录) | 测试 | Phase 1 (骨架) |

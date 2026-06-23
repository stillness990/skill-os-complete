# Skill OS v5 — 系统架构

> 版本：v5.0.0 | 生成：2026-06-22 | Phase 8 最终交付

---

## 一、概述

Skill OS v5 是 Claude Code 的本地技能操作系统，提供从输入路由到执行监督的完整闭环。v5 在 v4 六层架构基础上引入 **L0 Knowledge Bus**（横切知识出口层），形成 6+1 层架构。

### v5 设计目标

| 目标 | 实现方式 |
|------|---------|
| **知识不散落** | L0 Knowledge Bus — 唯一知识出口，所有长期产出必经此层 |
| **状态可恢复** | L4 State — 统一状态层，checkpoint 机制支持断点恢复 |
| **执行可验证** | L5 Guard — 7 条强制规则，5 层校验引擎，防"口头完成" |
| **技能可追溯** | 每个 skill 输出明确标注 knowledge-asset 沉淀要求 |

### v4 → v5 关键变化

```
v4:  6 层架构，知识分散在对话/debug-logs/docs/practice
     ↓
v5:  6+1 层架构，L0 Knowledge Bus 横切所有层，统一知识出口
```

---

## 二、6+1 层架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        Skill OS v5                               │
│                                                                  │
│  L6 Extension    ← orchestration/ agents/  (多代理扩展预留)       │
│  L5 Guard        ← 7 条强制规则 + 5 层校验引擎 + checkpoint      │
│  L4 State        ← .claude/state/  (统一状态层，单一真实来源)     │
│  L3 Workflow     ← 3 pipelines + routing + skill dispatch        │
│  L2 Core         ← summarize / planning / debug  (三大基座)      │
│  L1 Router       ← rule_router + semantic_router + normalizer    │
│                                                                  │
│  ═══════════════════════════════════════════════════════════     │
│  L0 Knowledge Bus ← knowledge-asset Engine  (唯一知识出口)        │
│                     SOP / Troubleshooting / Architecture         │
│                     Knowledge Note / Project Plan                │
│  ═══════════════════════════════════════════════════════════     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 三、各层详解

### L0 — Knowledge Bus（知识总线）

**定位**：横切所有层的知识基础设施。所有产生长期价值的输出必须通过此层结构化沉淀。

**组件**：
| 组件 | 路径 | 说明 |
|------|------|------|
| Knowledge Asset Engine | `.claude/skills/knowledge-asset/SKILL.md` | 引擎入口，schema 校验 + 模板匹配 + 写入 |
| 5 类模板 | `.claude/skills/knowledge-asset/templates/` | sop / troubleshooting / architecture / knowledge-note / project-plan |
| 知识库 | `.claude/skills/knowledge-asset/knowledge/` | 5 子目录，按模板分类存储 |

**核心规则**：
- ✅ 所有 skill 长期产出 → knowledge-asset → `knowledge/`
- ❌ 禁止任何 skill 直接写入 `knowledge/*` 或 `docs/*`
- ❌ 禁止用口头描述代替结构化沉淀

**数据流**：
```
summarize/debug/teach-plus/planning
        ↓
knowledge-asset Engine
  ├── Schema 校验 (9-section)
  ├── 模板匹配 (5 种)
  ├── 元数据提取
  └── 写入 knowledge/{type}/{date}_{title}.md
        ↓
返回 knowledge_asset_ref → state/ 记录引用
```

---

### L1 — Router（路由层）

**定位**：用户输入 → intent 识别 → workflow 匹配 → skill 分发。

**组件**：
| 组件 | 路径 | 说明 |
|------|------|------|
| Prompt Normalizer | `orchestration/prompt_normalizer.py` | 输入规范化、关键词提取 |
| Rule Router | `orchestration/rule_router.py` | 关键词规则匹配（~34 patterns for knowledge-asset） |
| Semantic Router | `orchestration/semantic_router.py` | 语义相似度匹配（降级后备） |
| Skill Index | `.claude/router/skill_index.json` | 技能注册表 |
| Skill Rules | `.claude/skill-rules.json` | 路由规则定义 |
| Synonym Map | `.claude/router/knowledge_asset_synonyms.md` | knowledge-asset 6 组同义词映射 |
| Skill Router Hook | `.claude/hooks/skill-router.py` | hook 入口，注入 skill 指令 |

**路由策略**：
1. Rule Router 命中 → 直接分发（99% 场景）
2. Rule Router 未命中 → Semantic Router → 降级到最高分 skill
3. 意图不明确 → fallback 到 ask skill

---

### L2 — Core Skills（核心基座）

**定位**：三大基础能力 — 知识整理、任务拆解、诊断分析。

| Skill | 路径 | 核心能力 | v5 变化 |
|-------|------|---------|---------|
| `summarize` | `.claude/skills/core/summarize/` | 知识整理、briefing 生成 | 输出强制接入 knowledge-asset |
| `planning` | `.claude/skills/core/planning/` | 任务拆解、执行计划、学习路线 | 可选 knowledge-asset 沉淀 |
| `debug` | `.claude/skills/core/debug/` | 诊断引擎、根因分析、回归清单 | 输出强制接入 knowledge-asset (troubleshooting) |

**协议文件**：
- `summary-protocol.md` / `briefing-protocol.md`
- `plan-protocol.md` / `learning-plan-protocol.md`
- `debug-protocol.md`

---

### L3 — Workflow（工作流控制层）

**定位**：三条正式 pipeline，编排 skill 执行顺序。

| Pipeline | 文件 | 链路 |
|----------|------|------|
| `delivery_pipeline` | `.claude/workflows/delivery_pipeline.md` | summarize → planning → task_ledger → code_assistant → reviewer → changelog → knowledge-asset → execution_guard |
| `debug_pipeline` | `.claude/workflows/debug_pipeline.md` | summarize(可选) → debug → code_assistant → knowledge-asset → execution_guard |
| `learning_pipeline` | `.claude/workflows/learning_pipeline.md` | summarize → planning → teach-plus/explain → teach-plus/practice → task_ledger → learning_state → teach-plus/review → knowledge-asset → execution_guard |

**执行层 Skills**：
| Skill | 说明 | 知识沉淀 |
|-------|------|---------|
| `code_assistant` | 代码编写与修改 | 可选 (architecture) |
| `reviewer` | 代码审查 | 不入沉淀 |
| `changelog` | 变更日志生成 | 不入沉淀 |
| `teach-plus` | 学习工作流控制器 (explain/practice/review) | 强制 (knowledge-note) |
| `task_ledger` | 系统层任务账本 | — |
| `ask` | 需求澄清 | 不入沉淀 |
| `echo` | 原样返回 | 不入沉淀 |

---

### L4 — State（统一状态层）

**定位**：所有运行时状态的单一真实来源（Single Source of Truth）。

**文件结构**：
```
.claude/state/
├── README.md                 # State 系统文档
├── current-task.json         # 当前活跃任务状态
├── learning-state.json       # 学习主题状态
├── execution-state.json      # 系统级执行状态
├── task-history.json         # 已完成任务历史
└── checkpoint/               # 状态快照
```

**v4→v5 迁移**：
| v4 位置 | v5 位置 |
|---------|---------|
| `system/task_ledger/tasks.json` (活跃) | `state/current-task.json` |
| `system/task_ledger/tasks.json` (终态) | `state/task-history.json` |
| `system/learning_state/state.json` | `state/learning-state.json` |
| 无 | `state/execution-state.json` (新建) |
| 无 | `state/checkpoint/` (新建) |

---

### L5 — Execution Guard（执行监督层）

**定位**：强制执行完成约束，防止"口头完成"和非法状态流转。

**7 条规则**：
| # | 规则 | v4/v5 |
|---|------|-------|
| R1 | done 必须带 artifact | v4 保留 |
| R2 | 状态流转必须合法 | v4 保留 |
| R3 | workflow 最小产物检查 | v4 保留，v5 扩展 |
| R4 | 施工任务必须有落地证据 | v4 保留 |
| R5 | 超时未更新处理 | v4 保留，v5 扩展 |
| R6 | **knowledge-asset 强制沉淀** | **v5 新增 (L0)** |
| R7 | **state/ 更新检查** | **v5 新增 (L4)** |

**校验引擎** (`completion-guard.py`)：
```
5 层校验:
  Layer 1: validate_state_transition()     — 状态流转合法性
  Layer 2: check_artifacts()               — 通用 artifact + changed_files
  Layer 3: check_task_type_artifacts()     — 按 task_type 特定检查
  Layer 4: check_knowledge_asset_ref()     — L0 Knowledge Bus 闭环
  Layer 5: check_state_update()            — L4 State 闭环
```

**Hook 文件**：
| Hook | 触发时机 | 职责 |
|------|---------|------|
| `task-guard.py` | 状态变更前 / 会话开始 | stall 检测 + 上下文注入 |
| `completion-guard.py` | 任务 done 前 | 5 层校验 + pass/fail 判定 |
| `skill-router.py` | 用户输入 | intent → workflow → skill |

---

### L6 — Extension（扩展层）

**定位**：多代理编排和自定义代理定义（预留）。

| 组件 | 路径 | 状态 |
|------|------|------|
| Orchestration modules | `orchestration/` | Phase 4 占位 |
| Agent definitions | `agents/` | Phase 4 占位 |

> **当前策略**：单代理优先，不滥用多代理。此层保留为未来扩展。

---

## 四、层间通信

```
User Input
    │
    ▼
[L1 Router] ─── intent + workflow ──→ [L3 Workflow]
    │                                      │
    │                                      ▼
    │                              [L2 Core Skills]
    │                                      │
    │                    ┌─────────────────┼─────────────────┐
    │                    ▼                  ▼                  ▼
    │              summarize           planning             debug
    │                    │                  │                  │
    │                    └──────────────────┼──────────────────┘
    │                                       │
    │                    ┌──────────────────┼──────────────────┐
    │                    ▼                  ▼                  ▼
    │              [L0 Knowledge Bus]  [L4 State]       [L5 Guard]
    │                    │                  │                  │
    │                    │                  │                  │
    │              knowledge/        state/*.json       validation
    │              (长期知识)         (运行时状态)        (强制执行)
    │                                       │
    └───────────────────────────────────────┼──────────────────→ Next Step
                                            │
                                     [L6 Extension]
                                     (预留扩展点)
```

### 关键通信路径

| 路径 | 协议 | 说明 |
|------|------|------|
| L1→L3 | intent→workflow→skill | 路由分发 |
| L2→L0 | knowledge_asset_ref | Core 产出沉淀到 Knowledge Bus |
| L2→L4 | state 写入 | Core 更新 current-task / learning-state |
| L4→L5 | state 读取 + 校验 | Guard 读取 state 执行 7 条规则 |
| L5→L4 | guard_status 回写 | Guard 校验结果写回 execution-state |
| L0→L4 | knowledge_asset_ref | State 记录 knowledge 引用（不持有内容） |
| L5→L3 | validation_result | Guard 结果影响 workflow 推进 |

---

## 五、Skill 目录结构

```
.claude/skills/
├── core/                       # L2 核心基座
│   ├── summarize/              # 知识整理 + briefing
│   │   ├── SKILL.md
│   │   ├── summary-protocol.md
│   │   ├── briefing-protocol.md
│   │   └── modes/
│   ├── planning/               # 任务拆解 + 执行计划
│   │   ├── SKILL.md
│   │   ├── plan-protocol.md
│   │   └── learning-plan-protocol.md
│   └── debug/                  # 诊断引擎
│       ├── SKILL.md
│       ├── debug-protocol.md
│       ├── diagnosis.md
│       └── regression.md
├── knowledge-asset/            # L0 Knowledge Bus
│   ├── SKILL.md                # 引擎入口
│   ├── templates/              # 5 类 9-section 模板
│   │   ├── sop.md
│   │   ├── troubleshooting.md
│   │   ├── architecture.md
│   │   ├── knowledge-note.md
│   │   └── project-plan.md
│   └── knowledge/              # 知识产出目录
│       ├── sop/
│       ├── troubleshooting/
│       ├── architecture/
│       ├── knowledge-notes/
│       └── project-plans/
├── teach-plus/                 # 学习工作流控制器
│   ├── SKILL.md
│   ├── explain.md
│   ├── practice.md
│   └── review.md
├── code_assistant/SKILL.md
├── reviewer/SKILL.md
├── changelog/SKILL.md
├── task_ledger/SKILL.md        # 系统层任务账本
├── ask/SKILL.md
├── echo/SKILL.md
├── sanitize/SKILL.md
└── dify_kb_search/SKILL.md
```

---

## 六、v4 → v5 完整迁移地图

| Layer | v4 组件 | v5 组件 | 变化类型 |
|-------|---------|---------|---------|
| L0 | 无（知识分散） | knowledge-asset Engine | **新建** |
| L0 | `sop` skill (独立) | knowledge-asset sop mode | **删除→合并** |
| L0 | `debug_log` skill (独立) | knowledge-asset troubleshooting mode | **删除→合并** |
| L1 | rule_router (16 patterns) | rule_router (34 patterns) | **扩展** |
| L1 | 无 synonym map | knowledge_asset_synonyms.md | **新建** |
| L2 | summarize → 对话 | summarize → 对话 + knowledge-asset | **改造** |
| L2 | debug → debug_log | debug → knowledge-asset (troubleshooting) | **改造** |
| L2 | planning → 对话 | planning → 对话 + 可选 knowledge-asset | **改造** |
| L3 | 3 pipelines (sop/debug_log stages) | 3 pipelines (knowledge-asset stages) | **更新** |
| L3 | teach-plus → practice/ | teach-plus → knowledge-asset | **改造** |
| L4 | system/task_ledger/ | state/current-task.json + task-history.json | **迁移** |
| L4 | system/learning_state/ | state/learning-state.json | **迁移** |
| L4 | 无 execution-state | state/execution-state.json | **新建** |
| L4 | 无 checkpoint | state/checkpoint/ | **新建** |
| L5 | 5 条规则 (prompt_injection) | 7 条规则 (structured enforcement) | **升级** |
| L5 | completion-guard (占位) | 5-layer validation engine | **升级** |
| L5 | task-guard (legacy) | state/ 三文件 stall 检测 | **升级** |

---

## 七、设计决策记录

| 决策 | 理由 |
|------|------|
| L0 作为横切层而非第 7 层 | Knowledge Bus 是所有层的横切关注点，在物理上属于 skill 目录但在逻辑上横切 L1-L6 |
| state/ 作为单一真实来源 | v4 状态分散在 3 处导致不一致；v5 统一到 `state/` 目录 |
| 保留 legacy 文件而非删除 | v4 文件标记为 legacy 保留，确保向后兼容引用 |
| Hook 输出结构化 JSON + prompt_injection | 同时支持机器解析和人类可读的终端输出 |
| knowledge_asset_ref 按 task_type 分级 | debug/learning 强制，delivery 施工强制/方案推荐，避免过度要求 |

---

## 八、文件索引

### 核心架构文件
| 文件 | 内容 |
|------|------|
| `ARCHITECTURE.md` | 本文件 — 系统架构 |
| `EXECUTION_FLOW.md` | 执行链路与 pipeline 说明 |
| `STATE_SYSTEM.md` | 状态机与 checkpoint |
| `KNOWLEDGE_SYSTEM.md` | 知识系统与 L0 Knowledge Bus |
| `CLAUDE.md` | 仓库操作手册 |
| `README.md` | 项目 README |

### 关键配置
| 文件 | 内容 |
|------|------|
| `.claude/skill-rules.json` | 路由规则（34 patterns for knowledge-asset） |
| `.claude/router/skill_index.json` | 技能注册表 |
| `.claude/router/knowledge_asset_synonyms.md` | 6 组同义词映射 |
| `.claude/router/workflow_templates.json` | workflow 模板 |
| `.claude/settings.json` | hook 注册 |

### 升级文档
| 文件 | 内容 |
|------|------|
| `docs/upgrade/v5_upgrade_state.json` | 升级进度状态 |
| `docs/upgrade/v5_phase2_design.md` | v5 架构设计详情 |
| `docs/upgrade/03_safe_mode_and_rollback.md` | 安全模式与回滚策略 |

# Skill OS v5

**Claude Code 的本地技能操作系统 / 任务操作系统 / 学习工作流操作系统 / 执行监督操作系统 / 知识资产引擎**

在 Claude Code 中输入文字时，Hook 自动分析内容并注入对应技能指令，让 Claude 按预定义规范回答。无需切换模式、无需手动选择技能。

> **当前版本：v5.0.0** — 6+1 层架构完整落地。L0 Knowledge Bus 唯一知识出口 + 统一状态层 + 7 条强制 Guard 规则 + checkpoint 恢复 + 5 层校验引擎。

---

## v5 6+1 层架构

```
┌──────────────────────────────────────────────────────────┐
│  L6 Extension    ← orchestration/ + agents/ (预留)        │
├──────────────────────────────────────────────────────────┤
│  L5 Guard        ← 7 条强制规则 + 5 层校验引擎 + checkpoint│
├──────────────────────────────────────────────────────────┤
│  L4 State        ← .claude/state/ 统一状态层              │
│                    current-task / learning-state           │
│                    execution-state / task-history          │
├──────────────────────────────────────────────────────────┤
│  L3 Workflow     ← 3 pipelines + routing + skill dispatch │
├──────────────────────────────────────────────────────────┤
│  L2 Core         ← summarize / planning / debug           │
├──────────────────────────────────────────────────────────┤
│  L1 Router       ← rule_router + semantic_router          │
│                    + normalizer + workflow_resolver        │
├──────────────────────────────────────────────────────────┤
│  ════════════════════════════════════════════════════     │
│  L0 Knowledge Bus ← knowledge-asset Engine                │
│                     唯一知识出口，横切所有层                │
│  ════════════════════════════════════════════════════     │
└──────────────────────────────────────────────────────────┘
```

---

## v4 → v5 升级演进

| 阶段 | 主题 | 核心交付 | 状态 |
|------|------|---------|------|
| Phase 1-2 | 仓库扫描 + 架构设计 | v5 四模型设计 | ✅ |
| Phase 3 | knowledge-asset 升级 | L0 Knowledge Bus 建立，sop/debug_log 路由收编（本体保留 legacy） | ✅ |
| Phase 4 | 路由系统修复 | knowledge-asset routing 24/24 accuracy | ✅ |
| Phase 5 | Skill 收编 | summarize/debug/teach-plus 强制接入 L0 | ✅ |
| Phase 6 | State System 建立 | .claude/state/ 统一状态层（4 JSON + checkpoint） | ✅ |
| Phase 7 | Execution Guard | 5→7 规则 + 5 层校验引擎 + state/ 集成 | ✅ |
| Phase 8 | 最终系统文档 | ARCHITECTURE / EXECUTION_FLOW / STATE_SYSTEM / KNOWLEDGE_SYSTEM | ✅ |

---

## 工作原理

```text
你在 Claude Code 中输入文字
  ↓
UserPromptSubmit Hook 触发（3 hooks 并行注入）
  │  skill-router.py  → intent → workflow → skill 指令
  │  task-guard.py    → stall 检测 + pipeline 上下文
  │  completion-guard.py → 5 层校验提醒
  ↓
L2 Core Skill 执行
  ↓
L0 Knowledge Bus 结构化沉淀 → knowledge/{type}/
  ↓
L4 State 更新 → state/*.json
  ↓
L5 Guard 校验 → 7 条规则 pass/fail
  ↓
返回用户 + Next Step
```

---

## 3 条正式工作流

### 1. Delivery Pipeline（项目交付链）

```
summarize → planning → task_ledger → code_assistant
    → reviewer → changelog → knowledge-asset → execution_guard
```

### 2. Debug Pipeline（诊断排障链）

```
summarize(可选) → debug → code_assistant → knowledge-asset → execution_guard
```

### 3. Learning Pipeline（学习成长链）

```
summarize → planning → teach-plus/explain → teach-plus/practice
    → task_ledger → learning_state → teach-plus/review
    → knowledge-asset → execution_guard
```

---

## 内置技能（14 主技能 + 2 legacy）

### L2 核心基座

| 技能 | 触发方式 | 作用 |
|------|---------|------|
| `summarize` | `总结`、`摘要`、`读懂这个` | 知识整理与 briefing 生成，强制接入 L0 |
| `planning` | `计划`、`规划`、`方案`、`学习路线` | 任务拆解与执行计划生成，可选接入 L0 |
| `debug` | `报错`、`诊断`、`行为异常`、`排查` | 诊断引擎，强制接入 L0 (troubleshooting) |

### L0 知识出口

| 技能 | 触发方式 | 作用 |
|------|---------|------|
| `knowledge-asset` | `沉淀`、`知识资产`、`SOP`、`故障排查`、`留档` | **L0 Knowledge Bus** — 唯一知识出口，5 类 9-section 模板 |

### 学习控制层

| 技能 | 触发方式 | 作用 |
|------|---------|------|
| `teach-plus` | `我想学`、`今天学什么`、`复盘`、`给我讲` | 学习工作流控制器，强制接入 L0 (knowledge-note) |

### 执行层

| 技能 | 触发方式 | 作用 |
|------|---------|------|
| `ask` | `我想做`、`有个想法` | 需求澄清 |
| `code_assistant` | `代码`、`修复`、`重构`、`帮我写` | 代码编写与修改 |
| `reviewer` | `review`、`代码审查` | 代码审查 |
| `changelog` | `changelog`、`更新日志` | 变更日志生成 |
| `sanitize` | `脱敏`、`消毒`、`sanitize`、`发布` | 敏感字符串脱敏 + 运行态数据隔离 + 一键安全发布（v2） |

### 系统层

| 技能 | 触发方式 | 作用 |
|------|---------|------|
| `task_ledger` | `下一步`、`当前进度`、`任务状态` | 系统层任务账本 |

### 工具层

| 技能 | 触发方式 | 作用 |
|------|---------|------|
| `echo` | `echo xxx` | 原样返回 |
| `dify_kb_search` | `科目一`~`科目四` | 电工知识库检索 |

### Legacy 兼容层

| 技能 | 状态 | 说明 |
|------|------|------|
| `sop` | `status: legacy` | 路由规则已并入 knowledge-asset（sop 模式）；SKILL.md 保留作 fallback |
| `debug_log` | `status: legacy` | 路由规则已并入 knowledge-asset（troubleshooting 模式）；SKILL.md 保留作 fallback |

> **v5 变化**：`sop` 和 `debug_log` 的路由规则已合并入 `knowledge-asset`（sop 模式 / troubleshooting 模式）。两者的 `SKILL.md` 本体保留为 `status: legacy` 兼容层（fallback），不再删除。

---

## v5 系统能力

### L0 Knowledge Bus（唯一知识出口）

- **5 类模板**：SOP / Troubleshooting / Architecture / Knowledge Note / Project Plan
- **9-section 强制 schema**：Core Insight → Tags，7 个必填 section
- **模板自动匹配**：按 skill 类型 + 内容自动选择模板
- **强制闭环**：debug/learning 强制沉淀，delivery 施工类强制
- **禁止绕过**：任何 skill 不得直接写入 `knowledge/*` 或 `docs/*`

### L1 智能路由

- **RuleRouter**：53 knowledge-asset keywords + 16 intentPatterns + 6 组同义词映射
- **SemanticRouter**：Ollama embedding 相似度检索 + 降级保护
- **WorkflowResolver**：rule + semantic 加权融合 → 唯一 RoutePlan
- **SAFE MODE**：embedding 不可用时退化为 rule_only

### L4 统一状态层

- **current-task.json**：活跃任务状态（单一写入者）
- **learning-state.json**：7 阶段学习状态机 + knowledge_assets 关联
- **execution-state.json**：pipeline 进度 + guard_status + safe_mode/degraded 标记
- **task-history.json**：已完成/已取消任务归档索引
- **checkpoint/**：状态快照（stage 完成自动 + 手动 `/checkpoint` + safe_mode 强制）

### L5 Execution Guard（7 条强制规则）

| # | 规则 | 类型 |
|---|------|------|
| R1 | done 必须带 artifact | v4 保留 |
| R2 | 状态流转必须合法 | v4 保留 |
| R3 | workflow 最小产物检查 | v4 保留，v5 扩展 |
| R4 | 施工任务必须有落地证据 | v4 保留 |
| R5 | 超时未更新处理 | v4 保留，v5 扩展 |
| R6 | **knowledge-asset 强制沉淀** | **v5 新增 (L0)** |
| R7 | **state/ 更新检查** | **v5 新增 (L4)** |

**5 层校验引擎**（`completion-guard.py`）：
```
state_transition → artifacts → task_type → L0_ka → L4_state
```

---

## 快速安装

```bash
# 1. 克隆项目
git clone https://github.com/stillness990/skill-os-complete.git

# 2. 进入你的项目目录
cd /path/to/your-project

# 3. 运行安装脚本
bash /path/to/skill-os-complete/install.sh
```

安装完成后自动：复制 `.claude/` → 部署编排模块 → 初始化 `state/` → 运行路由测试

---

## 项目结构（v5.0.0）

```text
skill-os-complete/
├── README.md                                # 本文件
├── CLAUDE.md                                # 仓库操作手册
├── ARCHITECTURE.md                          # ☆ v5 系统架构文档
├── EXECUTION_FLOW.md                        # ☆ v5 执行链路文档
├── STATE_SYSTEM.md                          # ☆ v5 状态系统文档
├── KNOWLEDGE_SYSTEM.md                      # ☆ v5 知识系统文档
├── install.sh                               # 一键安装脚本
├── deploy.sh                                # 一键部署/升级脚本
├── uninstall.sh                             # 一键卸载脚本
├── orchestration/                           # 编排引擎（13 模块）
│   ├── prompt_normalizer.py                 #   输入标准化器
│   ├── rule_router.py                       #   规则路由引擎
│   ├── embedding_provider.py                #   Embedding 服务
│   ├── semantic_router.py                   #   语义路由候选层
│   ├── workflow_resolver.py                 #   多源融合决策器
│   ├── skill_router.py                      #   技能执行器
│   ├── execution_guard.py                   #   执行监督层
│   ├── self_healing.py                      #   自愈管理器
│   ├── safe_mode.py                         #   安全模式管理器
│   ├── rollback_manager.py                  #   回滚管理器
│   └── ...
├── ledger/                                  # 任务账本
├── routing_assets/                          # 路由数据资产
├── tests/                                   # 自动化测试套件
├── docs/                                    # 文档（升级/架构/验证）
│   └── upgrade/                             #   8 phase 升级记录
└── .claude/
    ├── settings.json                        # Hook 注册（3 hooks）
    ├── skill-rules.json                     # 路由规则（53 knowledge-asset keywords）
    ├── hooks/
    │   ├── skill-router.py                  #   L1 路由 hook
    │   ├── task-guard.py                    #   L5 stall 检测 + 上下文注入
    │   └── completion-guard.py              #   L5 5 层校验引擎
    ├── router/                              # 路由配置
    │   ├── skill_index.json                 #   技能注册表
    │   ├── workflow_templates.json          #   3 条 workflow 定义
    │   ├── knowledge_asset_synonyms.md      # ☆ 6 组同义词映射
    │   └── ...
    ├── protocols/                           # 7 个协议文件
    ├── skills/                              # 14 个技能
    │   ├── core/                            #   L2 核心基座
    │   │   ├── summarize/                   #     知识整理
    │   │   ├── planning/                    #     任务拆解
    │   │   └── debug/                       #     诊断引擎
    │   ├── knowledge-asset/                 # ☆ L0 Knowledge Bus
    │   │   ├── SKILL.md                     #     引擎入口
    │   │   ├── README.md                    #     使用说明
    │   │   ├── templates/                   #     5 类 9-section 模板
    │   │   └── knowledge/                   #     知识产出目录（5 子目录）
    │   ├── teach-plus/                      #   学习工作流控制器
    │   ├── ask/                             #   需求澄清
    │   ├── code_assistant/                  #   代码编写
    │   ├── reviewer/                        #   代码审查
    │   ├── changelog/                       #   变更日志
    │   ├── sanitize/                        #   脱敏(字符串+运行态数据隔离+一键发布)
    │   ├── task_ledger/                     #   系统层任务账本
    │   ├── echo/                            #   工具
    │   ├── dify_kb_search/                  #   工具
    │   ├── sop/                             #   legacy 兼容层 (→ knowledge-asset)
    │   └── debug_log/                       #   legacy 兼容层 (→ knowledge-asset)
    ├── workflows/                           # 3 条 workflow 文档
    ├── state/                               # ☆ v5 统一状态层
    │   ├── README.md                        #   State 系统文档
    │   ├── current-task.json                #   活跃任务
    │   ├── learning-state.json              #   学习状态
    │   ├── execution-state.json             #   执行状态
    │   ├── task-history.json                #   任务历史
    │   └── checkpoint/                      #   状态快照
    └── system/                              # 系统文档（legacy + 参考）
        ├── task_ledger/                     #   任务账本 schema
        ├── learning_state/                  #   legacy → state/
        ├── execution_guard/                 #   7 条 guard 规则
        ├── knowledge/                       #   legacy → L0
        └── debug_archive/                   #   诊断归档索引
```

> ☆ = v5 新增/升级

---

## v5 系统文档

| 文档 | 说明 |
|------|------|
| `ARCHITECTURE.md` | v5 6+1 层架构完整参考 — 每层详解、层间通信、v4→v5 迁移地图 |
| `EXECUTION_FLOW.md` | 3 条 pipeline 逐阶段详解 + guard 检查点 + 异常恢复 |
| `STATE_SYSTEM.md` | 状态机（task/learning/pipeline）+ 4 个 state 文件 schema + checkpoint 恢复 |
| `KNOWLEDGE_SYSTEM.md` | L0 Knowledge Bus 架构 + 5 类模板 + 知识流转链路 |

---

## 运行测试

```bash
cd skill-os-complete
for f in tests/test_*.py; do python3 "$f" && echo "PASS: $f" || echo "FAIL: $f"; done
```

---

## 添加新技能

1. 新建 `.claude/skills/<技能名>/SKILL.md`
2. 在 `.claude/skill-rules.json` 的 `skills` 对象里加关键词规则
3. 在 `.claude/router/skill_index.json` 里注册
4. 确定知识沉淀策略（强制/可选/不入）
5. 保存，立刻生效，无需重启

---

## 兼容说明

- `sop` 和 `debug_log` 的路由规则已合并入 `knowledge-asset`（sop/troubleshooting 模式）；`SKILL.md` 本体保留为 `status: legacy` 兼容层作 fallback，不删除
- `planner` / `summarize` / `debug` / `task_manager` 旧目录保留作为 legacy shim
- `system/task_ledger/` 和 `system/learning_state/` 标记 legacy → 状态已迁移至 `state/`
- 推荐所有新引用指向 `skills/core/` 和 `state/`

---

## License

MIT

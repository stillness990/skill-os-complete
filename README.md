# Skill OS v4

**Claude Code 的本地技能操作系统 / 任务操作系统 / 学习工作流操作系统 / 执行监督操作系统**

在 Claude Code 中输入文字时，Hook 自动分析内容并注入对应技能指令，让 Claude 按预定义规范回答。无需切换模式、无需手动选择技能。

> **当前版本：v4.0.0** — 新增 execution_guard 监督层 + learning_state 学习状态追踪。六层架构正式成型。

---

## 工作原理

```text
你在 Claude Code 中输入文字
  ↓
UserPromptSubmit Hook 触发
  ↓
skill-router.py 读取输入 → intent → workflow → primary skill
  ↓
自动注入对应技能规范
  ↓
Claude 按规范回答（无命中则正常对话）
  ↓
execution_guard 检查任务完成质量（v4 新增）
```

---

## 四阶段演进

| 阶段 | 主题 | 核心交付 | 状态 |
|------|------|---------|------|
| **Phase 1** | Core Skill Foundation | summarize / planning / debug 三大基座 + 协议层 + router | ✅ 完成 |
| **Phase 2** | Workflow + Task Ledger + Learning | 三条 workflow 正式落地 + teach-plus 学习控制层 + task_ledger 学习任务 schema | ✅ 完成 |
| **Phase 3** | Execution Guard + Learning State | execution_guard 监督层 + learning_state 学习状态追踪 + teach-plus 正式接入 | ✅ 本轮完成 |
| **Phase 4** | Multi-Agent Orchestration | complexity_detector / orchestrator / agent_definitions | 📋 结构预留 |

---

## 六层架构

```text
┌──────────────────────────────────────────────────┐
│  6. Extension Layer（扩展层）                      │
│     orchestration / agents — Phase 4 预留         │
├──────────────────────────────────────────────────┤
│  5. Guard Layer（监督层）★ v4 新增                 │
│     execution_guard — 状态流转 / artifact / stall │
├──────────────────────────────────────────────────┤
│  4. System Layer（系统状态层）                      │
│     task_ledger / learning_state / knowledge      │
│     debug_archive                                │
├──────────────────────────────────────────────────┤
│  3. Workflow Layer（工作流控制层）                   │
│     delivery_pipeline / debug_pipeline            │
│     learning_pipeline                            │
├──────────────────────────────────────────────────┤
│  2. Core Skills（核心基座技能层）                    │
│     summarize / planning / debug                  │
├──────────────────────────────────────────────────┤
│  1. Router Layer（路由层）                          │
│     hooks / routing_rules / workflow_templates     │
│     skill_index / skill-rules                     │
└──────────────────────────────────────────────────┘
```

---

## 3 条正式工作流

### 1. Delivery Pipeline（项目交付链）

```text
summarize/briefing → planning/project → task_ledger
    → code_assistant → reviewer → changelog
    → execution_guard（完成检查）
```

### 2. Debug Pipeline（诊断排障链）

```text
summarize/briefing（可选）→ debug（诊断引擎）
    → code_assistant（修复）→ debug_log / debug_archive
    → execution_guard（完成检查）
```

### 3. Learning Pipeline（学习成长链）

```text
summarize/briefing（学习底稿）→ planning/learning（学习计划）
    → teach-plus/explain（理解框架）
    → teach-plus/practice（每日学习单）
    → task_ledger → learning_state（状态更新）
    → teach-plus/review（周复盘）
    → execution_guard（完成检查）
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

---

## 内置技能（15 个）

### 核心基座（Core Skills）

| 技能 | 定位 | 触发方式 | 模式 |
|------|------|---------|------|
| `summarize` | 知识整理与 briefing 生成器 | `总结`、`摘要`、`读懂这个`、`分析仓库` | basic / briefing |
| `planning` | 任务拆解与执行计划生成器 | `计划`、`规划`、`方案`、`学习路线` | project / learning |
| `debug` | 诊断引擎 | `报错`、`诊断`、`行为异常`、`排查` | 8 步诊断流程 |

### 学习控制层（Learning Workflow Controller）

| 技能 | 定位 | 触发方式 | 模式 |
|------|------|---------|------|
| `teach-plus` | 学习工作流控制器 | `我想学`、`今天学什么`、`复盘`、`给我讲` | explain / practice / review |

### 执行层

| 技能 | 触发方式 | 作用 |
|------|---------|------|
| `ask` | `我想做`、`有个想法`、`还没想好` | 需求澄清 |
| `code_assistant` | `代码`、`修复`、`重构`、`帮我写` | 代码编写与修复 |
| `sop` | `手册`、`怎么处理`、`SOP` | 生成标准操作手册 |
| `reviewer` | `review`、`代码审查` | 代码质量检查 |
| `changelog` | `changelog`、`更新日志` | 变更日志生成 |
| `sanitize` | `脱敏`、`消毒`、`sanitize` | 敏感信息清理 |
| `knowledge-asset` | `沉淀`、`知识资产`、`知识管理` | 任务/问题/项目 → 结构化知识资产 |

### 系统层

| 技能 | 触发方式 | 作用 |
|------|---------|------|
| `task_ledger` | `下一步`、`当前进度`、`任务状态` | 系统层任务账本 |
| `execution_guard` ★v4 | 自动触发 | 任务完成质量监督 |

### 工具层

| 技能 | 触发方式 | 作用 |
|------|---------|------|
| `echo` | `echo xxx` | 原样返回 |
| `debug_log` | `解决了`、`留档` | 排查记录归档 |
| `dify_kb_search` | `科目一`~`科目四` | 电工知识库检索 |

---

## v4 新增系统能力

### execution_guard（执行监督层）

负责约束任务完成质量，防止"跳步骤完成""空完成""只说不做"：

- **task-state-machine**：8 状态 + 合法流转规则
- **artifact-requirements**：4 种 task_type 的最小产物要求
- **guard-rules**：5 条核心监督规则
- **stall-policy**：超时检测与恢复策略
- **audit-checklist**：人机通用验收清单

详见 `.claude/system/execution_guard/`

### learning_state（学习状态追踪）

让 teach-plus 从"会讲课的技能"升级为"学习系统"：

- **learning-state-schema**：学习主题的状态数据结构
- **learning-state-machine**：7 阶段状态机 + 3 异常状态
- **study-resume-policy**：1~2天/3~5天/7天+/14天+ 四级断档恢复策略

详见 `.claude/system/learning_state/`

---

## teach-plus 的新定位

teach-plus 不再是"独立教学技能"，而是 **Learning Workflow Controller**：

| 模式 | 状态推进 | 输入依赖 |
|------|---------|---------|
| `explain` | topic_new → understanding | summarize 学习底稿 |
| `practice` | understanding → guided_practice / independent_practice | planning 学习计划 + learning_state |
| `review` | consolidation → review_due → mastered | task_ledger 学习记录 + learning_state |

teach-plus 建立在 summarize + planning + task_ledger + learning_state + execution_guard 之上。

---

## 项目结构（v4）

```text
skill-os-complete/
├── CLAUDE.md                               # 仓库操作手册
├── README.md                               # 本文件
├── install.sh                              # 一键安装脚本
├── deploy.sh                               # 一键部署/升级脚本
├── uninstall.sh                            # 一键卸载脚本
├── docs/                                   # 升级/验证/架构文档
│   ├── upgrade/                            #   分阶段升级 runbook
│   ├── validation/                         #   验收 checklist
│   ├── architecture/                       #   架构说明
│   └── failure/                            #   故障恢复方案
├── reports/                                # Phase 1~6 交付报告
├── routing_assets/                         # 路由资产（语义路由/规则路由测试）
├── orchestration/                          # Phase 4+ 编排模块（workflow_resolver/execution_guard/safe_mode/...）
├── ledger/                                 # 任务账本 Python 模块
├── tests/                                  # 自动化测试套件
└── .claude/
    ├── settings.json                       # Hook 注册入口
    ├── skill-rules.json                    # 路由关键词规则
    ├── hooks/
    │   ├── skill-router.py                 # v4 router：intent→workflow→skill
    │   ├── task-guard.py                   # ★ v4 任务状态校验 hook
    │   └── completion-guard.py             # ★ v4 任务完成校验 hook
    ├── router/
    │   ├── skill_index.json                # 技能索引
    │   ├── workflow_templates.json         # 3 条 workflow 定义
    │   ├── routing_rules.py                # 路由规则模块
    │   └── intent_schema.md                # 意图分类协议
    ├── protocols/
    │   ├── summary-protocol.md
    │   ├── briefing-protocol.md
    │   ├── plan-protocol.md
    │   ├── debug-protocol.md
    │   ├── learning-plan-protocol.md
    │   ├── daily-study-protocol.md
    │   └── weekly-review-protocol.md
    ├── skills/
    │   ├── core/
    │   │   ├── summarize/                  # 知识整理与 briefing 生成器
    │   │   ├── planning/                   # 任务拆解与执行计划生成器
    │   │   └── debug/                      # 诊断引擎
    │   ├── teach-plus/                     # 学习工作流控制器
    │   │   ├── SKILL.md
    │   │   ├── explain.md
    │   │   ├── practice.md
    │   │   ├── review.md
    │   │   └── templates/
    │   ├── ask/
    │   ├── code_assistant/
    │   ├── reviewer/
    │   ├── changelog/
    │   ├── sanitize/
    │   ├── knowledge-asset/            # 知识资产系统
    │   ├── sop/
    │   ├── debug_log/
    │   ├── echo/
    │   ├── dify_kb_search/
    │   ├── planner/                        # legacy shim → planning
    │   ├── summarize/                      # legacy shim → core/summarize
    │   ├── debug/                          # legacy shim → core/debug
    │   └── task_manager/                   # legacy shim → task_ledger
    ├── workflows/
    │   ├── delivery_pipeline.md
    │   ├── debug_pipeline.md
    │   └── learning_pipeline.md
    ├── system/
    │   ├── task_ledger/                    # 任务账本（含 v4 扩展状态机）
    │   ├── learning_state/                 # ★ v4 学习状态追踪
    │   ├── execution_guard/                # ★ v4 执行监督层
    │   ├── knowledge/                      # 知识沉淀
    │   └── debug_archive/                  # 诊断归档
    ├── orchestration/                      # ★ v4 Phase 4 扩展占位
    │   ├── README.md
    │   ├── schema/
    │   ├── runs/
    │   └── artifacts/
    └── agents/                             # ★ v4 Phase 4 扩展占位
        └── README.md
```

> ★ = v4 新增

---

## 添加新技能

### 第一步：创建技能定义

```bash
mkdir -p .claude/skills/<新技能名>
```

创建 `.claude/skills/<新技能名>/SKILL.md`，参考现有技能模板。

### 第二步：注册路由规则

在 `.claude/skill-rules.json` 的 `"skills"` 对象中添加关键词规则。

### 第三步：验证

```bash
python3 -c "import json; json.load(open('.claude/skill-rules.json'))"
echo '{"prompt": "你的测试输入"}' \
  | CLAUDE_PROJECT_DIR="$(pwd)" python3 .claude/hooks/skill-router.py
```

**不需要重启 Claude Code，保存文件立即生效。**

---

## 兼容说明

- 旧 `planner` / `summarize` / `debug` / `task_manager` 目录保留，内含 MIGRATION.md
- `task_manager` 作为 `task_ledger` 的兼容 alias，路由规则中仍可触发
- 推荐所有新引用指向 `skills/core/` 下的新版 skill 和 `system/` 下的系统层

---

## License

MIT

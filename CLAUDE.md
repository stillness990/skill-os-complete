# 项目说明

Skill OS v3 — Phase 2。Learning Workflow 正式落地。

## 核心升级（Phase 2）

| 模块 | Phase 1 | Phase 2 | 位置 |
|------|---------|---------|------|
| teach-plus | 单一学习 skill（占位） | 学习控制层（explain/practice/review 三模式） | `.claude/skills/teach-plus/` |
| learning_pipeline | 占位标记 | 7 阶段正式工作流 | `.claude/router/workflow_templates.json` + `.claude/workflows/learning_pipeline.md` |
| learning 协议 | 无 | 3 个协议文件 | `.claude/protocols/learning-plan-protocol.md` 等 |
| task_ledger | 通用任务 schema | 新增学习任务 schema | `.claude/system/task_ledger/learning-task-schema.md` |
| knowledge | 空占位目录 | 3 个学习沉淀子目录 | `.claude/system/knowledge/learning_briefs/` 等 |
| workflows/ | 无独立文档 | 3 个 .md 工作流文档 | `.claude/workflows/` |

## Phase 1 基座（保留）

| 模块 | 状态 | 位置 |
|------|------|------|
| 路由 | intent→workflow→primary/secondary skill（v3） | `.claude/hooks/skill-router.py` + `.claude/router/` |
| summarize | 双模式（basic/briefing）+ 协议 | `.claude/skills/core/summarize/` |
| planning | 双模式（project/learning）+ 协议 | `.claude/skills/core/planning/` |
| debug | 诊断引擎 + 回归规范 + 协议 | `.claude/skills/core/debug/` |
| task_ledger | 系统层任务账本 + 学习任务 schema | `.claude/system/task_ledger/` |

## 工作流（v3 Phase 2）

```
用户输入
    ↓
router 检测 intent
    ├─ project_delivery → delivery_pipeline
    │   summarize/briefing → planning/project → task_ledger → code_assistant → reviewer → changelog
    │
    ├─ debug_issue → debug_pipeline
    │   summarize/briefing(可选) → debug → code_assistant → debug_log
    │
    └─ learn_topic → learning_pipeline  ★ Phase 2 正式版
        ask(可选) → summarize/briefing → planning/learning → teach-plus/explain
        → teach-plus/practice → task_ledger → teach-plus/review
```

## teach-plus 三种模式

| 模式 | 职责 | 触发词示例 |
|------|------|-----------|
| `explain` | 建立理解框架：核心概念、主线、卡点、学习顺序 | "给我讲明白""梳理一下""入门""是什么" |
| `practice` | 每日学习单：步骤、练习、验收、自测 | "今天学什么""练习任务""今日学习单" |
| `review` | 周复盘：完成情况、卡点、下周调整 | "复盘""本周总结""学得怎么样" |

## 目录结构

```
.claude/
├── hooks/
│   └── skill-router.py              # v3 router：intent→workflow→skill
│
├── router/
│   ├── skill_index.json             # 技能索引（含 intent/category/role）
│   ├── workflow_templates.json      # 3 条 workflow 定义（learning_pipeline 非占位）
│   ├── routing_rules.py             # 路由规则模块（含 mode_routing）
│   └── intent_schema.md             # 意图分类协议
│
├── protocols/
│   ├── summary-protocol.md          # basic 摘要输出协议
│   ├── briefing-protocol.md         # 深度底稿输出协议
│   ├── plan-protocol.md             # 计划输出协议
│   ├── debug-protocol.md            # 诊断输出协议
│   ├── learning-plan-protocol.md    # ★ 学习计划协议
│   ├── daily-study-protocol.md      # ★ 每日学习单协议
│   └── weekly-review-protocol.md    # ★ 每周复盘协议
│
├── skills/
│   ├── core/                        # Phase 1 重构的三大基座
│   │   ├── summarize/               # 知识整理中台
│   │   ├── planning/                # 任务拆解引擎
│   │   └── debug/                   # 诊断引擎
│   │
│   ├── teach-plus/                  # ★ Phase 2 重构的学习控制层
│   │   ├── SKILL.md                 # 学习控制层总入口
│   │   ├── explain.md               # explain 模式定义
│   │   ├── practice.md              # practice 模式定义
│   │   ├── review.md                # review 模式定义
│   │   └── templates/               # 学习模板
│   │
│   ├── ask/                         # 需求澄清
│   ├── code_assistant/              # 代码助手
│   ├── reviewer/                    # 代码审查
│   ├── changelog/                   # 变更日志
│   ├── sanitize/                    # 脱敏工具
│   ├── sop/                         # 操作手册
│   ├── debug_log/                   # 排查记录
│   ├── echo/                        # 原样返回
│   ├── dify_kb_search/              # 知识库检索
│   ├── planner/                     # ← 兼容保留
│   ├── summarize/                   # ← 兼容保留
│   ├── debug/                       # ← 兼容保留
│   └── task_manager/                # ← 兼容保留
│
├── workflows/
│   ├── delivery_pipeline.md         # ★ 交付工作流独立文档
│   ├── debug_pipeline.md            # ★ 诊断工作流独立文档
│   └── learning_pipeline.md         # ★ 学习工作流独立文档
│
├── system/
│   ├── task_ledger/                 # 系统层任务账本
│   │   ├── tasks.json
│   │   ├── schema.md                # 通用 schema（已更新 v1.1.0）
│   │   ├── learning-task-schema.md  # ★ 学习任务 schema
│   │   └── task-ops.py
│   ├── debug_archive/               # 诊断归档
│   └── knowledge/                   # ★ Phase 2 正式启用
│       ├── learning_briefs/         # 学习底稿存档
│       ├── study_plans/             # 学习计划存档
│       └── review_logs/             # 复盘记录存档
│
├── settings.json                    # Hook 注册
└── skill-rules.json                 # 路由规则（14技能，teach-plus priority=4）
```

> ★ = Phase 2 新增或重构

## 当前可用技能（14个）

| 技能 | 分类 | 用途 |
|------|------|------|
| `echo` | devtools | 原样返回输入 |
| `ask` | support | 需求澄清 |
| `summarize` | core | 知识整理中台（basic/briefing） |
| `planning` | core | 任务拆解引擎（project/learning） |
| `debug` | core | 诊断引擎 |
| `task_manager` → `task_ledger` | system | 系统层任务账本（含学习任务 schema） |
| `teach-plus` | learning | **学习控制层（explain/practice/review 三模式）** |
| `code_assistant` | execution | 代码编写修复 |
| `reviewer` | execution | 代码审查 |
| `changelog` | execution | 变更日志 |
| `sanitize` | execution | 脱敏处理 |
| `sop` | execution | 操作手册 |
| `debug_log` | execution | 排查记录 |
| `dify_kb_search` | execution | 电工知识库 |

## 学习工作流完整链路（Phase 2）

```
用户说"我想学这个仓库"
    ↓
intent 检测: learn_topic → learning_pipeline → primary: teach-plus
    ↓
step 1 - ask: [目标已明确，跳过]
step 2 - summarize/briefing: 生成学习底稿 → knowledge/learning_briefs/
step 3 - planning/learning: 生成阶段学习计划 → knowledge/study_plans/
step 4 - teach-plus/explain: 建立理解框架（核心概念、主线、卡点）
step 5 - teach-plus/practice: 生成每日学习单 → practice/daily/ + task_ledger
step 6 - task_ledger: 学习任务入账（task_type=learning）
step 7 - teach-plus/review: 一周后生成复盘报告 → practice/reviews/ + knowledge/review_logs/
```

## 兼容说明

- 旧 `planner`/`summarize`/`debug`/`task_manager` 目录保留，内含 MIGRATION.md
- 旧 skill-rules.json 中 planner 条目仍可工作，路由会 fallback
- 推荐新引用指向 `.claude/skills/core/` 下的新版 skill
- `task_ledger` 通过 task_manager 的旧触发词仍可访问（router fallback）

## 验证命令

```bash
# 路由测试
echo '{"prompt": "我想学这个仓库"}' \
  | CLAUDE_PROJECT_DIR="$(pwd)" python3 .claude/hooks/skill-router.py
# 预期：intent=learn_topic, workflow=learning_pipeline, primary=teach-plus

echo '{"prompt": "给我今天的学习任务"}' \
  | CLAUDE_PROJECT_DIR="$(pwd)" python3 .claude/hooks/skill-router.py
# 预期：intent=learn_topic, primary=teach-plus

echo '{"prompt": "帮我复盘这周学的"}' \
  | CLAUDE_PROJECT_DIR="$(pwd)" python3 .claude/hooks/skill-router.py
# 预期：intent=learn_topic, primary=teach-plus
```

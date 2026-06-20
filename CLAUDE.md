# 项目说明

这个项目配置了自动技能路由系统。每次收到消息，hook 自动分析内容并注入对应技能。

## 完整工作流

```
用户模糊想法
    ↓
  ask（需求澄清）
    ↓
summarize（知识整理，产出底稿）
    ↓
planner（生成计划）
    ↓
task_manager（任务追踪）
    ↓
code_assistant / sop（执行）
    ↓
debug（遇到卡点→诊断引擎）
    ↓
reviewer（代码审查）
    ↓
changelog（变更日志）
    ↓
debug_log（排查记录）
```

## 学习工作流

```
summarize（产出学习底稿）
    ↓
planner（拆解学习阶段）
    ↓
teach-plus（每日练习+每周复盘）
```

## 当前可用技能（14个）

| 技能 | 优先级 | 触发词示例 | 作用 |
|------|--------|-----------|------|
| `echo` | 1 | echo、重复、原样 | 原样返回输入，用于调试验证 |
| `ask` | 3 | 我想做、有个想法、还没想好 | 需求澄清，模糊需求优先拦截，先问清楚再规划 |
| `summarize` | 2 | 总结、摘要、读懂这个、分析仓库 | 知识整理层：把任意输入提炼成结构化底稿（项目底稿/学习底稿），供后续技能复用 |
| `planner` | 2 | 计划、规划、方案、学习路线、拆解 | 任务与学习拆解引擎：先澄清再规划，代码任务走 EnterPlanMode，通用任务直接模板输出 |
| `task_manager` | 2 | 下一步、当前进度、任务状态 | 追踪任务执行状态，回答"下一步做什么" |
| `code_assistant` | 3 | 代码、修复、重构、帮我写 | 代码编写与修改，结构化输出 |
| `debug` | 3 | 报错、诊断、行为异常、不知道为什么 | 诊断引擎：现象→最小复现→假设→验证→修复→回归检查 |
| `sop` | 2 | 手册、标准流程、怎么处理 | 生成某类问题的标准操作手册 |
| `debug_log` | 2 | 解决了、留档、排查记录 | debug 结束后自动生成记录文件 |
| `sanitize` | 2 | 脱敏、消毒、sanitize | 扫描并替换项目中的敏感信息，支持一键发布 |
| `reviewer` | 2 | review、代码审查、帮我检查 | 检查代码质量、Bug、安全，只给意见不改代码 |
| `changelog` | 2 | changelog、更新日志、版本说明 | 自动生成标准发布日志 |
| `dify_kb_search` | 5 | 科目一、科目二、科目三、科目四 | 电工知识库检索 |
| `teach-plus` | 3 | 我想学、学会、每日练习、教我 | 学习编排器：底稿→阶段→每日任务→练习→复盘 |

## 技能依赖关系

```
summarize → planner → teach-plus
                ↓ (遇到卡点)
              debug → code_assistant → debug_log
```

## 关键文件

```
.claude/
├── settings.json        注册 hook 入口（不要改）
├── skill-rules.json     路由关键词规则（可加词）
├── hooks/
│   └── skill-router.py  自动路由脚本（不要改）
└── skills/
    ├── ask/SKILL.md             需求澄清
    ├── changelog/SKILL.md       变更日志
    ├── code_assistant/SKILL.md  代码助手
    ├── debug/SKILL.md           诊断引擎
    ├── debug_log/SKILL.md       排查记录
    ├── dify_kb_search/SKILL.md  知识库检索
    ├── echo/SKILL.md
    ├── planner/SKILL.md         任务与学习拆解
    ├── reviewer/SKILL.md        代码审查
    ├── sanitize/
    │   ├── SKILL.md             脱敏技能
    │   └── sanitize.py          脱敏扫描与发布脚本
    ├── sop/SKILL.md             操作手册
    ├── summarize/SKILL.md       知识整理层
    ├── task_manager/SKILL.md    任务追踪
    └── teach-plus/SKILL.md      学习编排器
```

## Planner 技能说明（v2 合并版）

Planner 已与 Claude Code 内置 Plan Mode 合并：
- **代码任务**（涉及代码、文件、项目、配置等）→ 自动调用 `EnterPlanMode` 工具，进入计划模式探索代码库，使用 planner 模板格式化输出，审批后执行
- **通用任务**（学习路线、旅行计划、架构文档等）→ 直接按三档模板（轻量/标准/重量）输出计划，不走 Plan Mode
- 不确定任务类型时会反问用户确认

## Summarize 技能说明（知识整理层）

Summarize 不只是摘要器，而是知识整理层：
- **模式A（项目底稿）**：提炼项目核心模块、工作流、风险点，供 planning/debug 使用
- **模式B（学习底稿）**：提炼核心概念、学习主线、卡点、练习方向，供 teach-plus 使用

## 添加新技能

1. 新建 `.claude/skills/<技能名>/SKILL.md`，按现有文件格式填写
2. 在 `.claude/skill-rules.json` 的 `skills` 对象里加对应关键词规则
3. 保存，立刻生效，无需重启

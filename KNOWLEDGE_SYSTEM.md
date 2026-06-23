# Skill OS v5 — 知识系统

> 版本：v5.0.0 | 生成：2026-06-22 | Phase 8 最终交付

---

## 一、概述

Skill OS v5 的知识系统以 **L0 Knowledge Bus**（knowledge-asset Engine）为核心，是 v5 相对于 v4 最根本的架构升级。所有产生长期价值的输出都必须通过此层进行结构化沉淀，形成可检索、可复用、可追溯的知识资产。

### v4 问题 → v5 解决

| v4 问题 | v5 解决 |
|---------|---------|
| 知识散落在对话/debug-logs/docs/practice 四处 | **单一出口**：knowledge-asset Engine |
| `sop` skill 独立运行，与知识库脱节 | **删除 sop**，成为 knowledge-asset sop mode |
| `debug_log` skill 独立写 debug-logs/ | **删除 debug_log**，成为 knowledge-asset troubleshooting mode |
| summarize/debug/teach-plus 产出不入沉淀 | **强制接入** knowledge-asset |
| 知识无结构、难以检索 | **9-section schema** + **5 类模板** + **元数据** |

---

## 二、L0 Knowledge Bus 架构

```
                    所有技能输出
                         │
                         ▼
              ┌─────────────────────┐
              │  是否长期知识？      │
              │  (SOP/诊断/学习/    │
              │   架构/计划/排障)    │
              └─────────┬───────────┘
                        │
              ┌─────────┴──────────┐
              │ YES                │ NO
              ▼                    ▼
    ┌──────────────────┐    直接对话输出
    │ knowledge-asset   │    (echo/ask/changelog/
    │ Engine            │     code_assistant 即时响应)
    │                   │
    │ 1. Schema 校验    │
    │ 2. 模板匹配       │
    │ 3. 元数据提取     │
    │ 4. 写入 knowledge/│
    │ 5. 返回 ref       │
    └──────┬────────────┘
           │
           ▼
    .claude/skills/knowledge-asset/knowledge/
    ├── sop/              ← SOP 操作手册
    ├── troubleshooting/  ← 诊断排查记录
    ├── architecture/     ← 架构设计文档
    ├── knowledge-notes/  ← 知识笔记
    └── project-plans/    ← 项目计划
```

---

## 三、5 类模板

### 3.1 模板总览

| 模板 | 文件 | 适用场景 | 9-section |
|------|------|---------|-----------|
| SOP | `templates/sop.md` | 标准操作流程、重复性任务 | ✅ |
| Troubleshooting | `templates/troubleshooting.md` | 故障排查、诊断记录 | ✅ |
| Architecture | `templates/architecture.md` | 系统架构、设计决策 | ✅ |
| Knowledge Note | `templates/knowledge-note.md` | 学习笔记、知识点 | ✅ |
| Project Plan | `templates/project-plan.md` | 项目计划、阶段拆解 | ✅ |

### 3.2 9-Section Schema（所有模板通用）

```
1. 标题 + 元数据        — 标题、日期、版本、作者、标签
2. 概述 / TL;DR         — 一句话总结
3. 背景 / 上下文        — 为什么需要、产生背景
4. 核心内容             — 主要知识/流程/分析
5. 关键决策 / 要点      — 决策记录、关键发现
6. 依赖 / 前置条件      — 依赖项、前置知识
7. 产出 / 结果          — 具体产出物、成果
8. 下一步 / 行动计划     — 后续步骤
9. 参考 / 关联          — 相关文档、外部链接
```

### 3.3 模板匹配逻辑

```
knowledge-asset Engine 匹配规则:

输入: skill 类型 + 产出内容
  │
  ├── skill=debug + 诊断报告
  │   └── 模板: troubleshooting → knowledge/troubleshooting/
  │
  ├── skill=teach-plus + 学习内容
  │   └── 模板: knowledge-note → knowledge/knowledge-notes/
  │
  ├── skill=summarize + briefing (架构类)
  │   └── 模板: architecture → knowledge/architecture/
  │
  ├── skill=summarize + briefing (通用)
  │   └── 模板: knowledge-note → knowledge/knowledge-notes/
  │
  ├── skill=planning + 项目计划
  │   └── 模板: project-plan → knowledge/project-plans/
  │
  ├── 用户请求 SOP
  │   └── 模板: sop → knowledge/sop/
  │
  └── 代码重大架构变更
      └── 模板: architecture → knowledge/architecture/
```

---

## 四、Skill → Knowledge 映射

### 4.1 强制沉淀

| Skill | 触发条件 | 模板 | 写入路径 | Guard 检查 |
|-------|---------|------|---------|-----------|
| `debug` | 诊断完成 | `troubleshooting` | `knowledge/troubleshooting/` | ✅ 强制 |
| `teach-plus/explain` | 概念讲解完成 | `knowledge-note` | `knowledge/knowledge-notes/` | ✅ 强制 |
| `teach-plus/practice` | 练习完成 | `knowledge-note` | `knowledge/knowledge-notes/` | ✅ 强制 |
| `teach-plus/review` | 复盘完成 | `knowledge-note` | `knowledge/knowledge-notes/` | ✅ 强制 |
| `summarize` (briefing) | briefing 完成 | `knowledge-note` / `architecture` | `knowledge/knowledge-notes/` 或 `knowledge/architecture/` | ✅ 强制 |

### 4.2 可选/推荐沉淀

| Skill | 触发条件 | 模板 | 写入路径 | Guard 检查 |
|-------|---------|------|---------|-----------|
| `planning` | 用户确认计划后 | `project-plan` | `knowledge/project-plans/` | 推荐 |
| `code_assistant` | 重大架构变更 | `architecture` | `knowledge/architecture/` | 可选 |
| `summarize` (basic) | 基础总结 | `knowledge-note` | `knowledge/knowledge-notes/` | 可选 |

### 4.3 不入沉淀

| Skill | 原因 |
|-------|------|
| `echo` | 纯回显，无知识产出 |
| `ask` | 需求澄清，临时对话 |
| `reviewer` | 代码审查意见，即时反馈 |
| `changelog` | 变更日志，由 delivery pipeline 统一沉淀 |
| `task_ledger` | 任务记录，属于 state 层 |
| `sanitize` | 脱敏操作，按需使用 |
| `dify_kb_search` | 外部知识库检索，即时查询 |

---

## 五、知识流转完整链路

### 5.1 单次知识沉淀流程

```
Step 1: Skill 执行完成
    │  summarize/debug/teach-plus/planning 产出结果
    │
    ▼
Step 2: 判断是否长期知识
    │  检查 skill 类型 + 产出性质
    │  YES → 进入 knowledge-asset
    │  NO  → 直接对话输出
    │
    ▼
Step 3: knowledge-asset Engine
    ├── 3a. Schema 校验: 检查是否符合 9-section
    ├── 3b. 模板匹配: 按 skill+内容 选择模板
    ├── 3c. 元数据提取: 日期/标签/版本/关联
    ├── 3d. 文件生成: 写入 knowledge/{type}/{date}_{title}.md
    └── 3e. 返回 ref: knowledge_asset_ref
    │
    ▼
Step 4: State 记录引用
    │  current-task.json → outputs.knowledge_asset_ref
    │  learning-state.json → topics[].knowledge_assets[]
    │
    ▼
Step 5: Guard 验证
    │  completion-guard.py Layer 4: 验证 knowledge_asset_ref
    │  强制类型: 非空 + 文件存在
    │  推荐类型: bonus 记录
    │
    ▼
Step 6: 知识可检索
    │  knowledge/ 目录下的 markdown 文件
    │  按模板分类 + 日期标题命名 + 9-section 结构
```

### 5.2 知识检索

```
knowledge/
├── sop/                    ← ls knowledge/sop/
├── troubleshooting/        ← ls knowledge/troubleshooting/
├── architecture/           ← ls knowledge/architecture/
├── knowledge-notes/        ← ls knowledge/knowledge-notes/
└── project-plans/          ← ls knowledge/project-plans/

检索方式:
  - 按目录浏览 (模板分类)
  - 按日期排序 (文件名前缀 YYYY-MM-DD)
  - 按标题搜索 (9-section 元数据)
  - 按标签过滤 (template metadata)
```

---

## 六、v4 → v5 知识迁移

### 6.1 已迁移

| v4 产出位置 | v5 产出位置 | 状态 |
|------------|------------|------|
| `sop` skill 独立输出 | knowledge-asset sop mode → `knowledge/sop/` | ✅ 已迁移 |
| `debug_log` skill → `debug-logs/` | knowledge-asset troubleshooting mode → `knowledge/troubleshooting/` | ✅ 已迁移 |
| `system/knowledge/` (部分) | `knowledge/` (knowledge-asset 管理) | ✅ 已迁移 |
| 对话中的诊断记录 | `knowledge/troubleshooting/` | ✅ 流程改造 |

### 6.2 保留为 legacy

| v4 位置 | 保留原因 |
|---------|---------|
| `system/knowledge/README.md` | 指向 v5 knowledge/ 的说明 |
| `system/debug_archive/README.md` | 指向 knowledge/troubleshooting/ 的索引 |
| `system/task_ledger/` | Schema 文档 + task-ops.py 工具 |
| `system/learning_state/` | 状态机文档 + 策略文档 |

### 6.3 已删除

| v4 组件 | 删除原因 |
|---------|---------|
| `sop` skill (`skills/sop/SKILL.md`) | 功能收编入 knowledge-asset sop mode |
| `debug_log` skill (`skills/debug_log/SKILL.md`) | 功能收编入 knowledge-asset troubleshooting mode |
| 直接写入 `docs/*` 的实践 | 统一通过 knowledge-asset |

---

## 七、禁止项（强制规则）

| ❌ 禁止行为 | 说明 | Guard 检查 |
|-----------|------|-----------|
| 任何 skill 直接写 `knowledge/*` | 必须通过 knowledge-asset Engine | Layer 4 |
| 任何 skill 直接写 `docs/*` | 必须通过 knowledge-asset Engine | Layer 4 |
| `sop` skill 独立调用 | 已删除，使用 knowledge-asset sop mode | Router 层面 |
| `debug_log` skill 独立调用 | 已删除，使用 knowledge-asset troubleshooting mode | Router 层面 |
| 口头描述代替结构化沉淀 | 诊断/学习/计划必须有结构化文档 | Layer 4 |
| 绕过 9-section schema | 所有 knowledge 产出必须符合 9-section | knowledge-asset Engine |

---

## 八、模板自定义

### 8.1 添加新模板

1. 在 `templates/` 下创建新模板文件
2. 遵循 9-section 结构
3. 在 `knowledge/` 下创建对应子目录
4. 更新 `knowledge-asset/SKILL.md` 中的模板匹配规则

### 8.2 扩展 9-Section

9-section 是基线要求。模板可以在此基础上增加特定 section，但不能减少核心 9 个。

---

## 九、与 State 层的关系

```
knowledge-asset (L0)           state/ (L4)
─────────────────────          ────────────
产生知识内容                    只记录引用
写入 knowledge/*.md            写入 knowledge_asset_ref
持有知识                       持有指针
长期不变                       随任务推进更新
可独立检索                     与任务生命周期绑定
```

**核心原则**：L0 持有内容，L4 持有引用。两者不重叠。

---

## 十、文件索引

| 文件 | 内容 |
|------|------|
| `.claude/skills/knowledge-asset/SKILL.md` | Knowledge Asset Engine 入口 |
| `.claude/skills/knowledge-asset/templates/` | 5 类 9-section 模板 |
| `.claude/skills/knowledge-asset/knowledge/` | 知识库根目录（5 子目录） |
| `.claude/router/knowledge_asset_synonyms.md` | 6 组同义词映射 |
| `.claude/system/knowledge/README.md` | Legacy knowledge 说明 |
| `.claude/system/debug_archive/README.md` | 诊断归档索引 |
| `KNOWLEDGE_SYSTEM.md` | 本文件 |

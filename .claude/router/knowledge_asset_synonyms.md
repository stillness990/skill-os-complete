# Knowledge-Asset Synonym Map

> v5.0.0 — 路由 synonym 参考文件
> 关联: `.claude/skill-rules.json` → knowledge-asset entry

## 说明

此文件记录了 knowledge-asset 所有触发词的 synonym 映射关系。
路由系统通过 `skill-rules.json` 中的 keywords 和 intentPatterns 进行匹配，
本文件用于人工维护 synonym 覆盖的完整性。

## Synonym 分组

### Group 1: 知识沉淀（Knowledge Deposition）

| 主词 | Synonyms |
|------|---------|
| 沉淀知识 | 知识沉淀, 知识资产, 结构化输出, 知识库 |
| 归档 | 留档, 保存记录, 记录归档 |

### Group 2: SOP（Standard Operating Procedure）

| 主词 | Synonyms |
|------|---------|
| SOP | sop, 标准流程, 操作手册, 规范, 流程文档, runbook |
| 生成SOP | 写SOP, 生成操作手册, 写操作手册, 做操作手册, 生成runbook, 整理成SOP, 生成标准操作流程 |

### Group 3: Troubleshooting（故障排查）

| 主词 | Synonyms |
|------|---------|
| 故障排查文档 | 排查记录, debug记录, 故障排查, 排查留档 |
| 问题解决记录 | 问题已解决, 解决了, 做排查记录, 保存debug记录 |

### Group 4: Architecture（架构文档）

| 主词 | Synonyms |
|------|---------|
| 生成架构文档 | 写架构文档, 做架构设计文档 |

### Group 5: Knowledge Note（知识笔记）

| 主词 | Synonyms |
|------|---------|
| 整理笔记 | 学习笔记, 知识笔记, 整理学习笔记 |

### Group 6: Project Plan（项目计划）

| 主词 | Synonyms |
|------|---------|
| 项目计划文档 | 写项目计划, 生成项目计划 |

## 覆盖状态

| Group | Keywords | Patterns | 覆盖率 |
|-------|---------|---------|--------|
| 知识沉淀 | ✅ 6 | ✅ 2 | 100% |
| SOP | ✅ 14 | ✅ 1 | 100% |
| Troubleshooting | ✅ 7 | ✅ 3 | 100% |
| Architecture | ✅ 1 | ✅ 1 | 100% |
| Knowledge Note | ✅ 2 | ✅ 1 | 100% |
| Project Plan | ✅ 1 | ✅ 1 | 100% |

## 上游 Skill 触发 Synonyms（间接调用）

这些不通过路由触发，而是上游 skill 完成后调用 knowledge-asset：

| 上游 Skill | knowledge-asset 模式 | 触发时机 |
|-----------|---------------------|---------|
| summarize/briefing | knowledge-note / architecture | briefing 完成后 |
| debug | troubleshooting | 诊断完成后 |
| teach-plus | knowledge-note | explain/practice/review 完成后 |
| planning | project-plan | 用户确认计划后（可选） |

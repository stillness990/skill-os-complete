# Knowledge（知识库）— v4 legacy

> **v5 注意**：知识产出已统一通过 L0 Knowledge Bus（`.claude/skills/knowledge-asset/knowledge/`）沉淀。状态管理已迁移至 `.claude/state/`。本目录保留为 v4 参考。

系统层知识存储目录。Phase 2 正式启用。

## 子目录

| 目录 | 用途 | 写入者 | 读取者 |
|------|------|--------|--------|
| `learning_briefs/` | 存放 summarize 产出的学习底稿 | summarize/briefing | teach-plus/explain, planning/learning |
| `study_plans/` | 存放 planning/learning 或 teach-plus 输出的阶段学习计划 | planning/learning, teach-plus | teach-plus/practice, teach-plus/review |
| `review_logs/` | 存放 teach-plus/review 产出的每周复盘 | teach-plus/review | teach-plus（后续复盘对比） |

## 与 practice/ 目录的关系

```
knowledge/                        ← 正式知识沉淀（结构化、可复用）
  ├── learning_briefs/            ← 学习底稿
  ├── study_plans/                ← 阶段计划
  └── review_logs/                ← 复盘记录

practice/                         ← 学习工作区（日常操作）
  ├── plans/                      ← 学习计划工作副本
  ├── daily/                      ← 每日学习单
  └── reviews/                    ← 每周复盘工作副本
```

`practice/` 是日常操作的轻量工作区，`knowledge/` 是长期沉淀的结构化知识库。

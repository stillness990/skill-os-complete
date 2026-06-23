# Debug Archive（诊断归档）— v5

## 定位

系统层诊断记录归档目录。`debug` 技能诊断 + `code_assistant` 修复完成后，将排查记录归档到此。

## 与 knowledge-asset 的关系

- **v5 起，结构化排查记录统一由 `knowledge-asset`（troubleshooting 模式）沉淀**
- 沉淀路径：`.claude/skills/knowledge-asset/knowledge/troubleshooting/`
- 旧 `debug_log` skill 已删除（v5），功能合并入 `knowledge-asset`
- `debug_archive/` 保留作为系统层索引目录，指向 knowledge-asset 的 troubleshooting 产出
- 执行状态追踪见 `.claude/state/execution-state.json`
- 任务进度见 `.claude/state/current-task.json`

## 归档格式

待后续版本定义。Phase 1 保留此目录作为系统层占位。

## 目录结构（计划）

```
debug_archive/
├── README.md
├── YYYY-MM-DD_问题关键词.md   ← 单次排查记录（可选摘要）
└── index.md                    ← 归档索引 → 指向 knowledge/troubleshooting/
```

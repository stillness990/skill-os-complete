# Debug Archive（诊断归档）

## 定位

系统层诊断记录归档目录。`debug` 技能诊断 + `code_assistant` 修复完成后，将排查记录归档到此。

## 与 debug_log 的关系

- `debug_log` （`.claude/skills/debug_log/`）是旧版归档方式，由 debug_log skill 主动调用
- `debug_archive` 是系统层归档，Phase 1 做最小占位
- Phase 2+ 中将 debug_log 的输出统一指向此目录

## 归档格式

待后续版本定义。Phase 1 保留此目录作为系统层占位。

## 目录结构（计划）

```
debug_archive/
├── README.md
├── YYYY-MM-DD_问题关键词.md   ← 单次排查记录
└── index.md                    ← 归档索引（Phase 2+）
```

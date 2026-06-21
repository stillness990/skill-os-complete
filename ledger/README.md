# Ledger Module

> Skill OS Workflow OS 账本模块
> Phase 1 骨架建立 — Phase 2 起逐步实现

## 目录结构

```
ledger/
├── README.md              # 本文件
├── ledger_schema.py       # [Phase 2] Python schema 定义
├── ledger_api.py          # [Phase 2] 可编程查询接口
└── task_ledger.py         # [Phase 2] 主模块（CRUD + 状态转移）
```

## 与现有 task_ledger 的关系

此 `ledger/` 目录是**新增的程序化接口层**，提供 Python API 供其他模块调用。
现有 `.claude/system/task_ledger/` 保留为数据存储和文档层。

- `ledger/ledger_api.py` → 读取/写入 `.claude/system/task_ledger/tasks.json`
- `ledger/task_ledger.py` → 取代/增强 `.claude/system/task_ledger/task-ops.py` 的功能
- `ledger/ledger_schema.py` → Python 版 schema 定义（与 `.claude/system/task_ledger/schema.md` 保持一致）

## Phase 填充计划

| Phase | 新建文件 |
|-------|---------|
| Phase 2 | ledger_schema.py, ledger_api.py, task_ledger.py |
| Phase 5 | 接入 guard + healing + rollback 的读写路径 |

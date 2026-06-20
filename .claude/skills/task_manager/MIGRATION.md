# Task Manager → Task Ledger 迁移说明

**旧版 `task_manager`**（本目录）→ **新版 `task_ledger`** `.claude/system/task_ledger/`

## 变化

| 方面 | 旧版 task_manager | 新版 task_ledger |
|------|------------------|------------------|
| 定位 | 普通 skill | 系统层组件 |
| 位置 | `.claude/skills/task_manager/` | `.claude/system/task_ledger/` |
| 数据存储 | `task.json`（根目录） | `tasks.json`（系统层目录） |
| 数据结构 | phases-based 嵌套结构 | 扁平 task 列表 |
| 操作方式 | 自然语言触发 | CLI 脚本 + 自然语言 |
| 状态集合 | done/in_progress/pending | queued/in_progress/blocked/done/retry |

## 状态映射

| 旧版 | 新版 |
|------|------|
| `pending` | `queued` |
| `in_progress` | `in_progress` |
| `done` | `done` |
| （无） | `blocked`（新增） |
| （无） | `retry`（新增） |

## 兼容性

- 旧版 SKILL.md 保留
- 旧 task_manager 的触发词（"下一步"、"当前进度"等）保留在 skill-rules.json 中
- 在 router 升级后，task_manager 触发词将指向 task_ledger 系统层

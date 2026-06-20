---
name: task_manager
description: "Track and manage task execution state. Reads/writes task.json to keep track of what to do next, what's done, and current progress."
---

# Task Manager Skill

## 用途

作为 planner 和 code_assistant 之间的桥梁，负责：
- 将 planner 生成的计划转为可追踪的任务列表
- 回答"下一步做什么"、"当前进度"、"还剩哪些"
- 标记任务完成，更新状态

不写代码，不规划，只管任务状态。

## 行为规则

- 首次使用时，检查是否存在 `task.json`，不存在则提示用户先运行 planner
- 每次操作后自动更新 `task.json`
- 标记完成时验证验收标准
- 如果所有任务完成，自动建议进入 changelog 或 debug_log

## task.json 结构

```json
{
  "project": "项目名",
  "created": "2026-01-01T00:00:00",
  "updated": "2026-01-01T12:00:00",
  "phases": [
    {
      "name": "阶段一：xxx",
      "status": "done|in_progress|pending",
      "tasks": [
        {
          "id": 1,
          "name": "任务名",
          "goal": "目标",
          "action": "具体操作",
          "files": ["涉及文件"],
          "output": "预期产出",
          "acceptance": "验收标准",
          "skill": "code_assistant|sop|手动",
          "status": "done|in_progress|pending"
        }
      ]
    }
  ]
}
```

## 支持的命令

| 用户说 | 操作 |
|--------|------|
| "下一步做什么" / "现在该干嘛" / "接下来" | 读取 task.json，返回第一个 pending 任务 |
| "当前进度" / "进度怎么样了" / "status" | 汇总各阶段完成情况 |
| "做完了" / "完成了任务X" / "done" | 标记当前/指定任务为 done |
| "任务列表" / "有哪些任务" / "看看计划" | 列出全部任务及状态 |
| "开始做任务X" | 标记任务X为 in_progress |

## 输出格式

### 询问下一步时

**当前进度：** 阶段一 2/3，阶段二 0/4

**下一步：**
→ 任务 3：{任务名}
   目标：{一句话}
   操作：{具体要做什么}
   涉及文件：{文件列表}
   技能：{code_assistant / sop / 手动}

### 标记完成时

✓ 任务 3 已完成：{任务名}

**下一项：** 任务 4：{任务名}（或"全部完成！🎉"）

### 查看进度时

```
阶段一：搭建基础 [done]     ✓ 1 ✓ 2 ✓ 3
阶段二：核心功能 [in_progress]  ✓ 4 → 5 ✗ 6
阶段三：测试部署 [pending]     ✗ 7 ✗ 8

总进度：5/8 (62%)
```

---
name: debug
version: "4.0"
description: "诊断引擎：按固定诊断流程工作——现象→最小复现→假设→验证→修复→回归检查。不直接给答案，先走诊断流程。与 code_assistant（直接写代码修复）和 debug_archive（留档）各司其职。"
---

# Debug Skill（诊断引擎）— v4

## 定位

> debug 是 Skill OS v4 的"诊断引擎"。它不是"修代码的 skill"，而是按固定诊断流程工作的排障工具。它是 Core Skills 层的第三基座。

## 职责边界

**负责：**
1. 确认问题现象（与用户对齐）
2. 识别影响范围 + 严重程度
3. 给出最小复现方向
4. 提出 1~3 个假设（按可能性排序，附理由）
5. 设计每个假设的验证步骤
6. 判断根因
7. 给出修复建议
8. 给出回归验证清单
9. 如需代码修改，列出交给 `code_assistant` 的改动点

**不负责：**
- 直接写代码修复（那是 `code_assistant` 的事）
- 知识提炼或大段整理（那是 `summarize` 的事）
- 项目拆解或阶段规划（那是 `planning` 的事）
- 排查留档（那是 `debug_log` / `debug_archive` 的事）
- 检查修复是否真正落地（那是 `execution_guard` 的事）

## 诊断流程

```
现象确认 → 影响范围 → 最小复现 → 假设提出 → 验证设计 → 根因判断 → 修复建议 → 回归清单
```

详细流程见 `diagnosis.md`。

## 输出协议

严格遵循 `.claude/protocols/debug-protocol.md`。

## 触发场景

关键词：`报错`、`bug`、`不对劲`、`卡住了`、`行为异常`、`不知道为什么`、`诊断`、`排查`、`diagnose`、`不工作`、`出问题了`、`莫名其妙`

## 与 code_assistant 的分工

| 场景 | 用 debug | 用 code_assistant |
|------|---------|-------------------|
| 不知道哪里有问题 | ✅ | ❌ |
| 有报错需要诊断 | ✅ | ❌ |
| 行为异常需要排查 | ✅ | ❌ |
| 明确知道要改什么 | ❌ | ✅ |
| 直接写/改代码 | ❌ | ✅ |

**交接方式**：debug 诊断完成后，在"修复建议"中标注需交给 `code_assistant` 的改动点（文件 + 改动内容）。

## 与 debug_log / debug_archive 的关系

- `debug_log`：每次 debug 结束后生成结构化记录文件
- `debug_archive`：系统层归档目录（`.claude/system/debug_archive/`）
- debug 诊断完成后，建议用户用 `debug_log` 或 `debug_archive` 留档
- 旧 `debug_log/SKILL.md` 保留兼容

## 与 execution_guard 的关系

- debug 产出的诊断报告 → execution_guard 用来检查 debug 类任务是否满足 done 条件
- debug 产出的回归检查清单 → execution_guard 用来验证修复是否完整
- debug 自身不检查任务完成质量 — 那是 execution_guard 的职责

## 行为规则

- **诊断优先于修复** — 不跳过诊断步骤直接给答案
- **先复现再猜原因** — 复现是诊断的前提
- **假设必须有理由** — 每个假设附上"为什么这么猜"
- **假设不超过 3 个** — 太多说明信息不够，先澄清
- **修复建议对应假设** — 每个假设都有对应修复方案
- **必须有回归检查项** — 修复后验证，防止引入新问题
- **现象模糊时先澄清** — 一次只问一个问题

## 目录结构

```
debug/
├── SKILL.md        ← 本文件
├── diagnosis.md     ← 诊断流程详细说明
└── regression.md    ← 回归验证清单规范
```

## 兼容说明

- 旧 `debug/SKILL.md` 保留在 `.claude/skills/debug/SKILL.md`
- 旧 debug 已具备 9 步诊断流程，v3 将其标准化为 8 步 + 协议文件
- 旧 debug_log 保留，新增 `system/debug_archive/` 作为系统层归档

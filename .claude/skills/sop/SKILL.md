---
name: sop
description: "Generate a standard operating procedure for handling a specific type of problem. Use when user asks how to handle/deal with a recurring issue type."
status: legacy
layer: compatibility
---

# SOP Skill

> **Legacy compatibility only.**
> This skill is not the primary v5 knowledge sink.
> For new v5 workflows, use `knowledge-asset` (SOP mode) as the primary long-term knowledge output.
> 本 skill 保留仅用于历史兼容和 fallback 场景，v5 中 SOP 产出统一由 knowledge-asset 的 sop 模板承接。

## 用途
针对某一类反复出现的问题，生成一份标准操作手册（SOP）。
让任何人拿到这份手册，都能按步骤独立解决同类问题。

## 行为规则
- 步骤必须具体可执行，不写"检查配置"这种废话，要写"打开 xxx 文件，找到 xxx 字段，确认值为 xxx"
- 每个步骤后写：做完这步你应该看到什么（预期结果）
- 写明分支判断：什么情况下跳到哪一步
- 最后写常见错误和对应处理方法
- 语言简单直白，不用专业术语

## 输出格式

# SOP：{问题类型}

**适用场景：** 什么时候用这份手册

**前置条件：** 开始之前需要准备什么

---

## 步骤

### 第一步：{步骤名}
操作：具体做什么，具体需要输入什么
预期：做完后你会看到 / 得到什么
如果不对：跳到第X步 / 检查XXX

### 第二步：{步骤名}
操作：…
预期：…

（依此类推，通常 4～8 步）

---

## 常见错误

| 错误现象 | 原因 | 处理方法 |
|----------|------|----------|
| … | … | … |

---

**最后验证：** 全部完成后，做这件事确认问题已解决

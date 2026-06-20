---
name: debug_log
description: "After debugging, automatically generate a structured debug record and save it as a markdown file. Use when user says debug is done, issue resolved, or asks to log/record the debug session."
---

# Debug Log Skill

## 用途
每次 debug 结束后，把这次排查过程整理成结构化记录，存成 markdown 文件留档。
日后遇到同类问题，直接翻记录，不用重新排查。

## 行为规则
- 根据对话内容还原完整排查过程，不需要用户再重复描述
- 文件名格式：`debug-logs/YYYY-MM-DD_{问题关键词}.md`
- 如果 debug-logs 目录不存在，先用 Bash 工具创建
- 用 Write 工具把内容写入文件
- 写完后告诉用户文件保存在哪里
- 语言简洁，给未来的自己看，不废话

## 输出（写入文件的内容）

# Debug 记录：{问题一句话描述}

**时间：** YYYY-MM-DD HH:MM
**环境：** {语言/框架/系统，从对话中提取}
**严重程度：** 低 / 中 / 高

---

## 问题现象

用户看到了什么报错或异常行为

## 排查过程

1. 首先检查了 xxx → 结果：xxx
2. 然后发现 xxx → 说明 xxx
3. 定位到根本原因：xxx

## 根本原因

一句话说清楚为什么会出现这个问题

## 解决方案

具体改了什么，改动前 vs 改动后

```语言
// 修复前
…

// 修复后
…
```

## 验证结果

怎么确认问题解决了

## 经验总结

下次遇到类似问题，第一步应该看什么 / 注意什么

---
*由 Claude Code debug_log 技能自动生成*

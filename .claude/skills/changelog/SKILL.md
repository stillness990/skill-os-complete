---
name: changelog
description: "Generate changelog from conversation or git diff."
---

# Changelog Skill

## 用途

根据对话内容、任务记录或 git diff 生成标准发布日志。

## 行为规则

- 按 Added / Changed / Fixed 分类
- 语言简洁，面向发布用户
- 不记录无意义的修改（格式化、注释调整等）
- 如果没有足够信息，先询问再看 diff

## 输出格式

# Changelog

## Added

- xxx
- xxx

## Changed

- xxx
- xxx

## Fixed

- xxx
- xxx

## Notes

- xxx

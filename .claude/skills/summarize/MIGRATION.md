# Summarize 迁移说明

**旧版**（本目录）→ **新版** `.claude/skills/core/summarize/`

## 变化

| 方面 | 旧版 | 新版 |
|------|------|------|
| 位置 | `.claude/skills/summarize/` | `.claude/skills/core/summarize/` |
| 模式定义 | 全部在 SKILL.md 中 | 拆分到 `modes/basic.md` + `modes/briefing.md` |
| 输出协议 | 嵌在 SKILL.md 中的模板 | 独立协议文件 `protocols/summary-protocol.md` + `protocols/briefing-protocol.md` |
| 下游连接 | 文字描述 | 明确 workflow 推荐 + primary/secondary skill |

## 兼容性

- 旧版 SKILL.md 保留，路由规则不变
- 如果旧路由仍命中 `summarize`，本目录内容仍可工作
- 建议新引用指向 `.claude/skills/core/summarize/`

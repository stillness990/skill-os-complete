# Debug 迁移说明

**旧版**（本目录）→ **新版** `.claude/skills/core/debug/`

## 变化

| 方面 | 旧版 | 新版 |
|------|------|------|
| 位置 | `.claude/skills/debug/` | `.claude/skills/core/debug/` |
| 诊断流程 | 9 步（嵌在 SKILL.md） | 8 步标准化（独立 `diagnosis.md`） |
| 输出协议 | 嵌在 SKILL.md 中的模板 | 独立 `protocols/debug-protocol.md` |
| 回归验证 | 在输出模板中简单提及 | 独立 `regression.md` |
| 与 code_assistant 边界 | 文字描述 | 明确交接方式（改动点列表） |

## 兼容性

- 旧版 SKILL.md 保留
- 旧 debug_log 保留在 `.claude/skills/debug_log/`
- 新增 `system/debug_archive/` 作为系统层归档目录

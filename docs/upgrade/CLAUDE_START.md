# CLAUDE START — skill-os-complete 升级入口

你现在处于 `skill-os-complete` 仓库根目录。

你的任务不是自由发挥，而是**严格按升级控制器执行当前轮**。

---

# 启动规则（必须遵守）

1. 先读取以下文件：
   - `docs/upgrade/CLAUDE_START.md`
   - `docs/upgrade/controller.md`
   - `docs/upgrade/runbook.md`
   - `docs/upgrade/phase_state.json`（如果存在）
   - `docs/upgrade/phase_report_template.md`（如果存在）
   - `docs/upgrade/reports/` 下已有 phase report（如果存在）

2. 然后按 `docs/upgrade/controller.md` 的规则执行：
   - 识别当前 phase
   - 只执行当前 phase
   - 做最小验证 / 自检
   - 输出 Phase Report
   - 做 Gate Check
   - 更新 `docs/upgrade/phase_state.json`

3. **执行完当前 phase 后必须停止**
   - 不允许自动进入下一轮
   - 必须等待用户确认

---

# 本次默认行为

如果用户没有额外说明，默认理解为：

> **执行当前 phase，并在结束后停下来等用户确认。**

---

# 严格禁止

- 不允许跳过 phase
- 不允许一次执行多个 phase
- 不允许在 Gate=GO 后自动继续下一轮
- 不允许只写计划不落地文件
- 不允许省略 Phase Report / Gate Check / phase_state.json 更新

---

# 如果用户说"继续下一轮"

只有当 `phase_state.json` 中 `last_gate == "GO"` 时，才允许进入下一轮。
否则必须停在当前轮并说明原因。

---

# 本次执行完成后，对话里必须输出

```
# Phase X Execution Result

## 1. Current Phase
- Phase Name:
- Goal:
- Status:

## 2. Files Modified

## 3. Files Added

## 4. What Was Completed

## 5. What Was Preserved / Kept Compatible

## 6. Test Results
- tests executed:
- tests passed:
- tests failed:
- failure reason:

## 7. Risks / Known Issues

## 8. Output Artifacts
- docs generated:
- schemas generated:
- test fixtures:
- route assets:

## 9. Gate Check
- Gate Result: GO / NO-GO
- Reason:
- If NO-GO, what must be fixed first:
- If GO, prerequisites for next phase:

## 10. Next Action
- 等待用户确认是否进入下一轮
```

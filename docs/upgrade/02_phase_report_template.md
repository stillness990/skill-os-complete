# 02 Phase Report Template

> 每个 Phase 结束后，Claude 必须严格按以下模板输出阶段报告。  
> **缺少任一字段，视为本轮未完成，不允许进入下一轮。**

---

# Phase Report Template

## 1. Current Phase
- Phase Name:
- Goal:
- Status: Completed / Partial / Failed

## 2. Files Modified
- file_a
- file_b
- file_c

## 3. Files Added
- file_x
- file_y

## 4. What Was Completed
- capability 1
- capability 2
- capability 3

## 5. What Was Preserved / Kept Compatible
- existing skill / module compatibility notes
- old behavior retained
- migration / adapter notes

## 6. Acceptance Check Results
> 必须逐项对照 `docs/upgrade/01_phase_acceptance.md` 当前阶段清单输出结果。

- Check ID:
  - Result: PASS / FAIL / PARTIAL
  - Notes:

- Check ID:
  - Result: PASS / FAIL / PARTIAL
  - Notes:

## 7. Test Results
- tests executed:
- tests passed:
- tests failed:
- failure reason:
- fixtures / mocks used:

## 8. Risks / Known Issues
- issue 1
- issue 2
- issue 3

## 9. Output Artifacts
- docs generated:
- schemas generated:
- route assets:
- test fixtures:
- validation outputs:

## 10. Gate Check
- Gate Result: GO / NO-GO
- Reason:
- Blocking Issues:
- Must Fix Before Next Phase:
- If GO, prerequisites for next phase:
- Remaining Risks:

## 11. Next Phase Plan
- next target
- files expected to change
- expected validation focus

---

# 使用规则

## 规则 1：必须包含 Acceptance Check Results
不能只写“已完成”，必须把当前 Phase 的验收项逐项列出来，并标记 PASS / FAIL / PARTIAL。

## 规则 2：Gate Check 必须与验收结果一致
- 如果任何关键验收项失败，Gate 不能写 GO
- 如果写 GO，必须说明为什么允许进入下一阶段

## 规则 3：NO-GO 时必须停止
若 Gate = NO-GO，Claude 必须停止进入下一阶段，并输出修复点。

## 规则 4：不得省略文件变更信息
至少要列出本轮修改 / 新增的关键文件。

# Audit Checklist（验收清单）— v4

## 版本

v4.0.0（Skill OS v4 execution_guard）

## 概述

一个人工和自动都能参考的验收清单，用于判断一个任务是否"真正完成而不是口头完成"。

---

## 通用验收（所有 task_type 适用）

### A1. 任务记录完整性

- [ ] 任务在 task_ledger（tasks.json）中有对应条目
- [ ] task_id、title、task_type、workflow、source 字段均已填写
- [ ] created_at 和 updated_at 时间戳有效

### A2. 状态流转合法性

- [ ] 任务状态流转符合 task-state-machine.md
- [ ] 没有跳步骤完成（如 queued → done）
- [ ] 没有从终态再流转
- [ ] plan_only 以外的任务都经过了 executing

### A3. 最小产物检查

- [ ] artifacts 数组非空
- [ ] artifact_refs 中至少有一个字段非空
- [ ] result_summary 非空且有意义（≥10 字符，不是"完成了""搞定了"）

### A4. 落地证据

- [ ] 施工类任务有 changed_files 或文档更新记录
- [ ] 不是"只有口头完成，没有仓库/文档改动"
- [ ] 如果确实是方案型任务，task_type 已标记为 plan_only

### A5. next_action / next_step

- [ ] 如果不是终态，next_action 非空
- [ ] next_action 是具体可操作的（不是"继续做"）
- [ ] done 或 cancelled 的任务可以没有 next_action

---

## 按 task_type 的分项验收

### B1. delivery 类任务

- [ ] plan_ref 有效（能指向实际文件）
- [ ] changed_files 非空（实施类）
- [ ] result_summary 说明了交付了什么
- [ ] 相关 workflow 阶段已执行（summarize → planning → executing）
- [ ] 如有 review，review_ref 有效
- [ ] 如有 changelog，changelog_ref 有效

### B2. debug 类任务

- [ ] debug_report_ref 有效
- [ ] root_cause 非空且有意义
- [ ] fix_recommendation 非空
- [ ] fix_ref 有效（如果有修复）或 diagnosis_only 明确标注
- [ ] regression_checklist_ref 有效

### B3. learning 类任务

- [ ] study_plan_ref 或 practice_log_ref 或 review_log_ref 至少有一个
- [ ] learning_state 已更新（current_stage / last_activity_at）
- [ ] next_action 给出了下一步学习建议
- [ ] next_review 给出了下次复盘日期（推荐）

### B4. plan_only 类任务

- [ ] plan_ref 有效且指向实际存在的文件
- [ ] plan 文件内容非空

---

## 防"假完成"特别检查

### C1. "口头完成"检测

- [ ] result_summary 不是仅"已完成""搞定了""做完了"
- [ ] artifacts 不是空数组
- [ ] 有具体文件路径或引用

### C2. "方案伪装实施"检测

- [ ] task_type 与实际产出一致
- [ ] 如果只产出了方案：task_type 应为 plan_only
- [ ] 如果任务是"改代码"但 changed_files 为空：不通过

### C3. "文件不存在"检测

- [ ] artifact_refs 中引用的文件路径确实存在（如可验证）
- [ ] 至少引用的路径格式合理（不是占位符）

### C4. "残留警告"检测

- [ ] guard_status.warnings 中没有未处理的严重警告
- [ ] 如果有 stalled 历史，已正确恢复

---

## execution_guard 使用方式

### 人工验收

在任务完成后，对照此清单逐项自检：
```
1. 通用验收 A1-A5
2. 分项验收 B1-B4（按 task_type）
3. 特别检查 C1-C4
4. 全部通过 → 任务真正完成
   任一项未通过 → 标注"部分完成"，记录缺失项
```

### 自动验收（hook 层）

`completion-guard.py` 读取此清单，自动检查可编程验证的项（A1/A2/A3/C1/C2），对需要人工判断的项（B1 中的文件存在性验证等）尽可能自动验证，无法自动验证的标记为"需人工确认"。

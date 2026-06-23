# 🚀 skill-os-complete 升级 Runbook（针对现有仓库定制版）

## 基于仓库实际状态的定制 Runbook

> **重要前提**：本 Runbook 是在充分读取仓库代码后定制的，
> Phase 1 和 Phase 2 的主要产物已在仓库中存在，
> 从 **Phase 3** 开始执行缺失模块的补全工作。

---

# 0. 强制规则（所有轮次）

1. **每次只允许执行一个 Phase**
2. 每个 Phase 结束后必须：输出阶段报告 → Gate Check → 更新 phase_state.json → **停止**
3. **不允许自动进入下一轮**
4. 只有用户说"继续下一轮 / 继续下一 phase / 进入下一轮 / 跑 phase X"才允许推进

---

# 1. 总控规则

## 1.1 不允许破坏现有实现

仓库中以下内容**已经落地且运行正常，禁止破坏**：
- `.claude/hooks/skill-router.py` — 主路由 hook，实际运行中
- `.claude/router/routing_rules.py` — 关键词 + intent 路由逻辑
- `.claude/router/workflow_templates.json` — 三条 workflow 定义
- `orchestration/route_plan.py` — RoutePlan dataclass
- `orchestration/orchestration_types.py` — 所有枚举类型
- `orchestration/workflow_state.py` — WorkflowState
- `orchestration/workflow_resolver.py` — 多源融合决策器（已引用 semantic_router）
- `orchestration/skill_router.py` — 技能执行器
- `orchestration/rollback_manager.py` — 回滚管理器（路径安全已实现）
- `orchestration/self_healing.py` — 自愈管理器（硬约束已实现）
- `orchestration/safe_mode.py` — SafeMode 管理器
- `orchestration/execution_guard.py` — 执行监督层
- `ledger/task_ledger.py` — 任务账本
- `ledger/ledger_schema.py` — Schema 定义
- `routing_assets/` — 三件套已落地

## 1.2 不允许假升级

以下情况视为失败：
- 文件创建了但 import 链断了
- 测试文件存在但被测模块不存在
- SAFE MODE 代码存在但从未真实触发过
- 只改文档不改代码
- 只写 TODO / placeholder

## 1.3 每轮必须严格按报告模板输出

## 1.4 每轮必须做 Gate Check

## 1.5 SAFE MODE 必须做真触发验证（Phase 6 硬要求）

---

# 2. 现有仓库状态速查

## ✅ 已完成（Phase 1 + 2 产物）

| 模块 | 文件 | 状态 |
|------|------|------|
| 协议层 | orchestration/orchestration_types.py | ✅ 完整 |
| RoutePlan | orchestration/route_plan.py | ✅ 完整 |
| WorkflowState | orchestration/workflow_state.py | ✅ 完整 |
| WorkflowResolver | orchestration/workflow_resolver.py | ✅ 已引用 semantic_router（但后者缺失） |
| SkillRouter | orchestration/skill_router.py | ✅ 完整 |
| RollbackManager | orchestration/rollback_manager.py | ✅ 路径安全已实现 |
| SelfHealing | orchestration/self_healing.py | ✅ 硬约束已实现 |
| SafeMode | orchestration/safe_mode.py | ✅ 完整 |
| ExecutionGuard | orchestration/execution_guard.py | ✅ 完整 |
| LedgerSchema | ledger/ledger_schema.py | ✅ 完整 |
| TaskLedger | ledger/task_ledger.py | ✅ 完整 |
| RoutingAssets | routing_assets/*.json | ✅ 三件套完整 |
| 现有 Hook | .claude/hooks/skill-router.py | ✅ 生产运行 |

## ❌ 缺失（需要补全）

| 模块 | 文件 | 缺失原因 |
|------|------|---------|
| PromptNormalizer | orchestration/prompt_normalizer.py | Phase 3 遗漏 |
| RuleRouter | orchestration/rule_router.py | Phase 3 遗漏 |
| SemanticRouter | orchestration/semantic_router.py | Phase 4 未做 |
| E2E 测试 | tests/test_e2e.py | Phase 6 未做 |
| SafeMode 测试 | tests/test_safe_mode.py | Phase 6 未做 |
| Rollback 测试 | tests/test_rollback.py | Phase 6 未做 |
| Ledger 测试 | tests/test_ledger.py | Phase 6 未做 |
| Runbook 控制系统 | docs/upgrade/ | 本次补入 |
| Architecture Report | docs/architecture/ | Phase 6 未做 |
| Validation Report | docs/validation/ | Phase 6 未做 |

---

# 3. 六轮总览（基于现状定制）

| Phase | 实际工作内容 |
|-------|-------------|
| 1 | ✅ 已完成 — 仓库审计产物已在 |
| 2 | ✅ 已完成 — 协议层 / Schema / Ledger 已在 |
| 3 | 补全 prompt_normalizer + rule_router + 验证 tests/test_prompt_normalizer 和 test_rule_router 可运行 |
| 4 | 实现 semantic_router + embedding health check + 验证 workflow_resolver 完整链路 |
| 5 | 集成测试：验证 skill_router + guard + rollback + healing + safe_mode 的联动（代码已在，需要接线和测试） |
| 6 | 全量测试 + SAFE MODE 真触发 + E2E 三大场景 + 生成 architecture/validation/failure 报告 |

---

# 4. Phase 3 — 补全 prompt_normalizer + rule_router

## 4.1 背景

`workflow_resolver.py` 已经写好了对 `prompt_normalizer` 和 `rule_router` 的 import：

```python
from prompt_normalizer import NormalizedInput, PromptNormalizer
from rule_router import RuleRouter, RuleMatch
```

但这两个文件不存在，导致 workflow_resolver 无法运行。
tests/test_prompt_normalizer.py 和 tests/test_rule_router.py 已存在，但无法运行。

## 4.2 本轮目标

1. 实现 `orchestration/prompt_normalizer.py`
2. 实现 `orchestration/rule_router.py`
3. 验证 tests/test_prompt_normalizer.py 可以运行
4. 验证 tests/test_rule_router.py 可以运行
5. **不破坏现有 .claude/hooks/skill-router.py 的运行**

## 4.3 PromptNormalizer 必须支持

- slash commands：`/plan /debug /task /next`
- intents：repo_analysis / planning / debug / learning / construction_prompt / multi_intent
- 输出 `NormalizedInput` dataclass，至少包含：
  - `normalized: str` — 标准化后的文本
  - `primary_intent_hint: str` — 主意图提示
  - `slash_commands: list[str]`
  - `is_multi_intent: bool`
  - `detected_types: list[str]`

## 4.4 RuleRouter 必须支持

接收 `NormalizedInput`，输出 `list[RuleMatch]`，每个 RuleMatch 包含：
- `workflow: Workflow`
- `intent: Intent`
- `confidence: float`
- `matched_rule: str`

必须覆盖的四条高置信规则（与 routing_assets/route_examples.json 对齐）：

| 规则 | 输入特征 | 输出 workflow |
|------|----------|--------------|
| A | "读取项目并评估功能" / "分析仓库" / "升级方案" | delivery_pipeline |
| B | "生成 Claude 施工单" / "construction prompt" | delivery_pipeline |
| C | "docker compose up 报 permission denied" / 报错类 | debug_pipeline |
| D | "我想学" / "今天学什么" / 学习型 | learning_pipeline |

## 4.5 本轮验收标准

- [ ] `orchestration/prompt_normalizer.py` 已创建，`PromptNormalizer` 可实例化
- [ ] `orchestration/rule_router.py` 已创建，`RuleRouter` 可实例化
- [ ] `from prompt_normalizer import NormalizedInput, PromptNormalizer` 不报错
- [ ] `from rule_router import RuleRouter, RuleMatch` 不报错
- [ ] `workflow_resolver.py` 可以 import（不再因缺失模块而报错）
- [ ] `tests/test_prompt_normalizer.py` 可以运行（无 ImportError）
- [ ] `tests/test_rule_router.py` 可以运行（无 ImportError）
- [ ] 三大场景的 rule routing 输出正确 workflow

## 4.6 不允许

- 修改 `.claude/hooks/skill-router.py`（生产 hook）
- 修改 `.claude/router/routing_rules.py`（生产路由规则）
- 删除或覆盖已有的 orchestration/ 文件
- 修改 workflow_resolver.py 的 import 行（让它们 pass 而不是真实实现）

---

# 5. Phase 4 — 实现 semantic_router + 验证 workflow_resolver 完整链路

## 5.1 背景

`workflow_resolver.py` 同样 import 了 semantic_router：

```python
from semantic_router import SemanticRouter, SemanticCandidate, EmbeddingHealth
```

需要实现这个模块，但 semantic-router 的真实 embedding 调用依赖 Ollama，
在没有 Ollama 的环境下必须能优雅降级。

## 5.2 本轮目标

1. 实现 `orchestration/semantic_router.py`
2. 实现 `orchestration/embedding_provider.py`（embedding 接口 + health check）
3. 验证 workflow_resolver 完整导入链路可用
4. 验证三大场景在 rule-only 模式（embedding 不可用时）能输出正确 RoutePlan
5. 验证 embedding health check 失败时正确进入 degraded 状态

## 5.3 SemanticRouter 必须支持

- 接收 `normalized: str`，查询 routing_assets/ 中的示例
- 输出 `list[SemanticCandidate]`，每个包含：`workflow / confidence / similarity_score`
- 支持 `EmbeddingHealth`：`available: bool / degraded: bool / error: str`
- embedding 服务不可用时返回空列表 + degraded health，不崩溃

## 5.4 embedding_provider 必须至少检查

- 服务是否可达（连接超时）
- 模型是否可调用
- 返回结构化 health 状态，不抛异常

## 5.5 三大场景验收（rule-only 模式，embedding 不可用）

| 场景 | 期望 workflow | 期望 stages |
|------|--------------|-------------|
| 读取项目并评估功能，再给升级方案 | delivery_pipeline | summarize → planning |
| 生成 Claude 施工单 | delivery_pipeline | summarize → planning → ask |
| docker compose up 报 permission denied | debug_pipeline | debug(diagnose) |

## 5.6 本轮验收标准

- [ ] `orchestration/semantic_router.py` 已实现
- [ ] `orchestration/embedding_provider.py` 已实现
- [ ] embedding 不可用时 SemanticRouter 返回空列表 + degraded health
- [ ] `workflow_resolver.py` 完整导入链路无 ImportError
- [ ] 三大场景在 rule-only 模式下输出正确 RoutePlan
- [ ] WorkflowResolver 实例可以创建并调用 resolve()

---

# 6. Phase 5 — 集成测试：联动验证

## 6.1 背景

Phase 5 的所有代码（skill_router / execution_guard / rollback_manager / self_healing / safe_mode）已经存在。
本轮的工作是**验证它们能正确协同工作**，并补全缺失的集成测试。

## 6.2 本轮目标

1. 编写 `tests/test_integration.py` — 验证完整执行链
2. 编写 `tests/test_rollback.py` — 验证路径安全规则
3. 编写 `tests/test_safe_mode.py` — 验证 SafeMode 基础行为
4. 编写 `tests/test_ledger.py` — 验证 ledger 写入读取
5. 运行所有测试，确保通过
6. 修复发现的任何集成 bug

## 6.3 集成测试必须验证

### skill_router 集成
- 接收 RoutePlan，逐 stage 执行
- stage 状态写入 ledger
- 失败时调用 self_healing

### execution_guard 集成
- required stages 检查
- no-op completion 检查
- delivery_pipeline 缺 summarize/planning 时 BLOCK

### rollback 路径安全（4 件事）
1. rollback 真实读取了 artifact_paths
2. artifact_paths 经过 repo-root 路径校验
3. 越界路径（含 `../` 或绝对路径）被拒绝删除
4. 安全路径正常清理

### self_healing 硬约束
- retry_count ≤ 3
- same_failure_type ≤ 2
- embedding_fail → immediate fallback
- 防递归调用

### safe_mode 基础行为
- 可以触发
- is_active 返回 True
- should_disable_semantic() 返回 True

## 6.4 本轮验收标准

- [ ] tests/test_integration.py 存在且通过
- [ ] tests/test_rollback.py 存在且通过（包含越界路径测试）
- [ ] tests/test_safe_mode.py 存在且通过
- [ ] tests/test_ledger.py 存在且通过
- [ ] 所有测试无 ImportError
- [ ] rollback 越界路径测试明确通过

---

# 7. Phase 6 — 全量测试 + SAFE MODE 真触发 + 最终报告

## 7.1 本轮目标

1. 运行所有测试
2. E2E 三大场景完整验证
3. SAFE MODE 真实触发（embedding 不可用场景）
4. 生成 architecture / validation / failure 报告

## 7.2 SAFE MODE 真触发（硬要求）

必须构造 embedding 不可用场景，验证以下 5 件事：

1. 系统**没有崩溃**
2. semantic-router **被禁用或返回 degraded**
3. workflow-resolver **退化为 rule_only 模式**
4. self-healing **在 SAFE MODE 下被收缩（stop 而非 retry）**
5. ledger / logs / 验证报告中**明确记录 SAFE MODE 已进入**

可用方案：
- **方案 A**：env flag `EMBEDDING_FORCE_FAIL=1` 让 health check 返回失败
- **方案 B**：embedding host 指向不可达地址（localhost:9999）
- **方案 C**：mock embedding_provider 直接返回 unavailable

## 7.3 rollback 验证（4 件事）

1. rollback 真实读取 artifact_paths
2. 路径经过 repo-root 校验
3. 越界路径（`../etc/passwd`）被拒绝
4. 安全路径文件被删除

## 7.4 最终报告

### docs/architecture/architecture_report.md
- 新架构图（文字或 ASCII）
- routing flow
- workflow flow
- 各模块职责
- skill 兼容策略（旧 hook 与新 orchestration 的关系）

### docs/validation/validation_report.md
- 三大场景结果
- execution_guard 结果
- SAFE MODE 触发结果
- rollback / healing 结果
- 测试通过情况

### docs/failure/failure_report.md（若有失败）
- failure type
- failure phase
- recovery action
- rollback log
- 是否进入 SAFE MODE

## 7.5 最终成功定义

- [ ] 所有现有测试通过
- [ ] tests/test_e2e.py 三大场景全部正确
- [ ] SAFE MODE 已真实触发验证
- [ ] rollback 越界路径拒删验证通过
- [ ] self-healing 上限验证通过
- [ ] architecture / validation 报告已生成

---

# 8. 轮次推进规则

Gate = GO **不代表可以自动进入下一轮**。

只有用户明确说：
- 继续下一轮
- 继续下一 phase
- 进入下一轮
- 跑 phase X

才允许推进。否则一律停留在当前轮。

# 03 SAFE MODE / Rollback / Self-Healing 统一规范

> 本文件定义高风险执行能力的统一规则。  
> Claude 在 Phase 2 ~ Phase 6 中涉及以下能力时，必须遵守本文件：
>
> - SAFE MODE
> - rollback
> - self-healing
> - artifact_paths 路径安全
> - embedding 不可用时的降级策略

---

# 1. SAFE MODE 的目标

SAFE MODE 的作用不是“报错退出”，而是让系统在关键依赖失效时：

1. 不崩溃
2. 不继续走高风险链路
3. 降级到可控的基础模式
4. 把异常状态记录到 ledger / logs / validation report
5. 防止自愈、回滚、路由等模块失控放大错误

---

# 2. SAFE MODE 进入条件

以下任一情况出现时，应允许系统进入 SAFE MODE：

## 2.1 embedding / semantic routing 不可用
例如：
- embedding 服务不可达
- embedding provider timeout
- 模型不存在 / 模型不可调用
- health check 连续失败
- semantic-router 关键依赖初始化失败

## 2.2 rollback 安全异常
例如：
- artifact_paths 包含越界路径
- rollback 解析后发现目标位于 repo-root 之外
- rollback 清理目标不可安全识别

## 2.3 self-healing 达到失控边界
例如：
- retry_count 超过上限
- same_failure_type_count 超过上限
- healing 尝试重复进入同类错误循环

## 2.4 execution_guard 发现关键结构性缺失
例如：
- delivery_pipeline 缺 summarize / planning
- construction_prompt 缺 ask
- debug_pipeline 缺 diagnose
- expected_artifacts 缺失且不可恢复

---

# 3. SAFE MODE 进入后的系统行为

一旦进入 SAFE MODE，系统至少要做到：

## 3.1 semantic-router 降级
- 禁用 semantic candidate 检索，或直接跳过 semantic-router
- workflow-resolver 只能使用：
  - normalized input
  - rule candidates
  - safe fallback rules

## 3.2 workflow-resolver 退化为 basic mode
basic mode 至少保证：
- 能根据 rule-router 输出保底 RoutePlan
- 不依赖 embedding 成功
- 能给出可审计的 fallback route

## 3.3 self-healing 收缩或禁用
SAFE MODE 下必须满足至少一条：
- 禁用自动 retry
- 或将 retry_count 收缩到 0/1 次
- 禁止继续对 embedding 故障做重复自愈

## 3.4 rollback 保守执行
若失败源于路径安全异常，则：
- 不做危险删除
- 记录 rollback security error
- 停止进一步清理危险路径

## 3.5 ledger / logs 必须记录 SAFE MODE
至少记录：
- safe_mode = true
- trigger_reason
- route_id
- workflow
- stage_id（如有）
- degraded_actions

---

# 4. SAFE MODE 真触发验证（Phase 6 硬要求）

在最终验收阶段，必须做**真实故障注入**，不接受“理论上可行”。

## 允许的故障注入方式
至少任选其一：

### 方案 A：错误 embedding 地址
- 将 embedding host / port 指向不可达地址
- 触发一次需要 semantic-router 的请求

### 方案 B：mock embedding provider unavailable
- 让 health check 返回失败
- 验证 degraded → safe_mode 分支

### 方案 C：测试环境 env flag 强制 embedding fail
- 仅用于测试环境
- 必须确保真实走到 SAFE MODE 分支

## 验收必须证明
1. 系统没有崩溃
2. semantic-router 被禁用或跳过
3. workflow-resolver 退化为 basic mode
4. self-healing 被禁用或收缩
5. ledger / logs / validation report 中明确记录 SAFE MODE 已进入

---

# 5. artifact_paths 的统一规则（硬约束）

所有 artifact_paths 必须遵守以下规则：

## 5.1 存储规则
- 统一存为**相对于仓库根目录（repo root）的相对路径**
- 不允许把绝对路径作为 ledger 标准存储格式
- 不允许存储裸 `~`、环境变量占位路径、不可解析路径

## 5.2 路径安全规则
- 禁止 `../` 向上遍历
- 清理前必须：
  1. normalize
  2. resolve against repo root
  3. 检查最终路径仍位于 repo root 内

## 5.3 越界路径处理规则
如果任一 artifact_path：
- 包含 `../`
- 归一化后越出 repo root
- 指向未知危险位置
- 解析失败

则必须：
1. 拒绝删除
2. 记录 rollback security error
3. 将该 route / rollback 标记为异常
4. 必要时进入 SAFE MODE

---

# 6. rollback 统一执行规范

rollback 必须至少执行以下步骤：

## Step 1 — 从 ledger 读取 artifact_paths
不得凭空猜测或只按目录通配删除。

## Step 2 — 对每个 artifact_path 执行路径安全校验
流程必须是：

```text
artifact_path
→ normalize
→ resolve against repo root
→ boundary check
→ safe cleanup or reject
```

## Step 3 — 删除安全 artifact
仅允许删除：
- 位于 repo-root 内
- 已通过 boundary check
- 属于当前 route / stage 的产物

## Step 4 — 清理 route cache / 状态
包括但不限于：
- route cache
- stage temp state
- rollback markers

## Step 5 — 写回 rollback 结果
至少记录：
- rollback_status
- cleaned_artifacts
- rejected_artifacts
- security_errors
- updated_at

---

# 7. self-healing 统一约束

self-healing 不是无限重试器，必须有硬上限。

## 7.1 硬限制
- `retry_count <= 3`
- `same_failure_type_count <= 2`
- embedding_fail → immediate fallback
- 不允许递归调用 self-healing
- 每次 retry 必须生成新的 route_id

## 7.2 禁止行为
- 同一个失败类型无限重试
- rollback 失败后无脑再 rollback
- SAFE MODE 下继续高频自愈
- 失败后绕过 execution_guard 强行宣告完成

## 7.3 建议恢复策略
优先级建议如下：
1. 轻量重试（仅限可恢复错误）
2. fallback route / fallback provider
3. 进入 SAFE MODE
4. 停止并输出 failure report

---

# 8. execution_guard 与 SAFE MODE 的联动

若 execution_guard 检测到以下关键结构性错误，应至少触发降级或阻止推进：

- delivery_pipeline 缺 summarize / planning
- construction_prompt 缺 ask
- debug_pipeline 缺 diagnose
- expected_artifacts 缺失且无法补救
- ledger 未更新但 stage 被宣告成功
- 出现 no-op completion

当这些错误无法通过安全补救解决时：
- 当前阶段应 `NO-GO`
- 必要时进入 SAFE MODE 或 failure state

---

# 9. Claude 实施时的固定要求

在实现 SAFE MODE / rollback / self-healing 相关代码时，Claude 必须做到：

1. 不只写文档，必须把关键规则落到实现中
2. 不允许“未来再做”式占位
3. 任何 rollback 删除动作都必须经过 repo-root 边界校验
4. 任何 SAFE MODE 触发都必须写入 ledger / logs
5. 任何 self-healing 都必须受 retry 上限约束

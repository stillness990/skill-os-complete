# skill-os-complete

**Claude Code 自动技能路由系统** — 零延迟、纯本地、关键字驱动的技能自动注入引擎。

在 Claude Code 中输入文字时，Hook 自动分析内容并注入对应技能指令，让 Claude 按预定义规范回答。无需切换模式、无需手动选择技能。

> **当前版本：Phase 2** — 学习工作流正式落地。teach-plus 升级为学习控制层（explain/practice/review 三模式），learning_pipeline 正式贯通。

## 工作原理

```text
你在 Claude Code 中输入文字
  ↓
UserPromptSubmit Hook 触发
  ↓
skill-router.py 读取输入 → intent→workflow→primary skill
  ↓
自动注入对应技能规范
  ↓
Claude 按规范回答（无命中则正常对话）
```

## 3 条工作流管线

### 1. Delivery Pipeline（项目交付）

```text
ask（需求澄清）
  ↓
summarize/briefing（项目底稿）
  ↓
planning/project（阶段计划 + 今日行动）
  ↓
task_ledger（任务入账）
  ↓
code_assistant → reviewer → changelog
```

### 2. Debug Pipeline（问题诊断）

```text
summarize/briefing（问题背景，可选）
  ↓
debug（诊断引擎：现象→假设→验证→修复→回归）
  ↓
code_assistant（代码修复）
  ↓
debug_log（排查记录归档）
```

### 3. Learning Pipeline（学习工作流）★ Phase 2 正式版

```text
summarize/briefing（学习底稿）
  ↓
planning/learning（阶段学习计划）
  ↓
teach-plus/explain（理解框架）
  ↓
teach-plus/practice（每日学习单 + 练习任务）
  ↓
task_ledger（学习任务入账）
  ↓
teach-plus/review（周复盘 / 阶段复盘）
```

## 快速安装

```bash
# 1. 克隆项目
git clone https://github.com/stillness990/skill-os-complete.git

# 2. 进入你的项目目录
cd /path/to/your-project

# 3. 运行安装脚本
bash /path/to/skill-os-complete/install.sh
```

安装脚本自动完成：
- 复制 `.claude/` 到项目目录
- 创建 `practice/` 学习工作区
- 设置执行权限
- 验证 4 个 JSON 文件格式
- 运行 20 项路由测试

## 内置技能（14 个）

### 核心基座（Phase 1 重构）

| 技能 | 分类 | 触发方式 | 作用 |
|------|------|---------|------|
| `summarize` | core | `总结`、`摘要`、`读懂这个`、`分析仓库` | 知识整理中台（basic/briefing 双模式） |
| `planning` | core | `计划`、`规划`、`方案`、`学习路线` | 任务拆解引擎（project/learning 双模式） |
| `debug` | core | `报错`、`诊断`、`行为异常`、`排查` | 诊断引擎（现象→假设→验证→修复→回归） |

### 学习控制层（Phase 2 重构）★

| 技能 | 分类 | 触发方式 | 作用 |
|------|------|---------|------|
| `teach-plus` | learning | `我想学`、`今天学什么`、`复盘`、`给我讲` | 学习控制层：explain（讲解）/ practice（每日练习）/ review（周复盘）三模式 |

### 执行层

| 技能 | 优先级 | 触发方式 | 作用 |
|------|--------|---------|------|
| `ask` | 4 | `我想做`、`有个想法`、`还没想好` | 需求澄清，最多 3 个关键问题 |
| `code_assistant` | 3 | `代码`、`修复`、`重构`、`帮我写` | 代码编写与修复 |
| `sop` | 2 | `手册`、`怎么处理`、`SOP` | 生成标准操作步骤 |
| `reviewer` | 2 | `review`、`代码审查` | 检查代码质量/Bug/安全 |
| `changelog` | 2 | `changelog`、`更新日志` | 按 Added/Changed/Fixed 生成日志 |
| `sanitize` | 2 | `脱敏`、`消毒`、`sanitize` | 扫描替换敏感信息 |

### 系统层

| 技能 | 优先级 | 触发方式 | 作用 |
|------|--------|---------|------|
| `task_manager` → `task_ledger` | 3 | `下一步`、`当前进度`、`任务状态` | 系统层任务账本（含学习任务 schema） |

### 工具层

| 技能 | 优先级 | 触发方式 | 作用 |
|------|--------|---------|------|
| `echo` | 1 | `echo xxx` | 原样返回 |
| `debug_log` | 2 | `解决了`、`留档` | 生成排查记录 .md |
| `dify_kb_search` | 2 | `科目一`~`科目四` | 电工知识库检索 |

## 使用方式

### 触发技能

输入中自然包含关键词即可，无需特殊前缀：

| 你想做的事 | 这样说 |
|-----------|--------|
| 需求澄清 | `我想做个东西但还没想好` |
| 知识整理 | `总结一下这个项目` / `读懂这个仓库是做什么的` |
| 出计划 | `给我一个计划，做一个用户登录系统` |
| 诊断问题 | `帮我 debug 这段代码，一直报 KeyError` |
| 写操作手册 | `数据库连接失败怎么处理，帮我写操作手册` |
| 代码审查 | `帮我 review 一下这段代码` |
| 变更日志 | `生成这次的更新日志` |
| 项目脱敏 | `帮我对这个项目做脱敏处理，准备发布` |
| **学习：讲解** | `我想学 Rust` / `给我讲明白这个系统` |
| **学习：练习** | `给我今天的学习任务` / `今天学什么` |
| **学习：复盘** | `帮我复盘这周学的` / `本周学习复盘` |
| 正常聊天 | `今天天气怎么样`（不触发任何技能） |

## 添加新技能

### 第一步：创建技能定义

```bash
mkdir -p .claude/skills/<新技能名>
```

创建 `.claude/skills/<新技能名>/SKILL.md`：

```markdown
---
name: <技能名>
description: "<一句话描述>"
---

# <技能名> Skill

## 用途
...

## 行为规则
- ...
```

参考模板：`.claude/skills/sop/SKILL.md`

### 第二步：注册路由规则

打开 `.claude/skill-rules.json`，在 `"skills"` 对象中添加：

```json
"<新技能名>": {
  "priority": 2,
  "keywords": ["关键词1", "关键词2"],
  "intentPatterns": [
    "(正则模式1)"
  ]
}
```

### 第三步：验证并测试

```bash
python3 -c "import json; json.load(open('.claude/skill-rules.json'))"
echo '{"prompt": "你的测试输入"}' \
  | CLAUDE_PROJECT_DIR="$(pwd)" python3 .claude/hooks/skill-router.py
```

**不需要重启 Claude Code，保存文件立即生效。**

## 项目结构（Phase 2）

```text
skill-os-complete/
├── CLAUDE.md                               # 项目说明
├── install.sh                              # 一键安装脚本（含 20 项测试）
├── README.md                               # 本文件
└── .claude/
    ├── settings.json                       # Hook 注册入口
    ├── skill-rules.json                    # 路由关键词规则（14个技能）
    ├── hooks/
    │   └── skill-router.py                 # v3 router：intent→workflow→skill
    ├── router/
    │   ├── skill_index.json                # 技能索引
    │   ├── workflow_templates.json         # 3 条 workflow 定义
    │   ├── routing_rules.py                # 路由规则模块
    │   └── intent_schema.md                # 意图分类协议
    ├── protocols/
    │   ├── summary-protocol.md             # 摘要协议
    │   ├── briefing-protocol.md            # 底稿协议
    │   ├── plan-protocol.md                # 计划协议
    │   ├── debug-protocol.md               # 诊断协议
    │   ├── learning-plan-protocol.md       # ★ 学习计划协议
    │   ├── daily-study-protocol.md         # ★ 每日学习单协议
    │   └── weekly-review-protocol.md       # ★ 每周复盘协议
    ├── skills/
    │   ├── core/
    │   │   ├── summarize/                  # 知识整理中台
    │   │   ├── planning/                   # 任务拆解引擎
    │   │   └── debug/                      # 诊断引擎
    │   └── teach-plus/
    │       ├── SKILL.md                    # ★ 学习控制层总入口
    │       ├── explain.md                  # ★ explain 模式
    │       ├── practice.md                 # ★ practice 模式
    │       ├── review.md                   # ★ review 模式
    │       └── templates/                  # ★ 学习模板
    ├── workflows/
    │   ├── delivery_pipeline.md            # ★ 交付工作流文档
    │   ├── debug_pipeline.md               # ★ 诊断工作流文档
    │   └── learning_pipeline.md            # ★ 学习工作流文档
    └── system/
        ├── task_ledger/
        │   ├── tasks.json                  # 任务账本
        │   ├── schema.md                   # 通用 schema
        │   ├── learning-task-schema.md     # ★ 学习任务 schema
        │   └── task-ops.py                 # 任务操作脚本
        └── knowledge/
            ├── learning_briefs/            # ★ 学习底稿存档
            ├── study_plans/                # ★ 学习计划存档
            └── review_logs/                # ★ 复盘记录存档
```

> ★ = Phase 2 新增或重构

## Phase 2 升级说明

### 与 Phase 1 的关键变化

| 模块 | Phase 1 | Phase 2 |
|------|---------|---------|
| teach-plus | 单一学习 skill | 学习控制层（explain/practice/review 三模式） |
| learning_pipeline | 占位标记 | 7 阶段正式工作流 |
| learning 协议 | 无 | 3 个协议文件 |
| task_ledger | 通用任务 schema | 新增 learning-task-schema |
| knowledge | 空占位目录 | 3 个子目录（briefings/plans/logs） |
| workflows/ | 定义在 JSON 中 | 新增独立 .md 工作流文档 |

### 学习请求的完整流转

```
"我想学这个仓库"
    ↓ ask（需求澄清，可选）
    ↓ summarize/briefing（生成学习底稿 → knowledge/learning_briefs/）
    ↓ planning/learning（生成阶段计划 → knowledge/study_plans/）
    ↓ teach-plus/explain（建立理解框架）
    ↓ teach-plus/practice（每日学习单 → practice/daily/ + task_ledger）
    ↓ teach-plus/review（周复盘 → practice/reviews/ + knowledge/review_logs/）
```

## 故障排查

### 技能完全不触发

```bash
echo '{"prompt": "帮我 debug 这段代码"}' \
  | CLAUDE_PROJECT_DIR="$(pwd)" python3 .claude/hooks/skill-router.py
```

预期输出中包含技能名和 `"prompt_injection"`。如果输出 `{}`：

| 检查项 | 命令 | 预期 |
|--------|------|------|
| skill-rules.json 存在 | `ls .claude/skill-rules.json` | 文件存在 |
| JSON 格式正确 | `python3 -c "import json; json.load(open('.claude/skill-rules.json')); print('OK')"` | `OK` |
| python3 可用 | `which python3` | 路径非空 |

### 多个技能竞争选错了

- A：给期望技能加独特关键词
- B：降低冲突技能的 `priority`
- C：给期望技能加精准的 `intentPatterns` 正则

## 备份与恢复

```bash
ls .claude/backups/
cp .claude/backups/<最新备份> .claude/settings.json
```

## 回滚/卸载

```bash
rm .claude/skill-rules.json
rm .claude/hooks/skill-router.py
rm -rf .claude/skills
rm -rf .claude/router
rm -rf .claude/protocols
rm -rf .claude/system
rm -rf .claude/workflows
```
然后手动编辑 `settings.json`，移除 skill-router 对应的 hook 条目。

## License

MIT

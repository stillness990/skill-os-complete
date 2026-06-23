# Knowledge Asset Skills

> 一个用于 Claude Code 的知识资产化技能：将日常任务、技术问题、项目规划、故障排查和工程交付，沉淀为结构化、可检索、可复用、可执行的长期知识资产。

## 目录

- [项目简介](#项目简介)
- [适用场景](#适用场景)
- [核心能力](#核心能力)
- [目录结构](#目录结构)
- [安装方式](#安装方式)
- [使用方式](#使用方式)
- [输出规范](#输出规范)
- [内置模板](#内置模板)
- [示例提示词](#示例提示词)
- [推荐工作流](#推荐工作流)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)
- [后续规划](#后续规划)

## 项目简介

`knowledge-asset-skills` 是一个 Claude Code Skill，目标不是让 AI 只给出一次性答案，而是让每一次交互都能产生可长期复用的知识资产。

它适合用于：

- 技术方案沉淀
- 项目规划与拆解
- 架构设计文档生成
- SOP / Runbook 编写
- 故障排查记录
- 自动化脚本说明
- 工程实践总结
- 团队知识库建设

该技能会引导 Claude 以更稳定的结构输出内容，减少随意聊天式回答，提升内容的可读性、可维护性和可检索性。

## 适用场景

| 场景 | 说明 | 推荐输出 |
|---|---|---|
| 技术问题分析 | 分析一个 bug、报错、异常行为或系统问题 | Troubleshooting Guide |
| 项目启动 | 从 0 到 1 规划项目目标、范围、里程碑和交付物 | Project Plan |
| 架构设计 | 梳理系统模块、数据流、依赖、风险和扩展方案 | Architecture Doc |
| 运维操作 | 固化部署、备份、恢复、巡检等流程 | SOP / Runbook |
| 自动化任务 | 设计脚本、命令、定时任务、验证方式 | SOP + Commands |
| 知识沉淀 | 将零散经验整理成可复用笔记 | Knowledge Note |
| 团队交接 | 生成新人可读的说明文档 | README / SOP |

## 核心能力

### 1. 结构化输出

默认使用固定结构组织答案：

1. 核心结论
2. 关键知识
3. 实施步骤
4. 命令 / 代码
5. 验证方法
6. 故障排查
7. 最佳实践
8. 相关知识
9. 标签

### 2. 知识资产优先

相比一次性回答，该技能更关注：

- 是否可以保存到 `docs/` 或 `knowledge-base/`
- 是否方便未来检索
- 是否有明确执行步骤
- 是否包含验证方法
- 是否能被他人复用

### 3. 工程化交付

处理软件工程任务时，会默认遵循以下流程：

1. 明确需求
2. 设计方案
3. 拆解任务
4. 实施修改
5. 测试验证
6. 文档沉淀

### 4. 模板化沉淀

仓库内置多种 Markdown 模板，可直接用于知识库、项目文档或团队 Wiki。

## 目录结构

```text
.
├── SKILL.md
├── README.md
└── templates/
    ├── architecture.md
    ├── knowledge-note.md
    ├── project-plan.md
    ├── sop.md
    └── troubleshooting.md
```

### 文件说明

| 文件 | 作用 |
|---|---|
| `SKILL.md` | Claude Code Skill 主定义文件，描述技能行为和输出规则 |
| `README.md` | 项目说明文档 |
| `templates/architecture.md` | 系统架构文档模板 |
| `templates/knowledge-note.md` | 通用知识笔记模板 |
| `templates/project-plan.md` | 项目计划模板 |
| `templates/sop.md` | 标准操作流程模板 |
| `templates/troubleshooting.md` | 故障排查文档模板 |

## 安装方式

### 方式一：复制到 Claude Code Skills 目录

将本仓库复制到 Claude Code 的 skills 目录中：

```bash
mkdir -p ~/.claude/skills
cp -r knowledge-asset-skills ~/.claude/skills/knowledge-asset
```

然后在 Claude Code 中使用：

```text
/knowledge-asset
```

### 方式二：克隆到本地后软链接

```bash
git clone https://github.com/stillness990/knowledge-asset-skills.git
ln -s $(pwd)/knowledge-asset-skills ~/.claude/skills/knowledge-asset
```

适合需要持续更新技能内容的场景。

### 方式三：直接维护在自定义 skills 目录

如果你已经有自己的技能目录，例如：

```text
~/skills/
```

可以直接放置为：

```text
~/skills/knowledge-asset/
```

并根据你的 Claude Code 配置加载该目录。

## 使用方式

在 Claude Code 中输入：

```text
/knowledge-asset
```

然后继续提出你的任务，例如：

```text
/knowledge-asset 帮我把这个部署流程整理成 SOP
```

或：

```text
/knowledge-asset 分析这个报错，并生成一份故障排查文档
```

或：

```text
/knowledge-asset 为这个项目生成架构说明和开发计划
```

## 输出规范

### 默认回答结构

使用该技能后，推荐输出包含以下部分：

```markdown
## 核心结论

## 关键知识

## 实施步骤

## 命令 / 代码

## 验证方法

## 故障排查

## 最佳实践

## 相关知识

## 标签
```

### 文档风格要求

- 使用清晰标题
- 使用列表和表格组织内容
- 避免冗长闲聊
- 给出可执行步骤
- 给出验证方法
- 给出失败排查方式
- 尽量产出可直接保存的 Markdown 文档

## 内置模板

### 1. SOP 模板

路径：

```text
templates/sop.md
```

适合沉淀标准操作流程，例如：

- 部署流程
- 备份流程
- 恢复流程
- 巡检流程
- 发布流程

### 2. Troubleshooting 模板

路径：

```text
templates/troubleshooting.md
```

适合记录问题排查过程，例如：

- 服务无法启动
- API 返回异常
- 数据库连接失败
- Docker 容器异常退出
- 定时任务未执行

### 3. Knowledge Note 模板

路径：

```text
templates/knowledge-note.md
```

适合整理通用知识，例如：

- 技术概念
- 命令速查
- 实践总结
- 常见坑点
- 参考链接

### 4. Architecture 模板

路径：

```text
templates/architecture.md
```

适合描述系统架构，例如：

- 系统目标
- 核心组件
- 数据流
- 外部依赖
- 风险点
- 监控方式
- 扩展方案

### 5. Project Plan 模板

路径：

```text
templates/project-plan.md
```

适合规划项目，例如：

- 项目目标
- 范围边界
- 技术架构
- 阶段里程碑
- 风险管理
- 成功标准
- 交付物列表

## 示例提示词

### 生成 SOP

```text
/knowledge-asset 请把以下 Docker 部署流程整理成标准 SOP，包含前置条件、操作步骤、验证方式、回滚方案和常见问题。
```

### 生成故障排查文档

```text
/knowledge-asset 服务启动失败，日志显示端口被占用。请生成一份故障排查文档，包含症状、原因、诊断命令、解决方法和预防措施。
```

### 生成架构文档

```text
/knowledge-asset 请根据当前项目结构生成系统架构文档，包含模块职责、数据流、依赖关系、风险点和扩展建议。
```

### 生成项目计划

```text
/knowledge-asset 我要做一个自动化消息推送系统，请生成项目计划，包含目标、范围、架构、里程碑、风险和交付物。
```

### 生成知识笔记

```text
/knowledge-asset 请把 GitHub Actions 的基础用法整理成一份知识笔记，包含核心概念、常用配置、最佳实践和常见坑点。
```

## 推荐工作流

### 技术问题沉淀流程

```text
发现问题
  ↓
记录症状
  ↓
分析根因
  ↓
整理诊断命令
  ↓
沉淀解决步骤
  ↓
补充验证方法
  ↓
形成 Troubleshooting 文档
```

### 项目知识库建设流程

```text
项目目标
  ↓
架构设计
  ↓
开发计划
  ↓
部署 SOP
  ↓
故障排查手册
  ↓
运维 Runbook
  ↓
经验复盘文档
```

### 自动化任务沉淀流程

```text
明确目标
  ↓
确定输入输出
  ↓
编写脚本或命令
  ↓
定义执行步骤
  ↓
定义验证方式
  ↓
定义回滚方案
  ↓
保存为 SOP
```

## 最佳实践

### 1. 每个重要问题都沉淀为文档

不要只解决当前问题，应同时记录：

- 为什么出现
- 如何确认
- 如何修复
- 如何验证
- 如何避免再次发生

### 2. 优先使用模板

如果输出内容属于固定类型，优先使用 `templates/` 中的模板。

### 3. 保持文档可执行

好的知识资产不只是解释概念，还应该包含：

- 命令
- 示例
- 参数说明
- 预期输出
- 验证方式
- 回滚方式

### 4. 给文档添加标签

建议在知识笔记中增加标签，例如：

```markdown
## 标签

#Docker #Linux #Automation #Troubleshooting #Runbook
```

便于后续搜索和分类。

### 5. 定期复盘和更新

知识资产不是一次性文档，应随着系统变化持续更新。

## 常见问题

### 1. 这个 skill 和普通提示词有什么区别？

普通提示词通常只解决当前问题，而该 skill 会持续约束 Claude 的回答风格，让输出更像可保存、可复用、可执行的知识库内容。

### 2. 是否只能用于技术文档？

不是。它也可以用于：

- 学习笔记
- 操作手册
- 业务流程
- 项目管理
- 自动化流程
- 团队协作规范

但它对软件工程、Linux 自动化、运维、架构设计和知识库建设尤其适合。

### 3. 是否会自动写入 docs/ 目录？

该 skill 会倾向于生成可保存到 `docs/` 或 `knowledge-base/` 的内容。是否实际写入文件，取决于你是否要求 Claude 执行文件写入。

例如：

```text
/knowledge-asset 请生成 docs/deployment-sop.md
```

### 4. 可以和其他 Claude Code skill 一起使用吗？

可以。该 skill 更像一种输出和工作模式，可以和代码审查、验证、运行项目等技能配合使用。

### 5. 如何扩展模板？

可以在 `templates/` 目录中新增 Markdown 文件，例如：

```text
templates/runbook.md
templates/checklist.md
templates/api-doc.md
templates/security-review.md
```

然后在 `SKILL.md` 中补充对应规则。

## 后续规划

可考虑继续补充：

- `templates/runbook.md`
- `templates/checklist.md`
- `templates/api-doc.md`
- `templates/review-note.md`
- `templates/security-review.md`
- 中文版 `SKILL.md`
- 中英文双语模板
- 示例知识库目录结构

## 许可证

当前尚未指定许可证。正式公开复用前，建议补充 `LICENSE` 文件，例如：

- MIT License
- Apache License 2.0
- CC BY 4.0

## 相关链接

- GitHub 仓库：<https://github.com/stillness990/knowledge-asset-skills>
- Claude Code Skills：用于扩展 Claude Code 行为和工作流的技能机制

## 标签

#ClaudeCode #Skill #KnowledgeAsset #Documentation #SOP #Runbook #Architecture #Troubleshooting #Automation

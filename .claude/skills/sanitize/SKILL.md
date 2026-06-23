---
name: sanitize
description: "Scan and desensitize projects by replacing sensitive strings (QQ IDs, API keys, personal paths, emails, phones, tokens) with placeholders, AND isolate runtime business data (state/telemetry/tasks/knowledge) via .gitignore. Use when user asks to sanitize, desensitize, clean, or publish a project. Supports one-click publish with preflight checks (remote divergence + tag collision) and push retry."
---

# Sanitize Skill (v2)

## 用途

项目脱敏工具 - 扫描并处理项目中的敏感信息,确保代码可以安全公开、推送到公共仓库。

> **v2 核心理念:敏感信息分两类,用两种武器处理**
>
> | 类别 | 例子 | 处理方式 |
> |---|---|---|
> | **敏感字符串** | API key、token、QQ、邮箱、手机、webhook、个人路径 | 正则替换成占位符 |
> | **运行态业务数据** | state/telemetry/tasks.json、knowledge 产出、日志 | `.gitignore` 整体排除(不入库) |
>
> ⚠️ 教训:运行态数据不含密钥但泄露隐私,正则扫不出来。只做字符串脱敏会漏掉这些。两者缺一不可。

支持三种工作模式:

| 模式 | 命令 | 说明 |
|------|------|------|
| **扫描** | `scan` | 仅检测不修改,报告敏感字符串 + 运行态数据 |
| **脱敏** | `apply` | 扫描并替换敏感信息 + 自动写入 .gitignore 排除运行态数据 |
| **一键发布** | `publish` | 复制项目 → 脱敏 → 前置检查 → Git 推送(带重试) |

## 支持检测的敏感类型(8 类)

| 类型 | 说明 | 默认开启 |
|------|------|---------|
| QQ 号 | 5-11 位 QQ 号码 | ✅ |
| API Key | Anthropic / OpenAI / Google / GitHub 等 | ✅ |
| Access Token | .env 中的 access_token | ✅ |
| 个人路径 | /home/xxx 或 /Users/xxx | ✅ |
| 邮箱地址 | user@domain.com | ✅ |
| 中国手机号 | 1 开头的 11 位号码 | ✅ |
| 内网 IP | 10.x / 172.16-31.x / 192.168.x | ❌ |
| Webhook URL | Slack / Discord / 企业微信 | ✅ |

## 行为规则

1. 先扫描报告,再执行替换,不让用户盲目操作
2. scan 模式仅报告不修改,apply 模式执行替换
3. 替换为统一占位符（`<QQ_ID>`、`<API_KEY>`、`<PROJECT_PATH>` 等）
4. 自动排除 `.git`、`node_modules`、`.venv`、`__pycache__` 等目录
5. 只处理文本文件,跳过二进制

## v2 运行态业务数据隔离(重要补充)

除了字符串脱敏,v2 会检测并隔离**运行态业务数据**——这些不含密钥但泄露隐私的文件:

| 类型 | 路径模式 | 处理 |
|------|---------|------|
| v5 状态层 | `.claude/state/*.json`、`.claude/state/telemetry/*` | .gitignore 排除 |
| 检查点 | `.claude/state/checkpoint/*.json` | 排除(保留 .gitkeep) |
| 任务台账 | `**/task_ledger/tasks.json` | 排除/清空模板 |
| 学习状态 | `**/learning_state/state.json` | 排除/清空模板 |
| 知识产出 | `**/knowledge/**` | 排除内容(保留 .gitkeep) |
| 学习数据 | `practice/*` | 排除 |
| 运行日志 | `*.jsonl`、`execution-timeline.jsonl` | 排除 |

- **模板保留**:`.gitkeep`、`README.md`、`schema.md/json` 不被当作运行数据
- **scan** 会报告运行态数据命中;**apply** 会自动向 `.gitignore` 写入排除规则
- **已被 git 跟踪的脉数据**:.gitignore 不生效,需 `git rm --cached <file>` 或清空成空模板
- **代码路径例外**:代码里的路径不要替成 `<PROJECT_PATH>`(会破坏运行),应改**动态定位**(`os.path.dirname(__file__)`)

## v2 发布前置检查与推送重试

`publish` 推送前自动运行 `preflight_check`:
- **远程分叉检测**:远程是否领先本地、是否已分叉(force 推送会重写历史)
- **tag 撞号检查**:列出远程现有 tag,避免版本号冲突
- **推送重试**:`git_push_retry` 应对 `gnutls_handshake`/TLS 等网络拖动,自动重试 3 次

## 使用方式

### 模式一:仅扫描

```bash
python sanitize.py scan /path/to/project
python sanitize.py scan /path/to/project -v          # 显示全部匹配
python sanitize.py scan /path/to/project --only qq_id,api_key
```

### 模式二:执行脱敏

```bash
python sanitize.py apply /path/to/project
python sanitize.py apply /path/to/project -v
python sanitize.py apply /path/to/project --exclude tests,docs
```

### 模式三:一键发布(推荐)

完整的「复制 → 脱敏 → 推送」工作流,输出一个可安全上传到 GitHub 的干净项目:

```bash
python sanitize.py publish /path/to/source \
    --name my-project \
    --remote git@github.com:user/my-project.git
```

参数说明:

| 参数 | 必需 | 说明 |
|------|------|------|
| `source` | ✅ | 源项目路径 |
| `--name` / `-n` | ✅ | 目标目录名,会创建在 `/media/ww/...` 下 |
| `--remote` / `-r` | ✅ | Git 远程仓库地址 |
| `--branch` / `-b` | 否 | 目标分支(默认 `main`) |
| `--force` / `-f` | 否 | 强制覆盖已存在的目标目录 |
| `--no-push` | 否 | 跳过推送,仅复制+脱敏 |
| `--only` | 否 | 仅检查指定敏感类型 |
| `--exclude` | 否 | 排除指定目录 |
| `--verbose` / `-v` | 否 | 显示全部匹配详情 |

**工作流步骤:**

```
[1/3] 复制项目
  rsync -a (排除 .git .venv node_modules 等)
  源 → /media/ww/d1f01292-c940-497e-8051-a0b76acd008c/<name>

[2/3] 脱敏处理
  扫描所有文件 → 替换敏感信息 → 打印报告

[3/3] Git 推送
  git init → 创建 .gitignore → git add -A → git commit → git push --force
```

**示例:**

```bash
# 发布 agent-qq 项目
python sanitize.py publish /home/user/my-project \
    -n my-project-sanitized \
    -r git@github.com:your-username/my-project.git

# 发布 skill-os-complete
python sanitize.py publish /path/to/skill-os-complete \
    -n skill-os \
    -r git@github.com:your-username/skill-os-complete.git \
    -f
```

## 输出格式

```
============================================================
  脱敏扫描报告
============================================================
  扫描文件:42
  发现匹配:56
  修改文件:4
============================================================

  [QQ 号] (13 处)
    config.py:15  123456789 → <QQ_ID>
    ...

============================================================
  一键发布:/home/user/my-project → /media/user/backup/my-project
============================================================

[1/3] 复制项目...
  ✓ 复制完成

[2/3] 脱敏处理...
============================================================
  脱敏扫描报告 ...(略)
============================================================

[3/3] Git 推送...
  ✓ 远程仓库:git@github.com:user/repo.git
  ✓ 已推送

============================================================
  发布完成 ✓
  本地:/media/ww/d1f01292-c940-497e-8051-a0b76acd008c/agent-qq
  远程:git@github.com:user/repo.git
============================================================
```

## 典型工作流

1. **日常检查** → `scan` 查看项目中有哪些敏感信息
2. **准备发布** → `apply` 原地脱敏替换
3. **完整发布** → `publish` 一键复制+脱敏+推送

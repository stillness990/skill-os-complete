---
name: sanitize
description: "Scan and desensitize projects by replacing sensitive data (QQ IDs, API keys, personal paths, emails, phones, tokens) with placeholders. Use when user asks to sanitize, desensitize, clean, or prepare a project for publishing. Also supports one-click publish: copy → sanitize → git push."
---

# Sanitize Skill

## 用途

项目脱敏工具 — 扫描并替换项目中的敏感信息，确保代码可以安全公开、推送到公共仓库。支持三种工作模式：

| 模式 | 命令 | 说明 |
|------|------|------|
| **扫描** | `scan` | 仅检测不修改，报告有哪些敏感信息 |
| **脱敏** | `apply` | 扫描并替换敏感信息 |
| **一键发布** | `publish` | 复制项目 → 脱敏 → Git 推送，全自动 |

## 支持检测的敏感类型（8 类）

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

1. 先扫描报告，再执行替换，不让用户盲目操作
2. scan 模式仅报告不修改，apply 模式执行替换
3. 替换为统一占位符（`<QQ_ID>`、`<API_KEY>`、`<PROJECT_PATH>` 等）
4. 自动排除 `.git`、`node_modules`、`.venv`、`__pycache__` 等目录
5. 只处理文本文件，跳过二进制

## 使用方式

### 模式一：仅扫描

```bash
python sanitize.py scan /path/to/project
python sanitize.py scan /path/to/project -v          # 显示全部匹配
python sanitize.py scan /path/to/project --only qq_id,api_key
```

### 模式二：执行脱敏

```bash
python sanitize.py apply /path/to/project
python sanitize.py apply /path/to/project -v
python sanitize.py apply /path/to/project --exclude tests,docs
```

### 模式三：一键发布（推荐）

完整的「复制 → 脱敏 → 推送」工作流，输出一个可安全上传到 GitHub 的干净项目：

```bash
python sanitize.py publish /path/to/source \
    --name my-project \
    --remote git@github.com:user/my-project.git
```

参数说明：

| 参数 | 必需 | 说明 |
|------|------|------|
| `source` | ✅ | 源项目路径 |
| `--name` / `-n` | ✅ | 目标目录名，会创建在 `/media/ww/...` 下 |
| `--remote` / `-r` | ✅ | Git 远程仓库地址 |
| `--branch` / `-b` | 否 | 目标分支（默认 `main`） |
| `--force` / `-f` | 否 | 强制覆盖已存在的目标目录 |
| `--no-push` | 否 | 跳过推送，仅复制+脱敏 |
| `--only` | 否 | 仅检查指定敏感类型 |
| `--exclude` | 否 | 排除指定目录 |
| `--verbose` / `-v` | 否 | 显示全部匹配详情 |

**工作流步骤：**

```
[1/3] 复制项目
  rsync -a （排除 .git .venv node_modules 等）
  源 → /media/ww/d1f01292-c940-497e-8051-a0b76acd008c/<name>

[2/3] 脱敏处理
  扫描所有文件 → 替换敏感信息 → 打印报告

[3/3] Git 推送
  git init → 创建 .gitignore → git add -A → git commit → git push --force
```

**示例：**

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
  扫描文件：42
  发现匹配：56
  修改文件：4
============================================================

  [QQ 号] (13 处)
    config.py:15  123456789 → <QQ_ID>
    ...

============================================================
  一键发布：/home/user/my-project → /media/user/backup/my-project
============================================================

[1/3] 复制项目...
  ✓ 复制完成

[2/3] 脱敏处理...
============================================================
  脱敏扫描报告 ...（略）
============================================================

[3/3] Git 推送...
  ✓ 远程仓库：git@github.com:user/repo.git
  ✓ 已推送

============================================================
  发布完成 ✓
  本地：/media/ww/d1f01292-c940-497e-8051-a0b76acd008c/agent-qq
  远程：git@github.com:user/repo.git
============================================================
```

## 典型工作流

1. **日常检查** → `scan` 查看项目中有哪些敏感信息
2. **准备发布** → `apply` 原地脱敏替换
3. **完整发布** → `publish` 一键复制+脱敏+推送

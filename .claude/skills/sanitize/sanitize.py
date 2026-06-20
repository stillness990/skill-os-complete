#!/usr/bin/env python3
"""
项目脱敏脚本 — 扫描并替换项目中的敏感信息。

用法：
    # 仅扫描报告（不修改）
    python sanitize.py scan /path/to/project

    # 执行脱敏（替换敏感信息）
    python sanitize.py apply /path/to/project

    # 一键发布：复制 → 脱敏 → 推送
    python sanitize.py publish /path/to/project --name my-project --remote git@github.com:user/my-project.git

    # 指定自定义规则文件
    python sanitize.py scan /path/to/project --rules my_rules.json

    # 排除特定目录
    python sanitize.py apply /path/to/project --exclude tests,fixtures

    # 只检查特定模式
    python sanitize.py scan /path/to/project --only qq_id,api_key
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# ── 默认敏感模式 ────────────────────────────────────────────

DEFAULT_PATTERNS = {
    "qq_id": {
        "label": "QQ 号",
        "patterns": [
            r"\b[1-9]\d{4,10}\b",  # 5-11 位数字
        ],
        "replacement": "<QQ_ID>",
        "context_keywords": ["qq", "admin", "user", "napcat", "qq_id", "qqid"],
        "require_context": True,  # 需要上下文关键词才触发
    },
    "api_key": {
        "label": "API Key / Token",
        "patterns": [
            r"sk-ant-[a-zA-Z0-9_-]{20,}",      # Anthropic
            r"sk-[a-zA-Z0-9]{20,}",             # OpenAI
            r"AIza[a-zA-Z0-9_-]{30,}",          # Google
            r"ghp_[a-zA-Z0-9]{30,}",            # GitHub PAT
            r"gho_[a-zA-Z0-9]{30,}",            # GitHub OAuth
            r"xox[bpras]-[a-zA-Z0-9-]{10,}",    # Slack
        ],
        "replacement": "<API_KEY>",
        "context_keywords": ["key", "token", "api", "secret", "auth", "bearer"],
        "require_context": True,
    },
    "access_token": {
        "label": "Access Token",
        "patterns": [
            # 仅匹配 .env / shell 中的简单赋值，排除 Python 代码
            r'(?i)(?:_)?ACCESS_TOKEN\s*=\s*(?!#|\$|[a-z])[^\s"\']{8,}',
        ],
        "replacement": "ACCESS_TOKEN=",
        "context_keywords": [],
        "require_context": False,
    },
    "personal_path": {
        "label": "个人路径",
        "patterns": [
            r"/home/\w+/[^\s\"'&\n]*",          # Linux home
            r"/Users/\w+/[^\s\"'&\n]*",         # macOS home
        ],
        "replacement": "/path/to/<USER>/...",
        "context_keywords": [],
        "require_context": False,
    },
    "email": {
        "label": "邮箱地址",
        "patterns": [
            r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        ],
        "replacement": "<EMAIL>",
        "context_keywords": [],
        "require_context": False,
        # 排除以 git@ / npm@ / pip@ 开头的 VCS/工具地址
        "exclude_starts_with": ["git@", "npm@", "pip@", "ssh@"],
    },
    "phone": {
        "label": "中国手机号",
        "patterns": [
            r"\b1[3-9]\d{9}\b",
        ],
        "replacement": "<PHONE>",
        "context_keywords": [],
        "require_context": False,
    },
    "private_ip": {
        "label": "内网 IP",
        "patterns": [
            r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b",
            r"\b(172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b",
            r"\b(192\.168\.\d{1,3}\.\d{1,3})\b",
        ],
        "replacement": "<IP>",
        "context_keywords": [],
        "require_context": False,
        "enabled_by_default": False,
    },
    "webhook_url": {
        "label": "Webhook / URL Token",
        "patterns": [
            r"https://[^\s\"'&\n]*token[=:][^\s\"'&\n]+",
            r"https://[^\s\"'&\n]*key[=:][^\s\"'&\n]+",
            r"https://hooks\.slack\.com/[^\s\"'&\n]+",
            r"https://discord\.com/api/webhooks/[^\s\"'&\n]+",
            r"https://qyapi\.weixin\.qq\.com/cgi-bin/[^\s\"'&\n]+",
        ],
        "replacement": "<WEBHOOK_URL>",
        "context_keywords": [],
        "require_context": False,
    },
}

# ═══════════════════════════════════════════════════════════
# 文本文件扩展名
# ═══════════════════════════════════════════════════════════
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".h",
    ".sh", ".bash", ".zsh", ".fish",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".md", ".txt", ".rst", ".tex",
    ".html", ".css", ".scss", ".xml", ".svg",
    ".env", ".env.example", ".gitignore", ".dockerignore",
    ".sql", ".graphql",
    ".rb", ".php", ".swift", ".kt", ".scala",
    ".tf", ".hcl",
}

# 始终排除的目录
ALWAYS_EXCLUDE = {
    ".git", ".svn", ".hg",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".venv", "venv", "vendor",
    ".idea", ".vscode", ".DS_Store",
    "logs", "*.log",
}

# ═══════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════


@dataclass
class Match:
    file: str
    line: int
    pattern_name: str
    label: str
    original: str
    replacement: str


@dataclass
class ScanResult:
    matches: list[Match] = field(default_factory=list)
    files_scanned: int = 0
    files_modified: int = 0

    @property
    def match_count(self) -> int:
        return len(self.matches)


# ═══════════════════════════════════════════════════════════
# 扫描逻辑
# ═══════════════════════════════════════════════════════════


def compile_patterns(selected: set[str] | None = None) -> dict[str, dict]:
    """编译并返回需要检查的模式。

    selected: 只使用这些 key；None 表示使用所有默认启用的。
    """
    result = {}
    for key, spec in DEFAULT_PATTERNS.items():
        if selected and key not in selected:
            continue
        if not selected and not spec.get("enabled_by_default", True):
            continue
        result[key] = {
            **spec,
            "compiled": [re.compile(p) for p in spec["patterns"]],
        }
    return result


def should_scan_file(filepath: Path, exclude_dirs: set[str]) -> bool:
    """判断文件是否应该被扫描。"""
    parts = set(filepath.parts)
    if parts & ALWAYS_EXCLUDE:
        return False
    if parts & exclude_dirs:
        return False
    if filepath.suffix and filepath.suffix not in TEXT_EXTENSIONS:
        return False
    if filepath.name.startswith(".") and filepath.suffix != ".env":
        return False
    return True


def check_context(line_lower: str, keywords: list[str]) -> bool:
    """检查行上下文是否包含至少一个关键词。"""
    if not keywords:
        return True
    return any(kw.lower() in line_lower for kw in keywords)


def scan_file(filepath: Path, patterns: dict[str, dict]) -> list[Match]:
    """扫描单个文件，返回匹配列表。"""
    matches = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return matches

    lines = content.split("\n")
    for i, line in enumerate(lines, start=1):
        line_lower = line.lower()
        for key, spec in patterns.items():
            if spec.get("require_context", False) and not check_context(line_lower, spec.get("context_keywords", [])):
                continue
            for regex in spec["compiled"]:
                for m in regex.finditer(line):
                    original = m.group(0)
                    # 跳过已经是占位符的内容
                    if original.startswith("<") and original.endswith(">"):
                        continue
                    # 某些模式需要额外过滤
                    if key == "qq_id" and not _is_likely_qq_id(original, line_lower):
                        continue
                    if key == "email" and any(original.startswith(p) for p in spec.get("exclude_starts_with", [])):
                        continue
                    replacement = _build_replacement(key, spec, original)
                    matches.append(Match(
                        file=str(filepath),
                        line=i,
                        pattern_name=key,
                        label=spec["label"],
                        original=original,
                        replacement=replacement,
                    ))
    return matches


def _is_likely_qq_id(digits: str, line_lower: str) -> bool:
    """减少 QQ 号误报：需要上下文关键词或合理长度。"""
    # 6 位以下容易误报（端口号、时间戳等）
    if len(digits) < 6:
        return False
    # 6-11 位 + 上下文
    context_words = ["qq", "admin", "user", "id", "qqid", "uin", "sender", "receiver"]
    if any(w in line_lower for w in context_words):
        return True
    # 9-10 位很可能是 QQ 号
    if len(digits) >= 9:
        return True
    return False


def _build_replacement(key: str, spec: dict, original: str) -> str:
    """根据模式类型构建替换值。"""
    base = spec["replacement"]
    if key == "personal_path":
        return "<PROJECT_PATH>"
    if key == "access_token":
        return "ACCESS_TOKEN="
    return base


def scan_directory(root: Path, patterns: dict[str, dict], exclude_dirs: set[str]) -> ScanResult:
    """递归扫描目录。"""
    result = ScanResult()
    for filepath in root.rglob("*"):
        if not filepath.is_file():
            continue
        if not should_scan_file(filepath, exclude_dirs):
            continue
        result.files_scanned += 1
        matches = scan_file(filepath, patterns)
        result.matches.extend(matches)
    return result


def apply_replacements(result: ScanResult, dry_run: bool = False) -> int:
    """逐行替换，按行号降序处理避免偏移，精确替换每个匹配。

    策略：不是用 str.replace 全局替换（同名路径出现在多处会出错），
    而是在指定行上做定向替换：从右往左替换该行上的匹配文本。
    """
    # 按文件分组
    by_file: dict[str, list[Match]] = {}
    for m in result.matches:
        by_file.setdefault(m.file, []).append(m)

    for filepath_str, file_matches in by_file.items():
        try:
            lines = Path(filepath_str).read_text(encoding="utf-8").split("\n")
        except OSError:
            continue

        changed = False
        # 按行号降序，同一行内按匹配文本长度降序（先替换长的，避免短串干扰）
        file_matches.sort(key=lambda x: (x.line, len(x.original)), reverse=True)

        seen: set[tuple[int, str]] = set()
        for m in file_matches:
            idx = m.line - 1
            if idx < 0 or idx >= len(lines):
                continue
            # 跳过同一位置同一内容的重复匹配
            key = (m.line, m.original)
            if key in seen:
                continue
            seen.add(key)

            if m.original != m.replacement and m.original in lines[idx]:
                lines[idx] = lines[idx].replace(m.original, m.replacement, 1)
                changed = True

        if changed:
            result.files_modified += 1
            if not dry_run:
                Path(filepath_str).write_text("\n".join(lines), encoding="utf-8")

    return result.files_modified


# ═══════════════════════════════════════════════════════════
# 输出
# ═══════════════════════════════════════════════════════════


def print_report(result: ScanResult, verbose: bool = False) -> None:
    """打印扫描/替换报告。"""
    if result.match_count == 0:
        print("✓ 未发现敏感信息。")
        return

    # 按类型分组统计
    by_type: dict[str, list[Match]] = {}
    for m in result.matches:
        by_type.setdefault(m.label, []).append(m)

    print(f"\n{'='*60}")
    print(f"  脱敏扫描报告")
    print(f"{'='*60}")
    print(f"  扫描文件：{result.files_scanned}")
    print(f"  发现匹配：{result.match_count}")
    print(f"  修改文件：{result.files_modified}")
    print(f"{'='*60}\n")

    for label, matches in sorted(by_type.items()):
        print(f"  [{label}] ({len(matches)} 处)")
        if verbose:
            for m in matches:
                fname = Path(m.file).name
                print(f"    {fname}:{m.line}  {m.original[:60]} → {m.replacement}")
        else:
            # 显示每组前 3 条
            for m in matches[:3]:
                fname = Path(m.file).name
                print(f"    {fname}:{m.line}  {m.original[:60]} → {m.replacement}")
            if len(matches) > 3:
                print(f"    ... 还有 {len(matches) - 3} 处")
        print()

    print(f"  共 {len(by_type)} 类敏感信息，{result.match_count} 处匹配。\n")


# ═══════════════════════════════════════════════════════════
# 一键发布：复制 → 脱敏 → 推送
# ═══════════════════════════════════════════════════════════

PUBLISH_ROOT = Path("/media/ww/d1f01292-c940-497e-8051-a0b76acd008c")

# rsync 排除项
RSYNC_EXCLUDES = [
    "--exclude=.git",
    "--exclude=__pycache__",
    "--exclude=*.pyc",
    "--exclude=.pytest_cache",
    "--exclude=.mypy_cache",
    "--exclude=.ruff_cache",
    "--exclude=.venv",
    "--exclude=venv",
    "--exclude=node_modules",
    "--exclude=.idea",
    "--exclude=.vscode",
    "--exclude=.DS_Store",
    "--exclude=logs",
    "--exclude=*.log",
]


def copy_project(source: Path, dest: Path, force: bool = False) -> bool:
    """将 source 项目复制到 dest，使用 rsync 保留权限。

    返回 True 表示成功。
    """
    if dest.exists():
        if force:
            import shutil
            shutil.rmtree(dest)
            print(f"  ✓ 已覆盖：{dest}")
        else:
            print(f"  ✗ 目标已存在：{dest}")
            print(f"    使用 --force 强制覆盖")
            return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["rsync", "-a"] + RSYNC_EXCLUDES + [str(source) + "/", str(dest)]
    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ 复制失败：{result.stderr}")
        return False
    print(f"  ✓ 复制完成：{source} → {dest}")
    return True


def init_and_push(project_dir: Path, remote_url: str, branch: str = "main", dry_run: bool = False) -> bool:
    """在 project_dir 中初始化 git、提交并推送。

    返回 True 表示成功。
    """
    import subprocess

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git"] + list(args), cwd=str(project_dir), capture_output=True, text=True)

    # 检查是否已是 git 仓库
    if not (project_dir / ".git").exists():
        r = git("init")
        if r.returncode != 0:
            print(f"  ✗ git init 失败：{r.stderr}")
            return False
        # 重命名默认分支
        git("branch", "-m", branch)

    # 设置 git 用户信息（如果未配置）
    for key, value in [("user.name", "stillness990"), ("user.email", "<EMAIL>")]:
        cr = git("config", key)
        if not cr.stdout.strip():
            git("config", key, value)

    # 创建 .gitignore（如不存在）
    gitignore = project_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("# Python\n__pycache__/\n*.py[cod]\n.pytest_cache/\n.venv/\n\n# IDE\n.idea/\n.vscode/\n.DS_Store\n\n# Logs\n*.log\n")

    # 添加并提交
    git("add", "-A")
    r = git("commit", "-m", "chore: publish sanitized project")
    if r.returncode != 0:
        if "nothing to commit" in r.stdout + r.stderr:
            print("  ⚠ 无变更需要提交，跳过。")
        else:
            print(f"  ✗ 提交失败：{r.stderr.strip()}")
            return False

    # 设置 remote
    git("remote", "remove", "origin")
    git("remote", "add", "origin", remote_url)
    print(f"  ✓ 远程仓库：{remote_url}")

    if dry_run:
        print("  [dry-run] 跳过推送。")
        return True

    # 推送
    r = git("push", "--force", "origin", branch)
    if r.returncode != 0:
        print(f"  ✗ 推送失败：{r.stderr.strip()}")
        if r.stdout.strip():
            print(f"  stdout: {r.stdout.strip()}")
        return False
    print(f"  ✓ 已推送到 {remote_url} ({branch})")
    return True


def publish_project(
    source: Path,
    name: str,
    remote: str,
    branch: str = "main",
    force: bool = False,
    no_push: bool = False,
    only: set[str] | None = None,
    exclude: set[str] | None = None,
    verbose: bool = False,
) -> int:
    """完整发布流程：复制 → 脱敏 → git 推送。

    返回 0 表示成功。
    """
    dest = PUBLISH_ROOT / name

    print(f"\n{'='*60}")
    print(f"  一键发布：{source} → {dest}")
    print(f"{'='*60}\n")

    # ── Step 1: 复制 ──
    print("[1/3] 复制项目...")
    if not copy_project(source, dest, force=force):
        return 1

    # ── Step 2: 脱敏 ──
    print("\n[2/3] 脱敏处理...")
    patterns = compile_patterns(only)
    exclude_dirs = exclude or set()
    result = scan_directory(dest, patterns, exclude_dirs)
    apply_replacements(result, dry_run=False)
    print_report(result, verbose=verbose)

    # ── Step 3: Git 推送 ──
    print("[3/3] Git 推送...")
    if not init_and_push(dest, remote, branch=branch, dry_run=no_push):
        return 1

    print(f"\n{'='*60}")
    print(f"  发布完成 ✓")
    print(f"  本地：{dest}")
    print(f"  远程：{remote}")
    print(f"{'='*60}\n")
    return 0


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════


def main() -> int:
    parser = argparse.ArgumentParser(
        description="项目脱敏工具 — 扫描并替换敏感信息",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python sanitize.py scan /path/to/project
  python sanitize.py apply /path/to/project --verbose
  python sanitize.py publish /path/to/project --name my-project --remote git@github.com:user/repo.git
  python sanitize.py scan . --only qq_id,api_key
  python sanitize.py apply . --exclude tests,docs
        """,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── scan / apply ──
    for cmd in ("scan", "apply"):
        p = sub.add_parser(cmd, help="scan=仅扫描报告 / apply=执行替换")
        p.add_argument("target", help="目标项目目录")
        p.add_argument("--rules", default=None, help="自定义规则 JSON 文件（可选）")
        p.add_argument("--only", default=None, help="只检查指定类型，逗号分隔（如：qq_id,api_key）")
        p.add_argument("--exclude", default=None, help="排除目录，逗号分隔")
        p.add_argument("--verbose", "-v", action="store_true", help="显示所有匹配详情")

    # ── publish ──
    pub = sub.add_parser("publish", help="一键发布：复制项目 → 脱敏 → Git 推送")
    pub.add_argument("source", help="源项目目录")
    pub.add_argument("--name", "-n", required=True, help="项目名称（目标目录名）")
    pub.add_argument("--remote", "-r", required=True, help="Git 远程仓库地址")
    pub.add_argument("--branch", "-b", default="main", help="目标分支（默认 main）")
    pub.add_argument("--force", "-f", action="store_true", help="强制覆盖已存在的目标目录")
    pub.add_argument("--no-push", action="store_true", help="跳过推送（仅复制+脱敏）")
    pub.add_argument("--only", default=None, help="只检查指定敏感类型（逗号分隔）")
    pub.add_argument("--exclude", default=None, help="脱敏时排除的目录（逗号分隔）")
    pub.add_argument("--verbose", "-v", action="store_true", help="显示所有匹配详情")

    args = parser.parse_args()

    # ── dispatch ──
    if args.command == "publish":
        source = Path(args.source).resolve()
        if not source.is_dir():
            print(f"✗ 目录不存在：{source}", file=sys.stderr)
            return 1
        only = set(args.only.split(",")) if args.only else None
        exclude = set(args.exclude.split(",")) if args.exclude else None
        return publish_project(
            source=source,
            name=args.name,
            remote=args.remote,
            branch=args.branch,
            force=args.force,
            no_push=args.no_push,
            only=only,
            exclude=exclude,
            verbose=args.verbose,
        )

    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"✗ 目录不存在：{target}", file=sys.stderr)
        return 1

    selected = set(args.only.split(",")) if args.only else None
    patterns = compile_patterns(selected)
    if not patterns:
        print("✗ 没有可用的检查模式。", file=sys.stderr)
        return 1

    exclude_dirs = set(args.exclude.split(",")) if args.exclude else set()

    print(f"→ 扫描目录：{target}")
    if selected:
        print(f"→ 检查模式：{', '.join(selected)}")
    print(f"→ 模式：{'仅报告 (dry-run)' if args.command == 'scan' else '执行替换'}")

    result = scan_directory(target, patterns, exclude_dirs)
    if args.command == "apply":
        apply_replacements(result, dry_run=False)
    else:
        apply_replacements(result, dry_run=True)

    print_report(result, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

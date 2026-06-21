"""
Rollback Manager — 回滚管理器 (Phase 5)
Phase 5: 实现基于 ledger artifact_paths 的安全回滚

执行流程 (Step 1-5 对应 03_safe_mode_and_rollback.md):
Step 1 — 从 ledger 读取 artifact_paths
Step 2 — 对每个 artifact_path 执行路径安全校验
Step 3 — 删除安全 artifact
Step 4 — 清理 route cache / 状态
Step 5 — 写回 rollback 结果

安全规则:
- artifact_paths 必须为 repo-root 相对路径
- 禁止 ../ 向上遍历
- 越界路径拒绝删除并记录 security error
- 安全异常时触发 safe_mode 或返回异常状态
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Rollback result data structures ──────────────────────

@dataclass
class CleanedArtifact:
    """已清理 artifact 记录"""
    path: str
    full_path: str
    existed: bool
    deleted: bool
    error: str = ""


@dataclass
class RejectedArtifact:
    """被拒绝的 artifact 记录"""
    path: str
    reason: str
    severity: str = "critical"  # critical / warning


@dataclass
class RollbackResult:
    """Rollback 执行结果"""
    route_id: str = ""
    rollback_status: str = "not_executed"  # success / partial / failed / not_executed
    cleaned_artifacts: list[CleanedArtifact] = field(default_factory=list)
    rejected_artifacts: list[RejectedArtifact] = field(default_factory=list)
    security_errors: list[str] = field(default_factory=list)
    cleaned_count: int = 0
    rejected_count: int = 0
    error_count: int = 0
    executed_at: str = ""
    updated_at: str = ""

    @property
    def has_security_errors(self) -> bool:
        return len(self.security_errors) > 0

    @property
    def all_clean(self) -> bool:
        return self.rejected_count == 0 and self.error_count == 0

    def to_dict(self) -> dict:
        return {
            "rollback_status": self.rollback_status,
            "cleaned_artifacts": [
                {"path": c.path, "deleted": c.deleted, "error": c.error}
                for c in self.cleaned_artifacts
            ],
            "rejected_artifacts": [
                {"path": r.path, "reason": r.reason, "severity": r.severity}
                for r in self.rejected_artifacts
            ],
            "security_errors": self.security_errors,
            "cleaned_count": self.cleaned_count,
            "rejected_count": self.rejected_count,
            "error_count": self.error_count,
            "executed_at": self.executed_at,
            "updated_at": self.updated_at,
        }


class RollbackManager:
    """
    回滚管理器 — 从 ledger 读取 artifact_paths 并安全清理。

    硬约束 (来自 03_safe_mode_and_rollback.md):
    - 不从 ledger 之外的来源获取要删除的路径
    - 每个路径必须经过 normalize → resolve → boundary check
    - 越界路径拒绝删除
    - 仅删除 repo-root 内的 artifact
    """

    def __init__(self, repo_root: Optional[str] = None):
        self._repo_root = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
        self._last_result: Optional[RollbackResult] = None

    @property
    def repo_root(self) -> Path:
        return self._repo_root

    @property
    def last_result(self) -> Optional[RollbackResult]:
        return self._last_result

    # ── Main rollback entry ───────────────────────────────

    def execute(
        self,
        route_id: str,
        artifact_paths: list[str],
        safe_mode_active: bool = False,
        dry_run: bool = False,
    ) -> RollbackResult:
        """
        执行回滚。

        参数:
            route_id: 关联 route ID
            artifact_paths: 从 ledger 读取的 artifact 相对路径列表
            safe_mode_active: 是否在 safe_mode 中 (保守执行)
            dry_run: True 则不实际删除, 只做安全校验

        返回:
            RollbackResult
        """
        result = RollbackResult(
            route_id=route_id,
            executed_at=_now_iso(),
        )

        if not artifact_paths:
            result.rollback_status = "success"  # nothing to clean
            result.updated_at = _now_iso()
            self._last_result = result
            return result

        for rel_path in artifact_paths:
            # Step 2: 路径安全校验
            is_safe, reason = self._validate_path(rel_path)

            if not is_safe:
                rejected = RejectedArtifact(
                    path=rel_path,
                    reason=reason,
                    severity="critical",
                )
                result.rejected_artifacts.append(rejected)
                result.rejected_count += 1
                result.security_errors.append(f"拒绝删除: {rel_path} — {reason}")
                continue

            # Step 3: 安全删除
            full_path = self._repo_root / rel_path
            cleaned = self._clean_artifact(full_path, rel_path, dry_run)
            result.cleaned_artifacts.append(cleaned)
            if cleaned.deleted:
                result.cleaned_count += 1
            if cleaned.error:
                result.error_count += 1

        # 判定最终状态
        if result.rejected_count > 0 and result.cleaned_count == 0:
            result.rollback_status = "failed"
        elif result.rejected_count > 0 or result.error_count > 0:
            result.rollback_status = "partial"
        else:
            result.rollback_status = "success"

        result.updated_at = _now_iso()
        self._last_result = result
        return result

    def rollback_route(
        self,
        route_id: str,
        ledger: dict,  # 从 ledger 读取的完整 task 数据
        safe_mode_active: bool = False,
        dry_run: bool = False,
    ) -> RollbackResult:
        """
        从 ledger 数据执行回滚 (Step 1: 读取 artifact_paths)。

        参数:
            route_id: 关联 route ID
            ledger: 从 ledger 读取的 task dict (包含 artifact_paths)
            safe_mode_active: 是否在 safe_mode 中
            dry_run: True 则不实际删除

        返回:
            RollbackResult
        """
        artifact_paths = ledger.get("artifact_paths", []) or []
        return self.execute(
            route_id=route_id,
            artifact_paths=artifact_paths,
            safe_mode_active=safe_mode_active,
            dry_run=dry_run,
        )

    # ── Path validation (Step 2) ──────────────────────────

    def _validate_path(self, rel_path: str) -> tuple[bool, str]:
        """
        路径安全校验。

        返回: (is_safe: bool, reason: str)
        """
        # Rule 1: 禁止空路径
        if not rel_path or not rel_path.strip():
            return False, "空路径"

        # Rule 2: 禁止 ../
        if ".." in rel_path:
            return False, f"路径包含 '..' (禁止向上遍历): {rel_path}"

        # Rule 3: 禁止绝对路径
        if os.path.isabs(rel_path):
            return False, f"不允许绝对路径: {rel_path}"

        # Rule 4: normalize + resolve + boundary check
        try:
            full_path = (self._repo_root / rel_path).resolve()
            repo_root_resolved = self._repo_root.resolve()

            if not str(full_path).startswith(str(repo_root_resolved)):
                return False, f"路径越出 repo root: {rel_path} → {full_path}"

        except Exception as e:
            return False, f"路径解析失败: {rel_path} — {e}"

        return True, "ok"

    def validate_path_public(self, rel_path: str) -> tuple[bool, str]:
        """公开的路径验证方法"""
        return self._validate_path(rel_path)

    # ── Artifact cleanup (Step 3) ─────────────────────────

    def _clean_artifact(
        self,
        full_path: Path,
        rel_path: str,
        dry_run: bool = False,
    ) -> CleanedArtifact:
        """安全删除单个 artifact"""
        existed = full_path.exists()

        if not existed:
            return CleanedArtifact(
                path=rel_path,
                full_path=str(full_path),
                existed=False,
                deleted=False,
                error="" if dry_run else "文件不存在，无需删除",
            )

        if dry_run:
            return CleanedArtifact(
                path=rel_path,
                full_path=str(full_path),
                existed=True,
                deleted=False,
                error="",  # dry_run is not an error
            )

        try:
            if full_path.is_file():
                full_path.unlink()
            elif full_path.is_dir():
                import shutil
                shutil.rmtree(full_path)
            return CleanedArtifact(
                path=rel_path,
                full_path=str(full_path),
                existed=True,
                deleted=True,
            )
        except Exception as e:
            return CleanedArtifact(
                path=rel_path,
                full_path=str(full_path),
                existed=True,
                deleted=False,
                error=str(e),
            )

    # ── Cache / state cleanup (Step 4) ────────────────────

    def clear_route_cache(self, route_id: str) -> None:
        """清理指定 route 的临时缓存 (内存级, 具体实现取决于 cache 存储)"""
        # Route cache 清理占位 — 实际实现取决于 cache 存储方式
        # 当前框架: route cache 在 memory 中, 由 Python GC 处理
        pass

    def get_last_result_summary(self) -> str:
        """获取最近一次 rollback 结果摘要"""
        if not self._last_result:
            return "No rollback executed"
        r = self._last_result
        return (
            f"Rollback({r.rollback_status}): "
            f"cleaned={r.cleaned_count}, rejected={r.rejected_count}, errors={r.error_count}"
        )

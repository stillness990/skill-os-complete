"""
Self-Healing Manager — 自愈管理器 (Phase 5)
Phase 5: 实现有限重试 + 同类型失败上限 + embedding fallback + 防递归

硬约束 (来自 03_safe_mode_and_rollback.md 和 P5-4):
- retry_count ≤ 3
- same_failure_type_count ≤ 2
- embedding_fail → immediate fallback (不重试)
- 不允许递归调用 self-healing
- 每次 retry 必须生成新的 route_id

恢复优先级:
1. 轻量重试 (仅限可恢复错误)
2. fallback route / fallback provider
3. 进入 SAFE MODE
4. 停止并输出 failure report
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from orchestration_types import FailureType, TaskStatus, SafeModeStatus


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_route_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"rte_{ts}_{short_uuid}"


# ── Healing config ───────────────────────────────────────

@dataclass
class HealingConfig:
    """自愈配置 (硬上限)"""
    max_retry_count: int = 3
    max_same_failure_type_count: int = 2
    embedding_fail_immediate_fallback: bool = True

    # 哪些 failure_type 允许重试
    retryable_failures: tuple = (
        FailureType.STAGE_TIMEOUT,
        FailureType.ARTIFACT_MISSING,
        FailureType.GUARD_REJECTED,
    )

    # embedding 失败不重试 (直接 fallback)
    no_retry_failures: tuple = (
        FailureType.EMBEDDING_UNAVAILABLE,
        FailureType.ROLLBACK_SECURITY,
        FailureType.ILLEGAL_TRANSITION,
    )


# ── Healing result ───────────────────────────────────────

@dataclass
class HealingDecision:
    """自愈决策"""
    action: str  # retry / fallback / safe_mode / stop / none
    reason: str
    new_route_id: str = ""
    retry_count: int = 0
    same_failure_count: int = 0
    decided_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "reason": self.reason,
            "new_route_id": self.new_route_id,
            "retry_count": self.retry_count,
            "same_failure_count": self.same_failure_count,
            "decided_at": self.decided_at,
        }


class SelfHealingManager:
    """
    自愈管理器 — 按优先级决策: retry → fallback → safe_mode → stop

    使用方式:
        healing = SelfHealingManager(safe_mode_manager)
        decision = healing.decide(failure_type, retry_count, same_failure_count)
        if decision.action == "retry":
            new_route_id = decision.new_route_id
            # 重新执行...
        elif decision.action == "safe_mode":
            safe_mode_manager.trigger(...)
    """

    def __init__(self, safe_mode_manager=None, config: Optional[HealingConfig] = None):
        self.config = config or HealingConfig()
        self._safe_mode_manager = safe_mode_manager  # 可选: SafeModeManager 实例
        self._healing_in_progress: bool = False  # 防递归标志
        self._decisions: list[HealingDecision] = []

    @property
    def is_healing(self) -> bool:
        """是否正在执行自愈 (防递归)"""
        return self._healing_in_progress

    @property
    def decisions(self) -> list[HealingDecision]:
        return list(self._decisions)

    # ── Main decision entry ───────────────────────────────

    def decide(
        self,
        failure_type: FailureType,
        retry_count: int = 0,
        same_failure_type_count: int = 0,
        safe_mode_active: bool = False,
    ) -> HealingDecision:
        """
        根据失败类型和当前计数决定自愈策略。

        参数:
            failure_type: 当前失败类型
            retry_count: 已重试次数
            same_failure_type_count: 同类型失败次数
            safe_mode_active: 当前是否已在 safe_mode 中

        返回:
            HealingDecision
        """
        # 防递归
        if self._healing_in_progress:
            decision = HealingDecision(
                action="stop",
                reason="Self-healing 递归调用被阻止",
                retry_count=retry_count,
                same_failure_count=same_failure_type_count,
            )
            self._decisions.append(decision)
            return decision

        self._healing_in_progress = True

        try:
            return self._do_decide(failure_type, retry_count, same_failure_type_count, safe_mode_active)
        finally:
            self._healing_in_progress = False

    def _do_decide(
        self,
        failure_type: FailureType,
        retry_count: int,
        same_failure_type_count: int,
        safe_mode_active: bool,
    ) -> HealingDecision:
        """决策核心逻辑"""

        # 如果已在 safe_mode, 收缩自愈
        if safe_mode_active:
            decision = HealingDecision(
                action="stop",
                reason="SAFE MODE 下禁用自愈",
                retry_count=retry_count,
                same_failure_count=same_failure_type_count,
            )
            self._decisions.append(decision)
            return decision

        # embedding 失败 → 立即 fallback (禁止重试)
        if failure_type in self.config.no_retry_failures:
            if failure_type == FailureType.EMBEDDING_UNAVAILABLE:
                decision = HealingDecision(
                    action="fallback",
                    reason="Embedding 不可用 → 立即 fallback 到 rule_only",
                    retry_count=retry_count,
                    same_failure_count=same_failure_type_count,
                )
            else:
                decision = HealingDecision(
                    action="safe_mode",
                    reason=f"{failure_type.value} 不可重试 → 触发 safe_mode",
                    retry_count=retry_count,
                    same_failure_count=same_failure_type_count,
                )
            self._decisions.append(decision)
            return decision

        # 硬上限检查
        if retry_count >= self.config.max_retry_count:
            decision = HealingDecision(
                action="safe_mode",
                reason=f"retry_count={retry_count} 达到上限 {self.config.max_retry_count}",
                retry_count=retry_count,
                same_failure_count=same_failure_type_count,
            )
            self._decisions.append(decision)
            return decision

        if same_failure_type_count >= self.config.max_same_failure_type_count:
            decision = HealingDecision(
                action="safe_mode",
                reason=f"same_failure_type_count={same_failure_type_count} 达到上限 {self.config.max_same_failure_type_count}",
                retry_count=retry_count,
                same_failure_count=same_failure_type_count,
            )
            self._decisions.append(decision)
            return decision

        # 可重试失败类型 → retry
        if failure_type in self.config.retryable_failures:
            decision = HealingDecision(
                action="retry",
                reason=f"{failure_type.value} 可重试 (attempt {retry_count + 1}/{self.config.max_retry_count})",
                new_route_id=_new_route_id(),
                retry_count=retry_count + 1,
                same_failure_count=same_failure_type_count,
            )
            self._decisions.append(decision)
            return decision

        # 未知失败 → fallback
        decision = HealingDecision(
            action="fallback",
            reason=f"未知失败类型 {failure_type.value} → fallback",
            retry_count=retry_count,
            same_failure_count=same_failure_type_count,
        )
        self._decisions.append(decision)
        return decision

    # ── Convenience: map failure type ─────────────────────

    @staticmethod
    def classify_failure(error_message: str) -> FailureType:
        """根据错误消息猜测 FailureType"""
        msg_lower = error_message.lower()
        if any(kw in msg_lower for kw in ("embedding", "embedd", "ollama", "nomic")):
            return FailureType.EMBEDDING_UNAVAILABLE
        if any(kw in msg_lower for kw in ("timeout", "timed out", "deadline")):
            return FailureType.STAGE_TIMEOUT
        if any(kw in msg_lower for kw in ("artifact", "missing file", "not found")):
            return FailureType.ARTIFACT_MISSING
        if any(kw in msg_lower for kw in ("transition", "illegal", "状态")):
            return FailureType.ILLEGAL_TRANSITION
        if any(kw in msg_lower for kw in ("guard", "blocked", "拒绝")):
            return FailureType.GUARD_REJECTED
        if any(kw in msg_lower for kw in ("rollback", "security", "越界", "out of bounds")):
            return FailureType.ROLLBACK_SECURITY
        return FailureType.UNKNOWN

    # ── Health check ─────────────────────────────────────

    def can_retry(self, retry_count: int, failure_type: FailureType) -> bool:
        """快速检查是否可以重试"""
        if retry_count >= self.config.max_retry_count:
            return False
        if failure_type in self.config.no_retry_failures:
            return False
        if self._healing_in_progress:
            return False
        return True

    def reset(self) -> None:
        """重置自愈状态 (测试用)"""
        self._decisions.clear()
        self._healing_in_progress = False

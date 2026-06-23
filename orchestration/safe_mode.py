"""
Safe Mode Manager — 安全模式管理器 (Phase 5)
Phase 5: 实现 SafeMode toggle, trigger 记录, 降级响应, ledger 写入

SafeMode 是全局安全开关，满足以下任一即触发:
- embedding / semantic routing 不可用
- rollback 安全异常 (越界路径)
- self-healing 达到上限
- execution_guard 发现关键结构性缺失

SafeMode 触发后:
- semantic-router 禁用/跳过
- workflow-resolver 退化为 rule_only_safe_mode
- self-healing 收缩/禁用
- rollback 保守执行
- 状态写入 ledger
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .orchestration_types import SafeModeStatus, ExecutionStatus, FailureType


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Trigger reason catalog ─────────────────────────────

SAFE_MODE_TRIGGERS = {
    "embedding_unavailable": "Embedding 服务不可达或模型不可用",
    "semantic_router_init_failed": "SemanticRouter 初始化失败",
    "rollback_path_out_of_bounds": "Rollback 检测到越界 artifact_path",
    "rollback_security_error": "Rollback 安全校验失败",
    "self_healing_limit_exceeded": "Self-healing retry/same_failure 超出上限",
    "execution_guard_critical": "Execution guard 发现关键结构性缺失",
    "manual_trigger": "手动触发 safe_mode",
}


@dataclass
class SafeModeRecord:
    """单次 SafeMode 触发记录"""
    triggered_at: str = field(default_factory=_now_iso)
    trigger_reason: str = ""
    route_id: str = ""
    workflow: str = ""
    stage_id: str = ""
    degraded_actions: list[str] = field(default_factory=list)
    safe_mode: bool = True


class SafeModeManager:
    """
    Safe Mode 管理器 — 全局单例模式。

    职责:
    - 管理 safe_mode 状态 (inactive / active / triggered)
    - 记录触发原因和降级动作
    - 为其他模块提供 safe_mode 状态查询
    - 写入 ledger (通过回调注入)
    """

    def __init__(self, repo_root: Optional[str] = None):
        self._status: SafeModeStatus = SafeModeStatus.INACTIVE
        self._records: list[SafeModeRecord] = []
        self._degraded_actions: list[str] = []
        self._repo_root = Path(repo_root) if repo_root else Path.cwd()

        # 可注入的 ledger 写入回调
        self._on_safe_mode_change = None  # callable(status, record)

    # ── Properties ─────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self._status in (SafeModeStatus.ACTIVE, SafeModeStatus.TRIGGERED)

    @property
    def is_inactive(self) -> bool:
        return self._status == SafeModeStatus.INACTIVE

    @property
    def status(self) -> SafeModeStatus:
        return self._status

    @property
    def records(self) -> list[SafeModeRecord]:
        return list(self._records)

    @property
    def latest_record(self) -> Optional[SafeModeRecord]:
        return self._records[-1] if self._records else None

    @property
    def trigger_count(self) -> int:
        return len(self._records)

    # ── Trigger / Release ──────────────────────────────

    def trigger(
        self,
        reason: str,
        route_id: str = "",
        workflow: str = "",
        stage_id: str = "",
        degraded_actions: Optional[list[str]] = None,
    ) -> SafeModeRecord:
        """
        触发 safe_mode。

        参数:
            reason: 触发原因 (使用 SAFE_MODE_TRIGGERS 中的 key 或自定义文本)
            route_id: 关联的 route
            workflow: 关联的 workflow
            stage_id: 触发时的 stage
            degraded_actions: 已采取的降级动作列表

        返回:
            SafeModeRecord
        """
        if reason not in SAFE_MODE_TRIGGERS:
            degraded_actions = degraded_actions or [f"unknown_reason: {reason}"]
        else:
            degraded_actions = degraded_actions or [SAFE_MODE_TRIGGERS[reason]]

        record = SafeModeRecord(
            trigger_reason=reason,
            route_id=route_id,
            workflow=workflow,
            stage_id=stage_id,
            degraded_actions=degraded_actions or [],
        )

        self._records.append(record)
        self._degraded_actions.extend(degraded_actions or [])
        self._status = SafeModeStatus.TRIGGERED  # 刚触发，待确认

        # 回调通知
        if self._on_safe_mode_change:
            self._on_safe_mode_change(self._status, record)

        return record

    def confirm(self) -> None:
        """确认 safe_mode 已激活 (TRIGGERED → ACTIVE)"""
        if self._status == SafeModeStatus.TRIGGERED:
            self._status = SafeModeStatus.ACTIVE

    def release(self, reason: str = "") -> None:
        """退出 safe_mode"""
        self._status = SafeModeStatus.INACTIVE
        if self._on_safe_mode_change:
            self._on_safe_mode_change(self._status, None)

    # ── Degraded actions ───────────────────────────────

    def add_degraded_action(self, action: str) -> None:
        self._degraded_actions.append(action)

    def get_degraded_actions(self) -> list[str]:
        return list(self._degraded_actions)

    # ── Condition checks (其他模块调用) ────────────────

    def should_disable_semantic(self) -> bool:
        """SafeMode 下是否应禁用 semantic-router"""
        return self.is_active

    def should_shrink_healing(self) -> bool:
        """SafeMode 下是否应收缩 self-healing"""
        return self.is_active

    def is_rollback_conservative(self) -> bool:
        """SafeMode 下 rollback 是否应保守执行"""
        return self.is_active

    # ── Execution guard check ──────────────────────────

    @staticmethod
    def check_critical_structural(
        workflow: str,
        required_stages: list[str],
        completed_stages: list[str],
        expected_artifacts: list[str],
        existing_artifacts: list[str],
    ) -> Optional[str]:
        """
        检查关键结构性缺失，用于 execution_guard → safe_mode 联动。

        返回: None 表示安全; 否则返回触发原因 key。
        """
        # 检查 required stages 缺失
        for stage in required_stages:
            if stage not in completed_stages:
                return "execution_guard_critical"

        # 检查 expected_artifacts 存在性
        for art in expected_artifacts:
            if art and art not in existing_artifacts:
                return "execution_guard_critical"

        return None

    # ── Serialization ──────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "safe_mode_status": self._status.value,
            "trigger_count": self.trigger_count,
            "latest_trigger_reason": self.latest_record.trigger_reason if self.latest_record else "",
            "degraded_actions": self._degraded_actions,
            "updated_at": _now_iso(),
        }

    def __repr__(self) -> str:
        return f"SafeModeManager(status={self._status.value}, triggers={self.trigger_count})"


# ── Module-level singleton ──────────────────────────────

_safe_mode_instance: Optional[SafeModeManager] = None


def get_safe_mode_manager(repo_root: Optional[str] = None) -> SafeModeManager:
    """获取全局 SafeModeManager 单例"""
    global _safe_mode_instance
    if _safe_mode_instance is None:
        _safe_mode_instance = SafeModeManager(repo_root=repo_root)
    return _safe_mode_instance


def reset_safe_mode_manager() -> None:
    """重置单例 (测试用)"""
    global _safe_mode_instance
    _safe_mode_instance = None

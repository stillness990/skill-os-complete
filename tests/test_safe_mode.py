"""
Tests: Safe Mode Manager
Phase 5 — 验证 SafeMode: trigger, is_active, should_disable_semantic, confirm, release
"""

import sys
import os

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from orchestration.orchestration_types import SafeModeStatus
from orchestration.safe_mode import SafeModeManager, SafeModeRecord


def test_initial_state_inactive():
    """New SafeModeManager starts INACTIVE"""
    print("1. Initial state → INACTIVE")
    sm = SafeModeManager()
    assert not sm.is_active
    assert sm.is_inactive
    assert sm.status == SafeModeStatus.INACTIVE
    print(f"  status={sm.status.value}, is_active={sm.is_active}")
    print("  PASS")


def test_trigger_sets_triggered():
    """trigger() sets status to TRIGGERED and records reason"""
    print("2. Trigger → TRIGGERED + record")
    sm = SafeModeManager()
    record = sm.trigger("manual_trigger", route_id="rte_001", workflow="delivery_pipeline")
    assert sm.status == SafeModeStatus.TRIGGERED
    assert sm.is_active  # TRIGGERED counts as active
    assert sm.trigger_count == 1
    assert record.trigger_reason == "manual_trigger"
    assert record.route_id == "rte_001"
    print(f"  status={sm.status.value}, trigger_count={sm.trigger_count}")
    print("  PASS")


def test_confirm_sets_active():
    """confirm() transitions TRIGGERED → ACTIVE"""
    print("3. Confirm → ACTIVE")
    sm = SafeModeManager()
    sm.trigger("manual_trigger")
    assert sm.status == SafeModeStatus.TRIGGERED
    sm.confirm()
    assert sm.status == SafeModeStatus.ACTIVE
    assert sm.is_active
    print(f"  status after confirm={sm.status.value}")
    print("  PASS")


def test_release_sets_inactive():
    """release() transitions to INACTIVE"""
    print("4. Release → INACTIVE")
    sm = SafeModeManager()
    sm.trigger("manual_trigger")
    sm.confirm()
    sm.release("testing complete")
    assert sm.status == SafeModeStatus.INACTIVE
    assert not sm.is_active
    assert sm.is_inactive
    print(f"  status after release={sm.status.value}")
    print("  PASS")


def test_should_disable_semantic():
    """should_disable_semantic() returns True when active"""
    print("5. should_disable_semantic")
    sm = SafeModeManager()
    assert not sm.should_disable_semantic()  # inactive → False
    sm.trigger("embedding_unavailable")
    sm.confirm()
    assert sm.should_disable_semantic()  # active → True
    print(f"  inactive: {not SafeModeManager().should_disable_semantic()}")
    print(f"  active: {sm.should_disable_semantic()}")
    print("  PASS")


def test_multiple_triggers():
    """Multiple triggers accumulate records"""
    print("6. Multiple triggers → accumulated records")
    sm = SafeModeManager()
    sm.trigger("embedding_unavailable", route_id="rte_a")
    sm.confirm()
    sm.release("recovered")
    sm.trigger("rollback_security_error", route_id="rte_b")
    sm.confirm()

    assert sm.trigger_count == 2
    assert sm.records[0].trigger_reason == "embedding_unavailable"
    assert sm.records[1].trigger_reason == "rollback_security_error"
    print(f"  trigger_count={sm.trigger_count}")
    print("  PASS")


def test_latest_record():
    """latest_record returns most recent trigger"""
    print("7. latest_record")
    sm = SafeModeManager()
    sm.trigger("self_healing_limit_exceeded", route_id="rte_x")
    latest = sm.latest_record
    assert latest is not None
    assert latest.trigger_reason == "self_healing_limit_exceeded"
    print(f"  latest: {latest.trigger_reason} (route={latest.route_id})")
    print("  PASS")


def test_should_shrink_healing():
    """should_shrink_healing returns True when active"""
    print("8. should_shrink_healing")
    sm = SafeModeManager()
    assert not sm.should_shrink_healing()
    sm.trigger("manual_trigger")
    sm.confirm()
    assert sm.should_shrink_healing()
    print("  PASS")


def test_degraded_actions():
    """Degraded actions are tracked"""
    print("9. Degraded actions tracking")
    sm = SafeModeManager()
    sm.trigger("embedding_unavailable", degraded_actions=["disable_semantic", "fallback_rule_only"])
    actions = sm.get_degraded_actions()
    assert "disable_semantic" in actions
    assert "fallback_rule_only" in actions
    print(f"  degraded_actions={actions}")
    print("  PASS")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 5 — Safe Mode Manager Tests")
    print("=" * 60)
    print()
    test_initial_state_inactive()
    print()
    test_trigger_sets_triggered()
    print()
    test_confirm_sets_active()
    print()
    test_release_sets_inactive()
    print()
    test_should_disable_semantic()
    print()
    test_multiple_triggers()
    print()
    test_latest_record()
    print()
    test_should_shrink_healing()
    print()
    test_degraded_actions()
    print()
    print("=" * 60)
    print("ALL SAFE MODE TESTS PASSED")
    print("=" * 60)

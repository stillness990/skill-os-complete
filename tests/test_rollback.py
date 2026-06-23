"""
Tests: Rollback Manager
Phase 5 — 验证路径安全规则：artifact_paths, repo-root 校验, ../ 拒绝, 安全清理
"""

import sys
import os
import tempfile
from pathlib import Path

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from orchestration.rollback_manager import RollbackManager, RollbackResult, CleanedArtifact, RejectedArtifact


# ── Helpers ──────────────────────────────────────────

REPO_ROOT = _REPO


def _make_manager() -> RollbackManager:
    return RollbackManager(repo_root=REPO_ROOT)


# ── Tests ────────────────────────────────────────────

def test_validate_safe_path():
    """Safe relative path passes validation"""
    print("1. Safe relative path → valid")
    mgr = _make_manager()
    is_safe, reason = mgr.validate_path_public("README.md")
    assert is_safe, f"Expected safe, got: {reason}"
    print(f"  'README.md': safe={is_safe}")
    print("  PASS")


def test_validate_dotdot_rejected():
    """Path with ../ is rejected"""
    print("2. Path with ../ → REJECTED")
    mgr = _make_manager()
    is_safe, reason = mgr.validate_path_public("../etc/passwd")
    assert not is_safe, f"Expected unsafe for ../, got safe"
    assert ".." in reason
    print(f"  '../etc/passwd': safe={is_safe}, reason='{reason}'")
    print("  PASS")


def test_validate_absolute_rejected():
    """Absolute path is rejected"""
    print("3. Absolute path → REJECTED")
    mgr = _make_manager()
    is_safe, reason = mgr.validate_path_public("/etc/passwd")
    assert not is_safe, f"Expected unsafe for absolute path"
    print(f"  '/etc/passwd': safe={is_safe}, reason='{reason}'")
    print("  PASS")


def test_validate_empty_rejected():
    """Empty path is rejected"""
    print("4. Empty path → REJECTED")
    mgr = _make_manager()
    is_safe, reason = mgr.validate_path_public("")
    assert not is_safe
    print(f"  '': safe={is_safe}, reason='{reason}'")
    print("  PASS")


def test_validate_multiple_dotdot():
    """Multiple ../ chains are rejected"""
    print("5. Multiple ../ → REJECTED")
    mgr = _make_manager()
    is_safe, reason = mgr.validate_path_public("../../var/log/syslog")
    assert not is_safe
    assert ".." in reason
    print(f"  '../../var/log/syslog': safe={is_safe}")
    print("  PASS")


def test_rollback_rejects_dangerous_paths():
    """Rollback execution rejects dangerous artifact_paths"""
    print("6. Rollback.execute — dangerous paths rejected")
    mgr = _make_manager()
    result = mgr.execute(
        route_id="test_001",
        artifact_paths=["../etc/passwd", "/etc/shadow"],
    )
    assert result.rejected_count == 2
    assert result.cleaned_count == 0
    assert result.rollback_status == "failed"
    assert result.has_security_errors
    print(f"  rejected={result.rejected_count}, status={result.rollback_status}")
    print(f"  security_errors={result.security_errors}")
    print("  PASS")


def test_rollback_safe_path_cleanup():
    """Rollback execution cleans up safe artifact paths"""
    print("7. Rollback.execute — safe path cleanup")
    mgr = _make_manager()

    # Create a temp file within repo to test safe deletion
    test_path = Path(REPO_ROOT) / "tests" / "_rollback_test_temp.txt"
    test_path.write_text("test artifact for rollback")
    assert test_path.exists()

    result = mgr.execute(
        route_id="test_002",
        artifact_paths=["tests/_rollback_test_temp.txt"],
    )

    assert result.cleaned_count == 1
    assert result.rejected_count == 0
    assert result.rollback_status == "success"
    assert not test_path.exists()  # file was actually deleted
    print(f"  cleaned={result.cleaned_count}, file_deleted={not test_path.exists()}")
    print("  PASS")

    # Cleanup in case test failed
    if test_path.exists():
        test_path.unlink()


def test_rollback_dry_run_preserves_files():
    """Dry run mode does not actually delete files"""
    print("8. Dry run → files preserved")
    mgr = _make_manager()

    test_path = Path(REPO_ROOT) / "tests" / "_rollback_dryrun_test.txt"
    test_path.write_text("test artifact for dry run")
    assert test_path.exists()

    result = mgr.execute(
        route_id="test_003",
        artifact_paths=["tests/_rollback_dryrun_test.txt"],
        dry_run=True,
    )

    assert result.cleaned_count == 0  # dry_run doesn't actually clean
    assert test_path.exists()  # file still there
    print(f"  cleaned={result.cleaned_count}, file_preserved={test_path.exists()}")
    print("  PASS")

    # Cleanup
    test_path.unlink()


def test_rollback_route_reads_ledger():
    """rollback_route reads artifact_paths from ledger dict"""
    print("9. rollback_route — reads from ledger")
    mgr = _make_manager()

    ledger_data = {
        "task_id": "task_004",
        "route_id": "test_004",
        "artifact_paths": ["README.md"],
    }
    result = mgr.rollback_route(
        route_id="test_004",
        ledger=ledger_data,
        dry_run=True,  # don't actually delete README.md!
    )
    print(f"  artifacts from ledger: {result.cleaned_artifacts}")
    assert len(result.cleaned_artifacts) > 0
    assert result.cleaned_artifacts[0].path == "README.md"
    print("  PASS")


def test_rollback_partial_status():
    """Mix of safe and dangerous → partial status"""
    print("10. Mixed paths → partial/failed status")
    mgr = _make_manager()

    # Create a temp file so safe path actually cleans
    test_path = Path(REPO_ROOT) / "tests" / "_rollback_mixed_test.txt"
    test_path.write_text("test")

    result = mgr.execute(
        route_id="test_005",
        artifact_paths=["tests/_rollback_mixed_test.txt", "../etc/passwd"],
    )
    # With one safe path cleaned and one dangerous path rejected → partial
    assert result.rejected_count >= 1
    assert result.rollback_status in ("partial", "failed")
    print(f"  status={result.rollback_status}, cleaned={result.cleaned_count}, rejected={result.rejected_count}")
    print("  PASS")

    # Cleanup
    if test_path.exists():
        test_path.unlink()


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 5 — Rollback Manager Tests")
    print("=" * 60)
    print()
    test_validate_safe_path()
    print()
    test_validate_dotdot_rejected()
    print()
    test_validate_absolute_rejected()
    print()
    test_validate_empty_rejected()
    print()
    test_validate_multiple_dotdot()
    print()
    test_rollback_rejects_dangerous_paths()
    print()
    test_rollback_safe_path_cleanup()
    print()
    test_rollback_dry_run_preserves_files()
    print()
    test_rollback_route_reads_ledger()
    print()
    test_rollback_partial_status()
    print()
    print("=" * 60)
    print("ALL ROLLBACK TESTS PASSED")
    print("=" * 60)

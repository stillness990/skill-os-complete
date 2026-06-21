"""
Tests: Semantic Router
Phase 4 — 验证 embedding health check, degrade, candidate retrieval
"""

import sys
sys.path.insert(0, "/path/to/skill-os-complete")
sys.path.insert(0, "/path/to/skill-os-complete/routing_assets")
sys.path.insert(0, "/path/to/skill-os-complete/orchestration")
sys.path.insert(0, "/path/to/skill-os-complete/ledger")

from semantic_router import SemanticRouter, EmbeddingHealth


def test_instantiation():
    """SemanticRouter can be created without crash"""
    sr = SemanticRouter()
    assert sr is not None
    assert sr.is_degraded  # 未检查前默认 degraded (safe-first)
    print("  instantiation: OK")
    print("  PASS")


def test_health_check_degraded():
    """Health check returns degraded when embedding unavailable"""
    sr = SemanticRouter(host="http://localhost:19999")  # nonexistent port
    health = sr.check_health()
    assert not health.available, f"Expected unavailable, got {health.available}"
    assert health.degraded, f"Expected degraded, got {health.degraded}"
    assert health.error, "Expected error message"
    print(f"  health: available={health.available}, degraded={health.degraded}")
    print(f"  error: {health.error}")
    print("  PASS")


def test_no_crash_on_unavailable():
    """P4-8: semantic-router failure → no crash"""
    sr = SemanticRouter(host="http://localhost:19999")
    candidates, health = sr.get_candidates("test query")
    assert candidates == [], f"Expected empty candidates, got {len(candidates)}"
    assert not health.available
    print("  get_candidates on unavailable → empty list, no crash")
    print("  PASS")


def test_candidate_returns_degraded_status():
    """get_candidates returns health with degraded status"""
    sr = SemanticRouter(host="http://localhost:19999")
    _, health = sr.get_candidates("test")
    assert health.degraded
    assert "error" in health.to_dict()
    print(f"  health.to_dict(): {health.to_dict()}")
    print("  PASS")


def test_index_build_fails_gracefully():
    """_build_index returns False when embedding unavailable"""
    sr = SemanticRouter(host="http://localhost:19999")
    sr._health = EmbeddingHealth(available=False, degraded=True, error="no service")
    ok = sr._build_index()
    assert not ok, f"Expected build failure, got {ok}"
    assert not sr._index_built
    print(f"  index built: {sr._index_built}")
    print("  PASS")


def test_routing_assets_loadable():
    """Semantic router can load workflow_cards and skill_cards"""
    sr = SemanticRouter()
    assert sr._workflow_cards is not None
    assert sr._skill_cards is not None
    wf_count = len(sr._workflow_cards.get("workflows", []))
    sk_count = len(sr._skill_cards.get("skills", []))
    print(f"  workflow cards: {wf_count}, skill cards: {sk_count}")
    assert wf_count == 3
    assert sk_count >= 8
    print("  PASS")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 4 — Semantic Router Tests")
    print("=" * 60)
    print()
    test_instantiation()
    print()
    test_health_check_degraded()
    print()
    test_no_crash_on_unavailable()
    print()
    test_candidate_returns_degraded_status()
    print()
    test_index_build_fails_gracefully()
    print()
    test_routing_assets_loadable()
    print()
    print("=" * 60)
    print("ALL SEMANTIC ROUTER TESTS PASSED")
    print("=" * 60)

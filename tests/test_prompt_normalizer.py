"""
Tests: Prompt Normalizer
Phase 3 — 验证输入标准化器的所有功能
"""

import sys
import os
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from orchestration.prompt_normalizer import PromptNormalizer, get_normalizer


def test_slash_commands():
    """Test /plan /debug /task /next detection"""
    n = PromptNormalizer()

    # /plan
    r = n.normalize("/plan 重构路由系统")
    assert "/plan" in r.slash_commands, f"Expected /plan in {r.slash_commands}"
    assert r.normalized == "重构路由系统"
    print(f"  /plan → normalized='{r.normalized}', slash={r.slash_commands}")

    # /debug
    r = n.normalize("/debug 为什么启动失败")
    assert "/debug" in r.slash_commands
    assert r.normalized == "为什么启动失败"
    print(f"  /debug → normalized='{r.normalized}', slash={r.slash_commands}")

    # /task
    r = n.normalize("/task 查看进度")
    assert "/task" in r.slash_commands
    print(f"  /task → slash={r.slash_commands}")

    # /next
    r = n.normalize("/next")
    assert "/next" in r.slash_commands
    print(f"  /next → slash={r.slash_commands}")

    print("  PASS")


def test_intent_types():
    """Test detection of repo_analysis / planning / debug / learning / construction_prompt"""
    n = PromptNormalizer()

    # repo_analysis
    r = n.normalize("读取项目并评估功能，再给升级方案")
    assert "repo_analysis" in r.detected_types or "planning" in r.detected_types
    assert r.primary_intent_hint == "project_delivery"
    print(f"  repo_analysis → intent={r.primary_intent_hint}, types={r.detected_types}")

    # planning
    r = n.normalize("帮我制定一个项目计划")
    assert "planning" in r.detected_types
    assert r.primary_intent_hint == "project_delivery"
    print(f"  planning → intent={r.primary_intent_hint}, types={r.detected_types}")

    # debug
    r = n.normalize("docker compose up 报 permission denied")
    assert "debug" in r.detected_types
    assert r.primary_intent_hint == "debug_issue"
    print(f"  debug → intent={r.primary_intent_hint}, types={r.detected_types}")

    # learning
    r = n.normalize("我想学 Python 异步编程")
    assert "learning" in r.detected_types
    assert r.primary_intent_hint == "learn_topic"
    print(f"  learning → intent={r.primary_intent_hint}, types={r.detected_types}")

    # construction_prompt
    r = n.normalize("生成 Claude 施工单")
    assert "construction_prompt" in r.detected_types or "planning" in r.detected_types
    assert r.primary_intent_hint == "project_delivery"
    print(f"  construction → intent={r.primary_intent_hint}, types={r.detected_types}")

    print("  PASS")


def test_multi_intent():
    """Test multi-intent detection"""
    n = PromptNormalizer()

    r = n.normalize("系统报错了，帮我诊断并制定修复计划")
    assert r.multi_intent, f"Expected multi_intent=True, got {r.multi_intent}"
    assert r.primary_intent_hint in ("debug_issue", "project_delivery")
    print(f"  multi-intent: {r.multi_intent}, primary={r.primary_intent_hint}, secondary={r.secondary_intent_hint}")

    print("  PASS")


def test_unknown():
    """Test unknown intent fallback"""
    n = PromptNormalizer()

    r = n.normalize("今天天气怎么样")
    assert r.primary_intent_hint == "unknown" or r.confidence == 0.0
    print(f"  unknown → intent={r.primary_intent_hint}, confidence={r.confidence}")

    r = n.normalize("你好")
    assert r.primary_intent_hint == "unknown" or not r.detected_types
    print(f"  hello → intent={r.primary_intent_hint}, types={r.detected_types}")

    print("  PASS")


def test_singleton():
    """Test singleton access"""
    n1 = get_normalizer()
    n2 = get_normalizer()
    assert n1 is n2
    print("  singleton: OK")
    print("  PASS")


if __name__ == "__main__":
    print("=== Test: Prompt Normalizer ===")
    print()
    test_slash_commands()
    print()
    test_intent_types()
    print()
    test_multi_intent()
    print()
    test_unknown()
    print()
    test_singleton()
    print()
    print("ALL NORMALIZER TESTS PASSED")

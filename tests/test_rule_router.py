"""
Tests: Rule Router
Phase 3 — 验证规则路由的 4 个必须场景 + slash command 路由

P3-4 要求:
1. 读取项目并评估功能，再给升级方案 → delivery_pipeline
2. 生成 Claude 施工单 → delivery_pipeline
3. docker compose up 报 permission denied → debug_pipeline
4. 学习类请求 → learning_pipeline
"""

import sys
sys.path.insert(0, "/path/to/skill-os-complete")
sys.path.insert(0, "/path/to/skill-os-complete/routing_assets")
sys.path.insert(0, "/path/to/skill-os-complete/orchestration")
sys.path.insert(0, "/path/to/skill-os-complete/ledger")

from orchestration_types import Workflow, Intent, TaskStatus
from prompt_normalizer import PromptNormalizer
from rule_router import RuleRouter


def _route(text: str):
    """Helper: normalize → route"""
    n = PromptNormalizer()
    r = RuleRouter()
    normalized = n.normalize(text)
    plan = r.route(normalized)
    return normalized, plan


def test_scenario_1():
    """P3-4 场景 1: 读取项目并评估功能，再给升级方案 → delivery_pipeline"""
    print("Scenario 1: 读取项目并评估功能，再给升级方案")
    normalized, plan = _route("读取项目并评估功能，再给升级方案")
    print(f"  normalized.intent_hint: {normalized.primary_intent_hint}")
    print(f"  normalized.types: {normalized.detected_types}")
    print(f"  plan.workflow: {plan.workflow.value}")
    print(f"  plan.intent: {plan.intent.value}")
    print(f"  plan.confidence: {plan.confidence}")
    print(f"  plan.stages: {[s.phase for s in plan.stages]}")
    stages = [s.phase for s in plan.stages]
    assert plan.workflow == Workflow.DELIVERY, f"Expected delivery_pipeline, got {plan.workflow}"
    assert plan.intent == Intent.PROJECT_DELIVERY
    assert "understand" in stages or "summarize" in stages or any(s.skill == "summarize" for s in plan.stages), \
        f"Expected summarize stage in {stages}"
    assert any(s.skill == "planning" for s in plan.stages), f"Expected planning stage in {stages}"
    assert plan.confidence > 0.3
    print("  PASS")


def test_scenario_2():
    """P3-4 场景 2: 生成 Claude 施工单 → delivery_pipeline"""
    print("Scenario 2: 生成 Claude 施工单")
    normalized, plan = _route("生成 Claude 施工单")
    print(f"  normalized.intent_hint: {normalized.primary_intent_hint}")
    print(f"  normalized.types: {normalized.detected_types}")
    print(f"  plan.workflow: {plan.workflow.value}")
    print(f"  plan.intent: {plan.intent.value}")
    print(f"  plan.confidence: {plan.confidence}")
    stages = [s.phase for s in plan.stages]
    print(f"  plan.stages: {stages}")
    assert plan.workflow == Workflow.DELIVERY, f"Expected delivery_pipeline, got {plan.workflow}"
    assert plan.intent == Intent.PROJECT_DELIVERY
    assert plan.confidence > 0.2
    print("  PASS")


def test_scenario_3():
    """P3-4 场景 3: docker compose up 报 permission denied → debug_pipeline"""
    print("Scenario 3: docker compose up 报 permission denied")
    normalized, plan = _route("docker compose up 报 permission denied")
    print(f"  normalized.intent_hint: {normalized.primary_intent_hint}")
    print(f"  normalized.types: {normalized.detected_types}")
    print(f"  plan.workflow: {plan.workflow.value}")
    print(f"  plan.intent: {plan.intent.value}")
    print(f"  plan.confidence: {plan.confidence}")
    stages = [s.phase for s in plan.stages]
    print(f"  plan.stages: {stages}")
    assert plan.workflow == Workflow.DEBUG, f"Expected debug_pipeline, got {plan.workflow}"
    assert plan.intent == Intent.DEBUG_ISSUE
    assert any(s.phase == "diagnose" and s.required for s in plan.stages), \
        f"Expected required diagnose stage in {stages}"
    assert plan.confidence > 0.2
    print("  PASS")


def test_scenario_4():
    """P3-4 场景 4: 学习类请求 → learning_pipeline"""
    print("Scenario 4: 我想学 Docker 网络原理")
    normalized, plan = _route("我想学 Docker 网络原理")
    print(f"  normalized.intent_hint: {normalized.primary_intent_hint}")
    print(f"  normalized.types: {normalized.detected_types}")
    print(f"  plan.workflow: {plan.workflow.value}")
    print(f"  plan.intent: {plan.intent.value}")
    print(f"  plan.confidence: {plan.confidence}")
    stages = [s.phase for s in plan.stages]
    print(f"  plan.stages: {stages}")
    assert plan.workflow == Workflow.LEARNING, f"Expected learning_pipeline, got {plan.workflow}"
    assert plan.intent == Intent.LEARN_TOPIC
    assert plan.confidence > 0.3
    print("  PASS")


def test_slash_commands():
    """Test slash command routing"""
    print("Slash command tests:")

    # /plan
    _, plan = _route("/plan 重构路由系统")
    assert plan.workflow == Workflow.DELIVERY
    print(f"  /plan → {plan.workflow.value} (confidence={plan.confidence})")

    # /debug
    _, plan = _route("/debug npm install 失败")
    assert plan.workflow == Workflow.DEBUG
    print(f"  /debug → {plan.workflow.value} (confidence={plan.confidence})")

    # /task
    _, plan = _route("/task 查看当前进度")
    assert any(s.skill == "task_ledger" for s in plan.stages), \
        f"Expected task_ledger stage, got {[s.skill for s in plan.stages]}"
    print(f"  /task → stages: {[s.skill for s in plan.stages]}")

    # /next
    _, plan = _route("/next")
    assert any(s.skill == "task_ledger" for s in plan.stages)
    print(f"  /next → stages: {[s.skill for s in plan.stages]}")

    print("  PASS")


def test_fallback():
    """Test unknown → fallback"""
    print("Fallback tests:")
    _, plan = _route("今天天气怎么样")
    assert plan.intent == Intent.UNKNOWN or plan.confidence == 0.0
    print(f"  '今天天气怎么样' → intent={plan.intent.value}, confidence={plan.confidence}")

    _, plan = _route("你好")
    assert plan.intent == Intent.UNKNOWN or plan.confidence == 0.0
    print(f"  '你好' → intent={plan.intent.value}, confidence={plan.confidence}")
    print("  PASS")


def test_no_embedding_dependency():
    """P3-5: 暂时不依赖 embedding 也能跑通基本路由"""
    print("No embedding dependency check:")
    # RuleRouter 不需要任何 embedding 服务即可工作
    r = RuleRouter()
    n = PromptNormalizer()
    normalized = n.normalize("帮我诊断这个报错")
    plan = r.route(normalized)
    assert plan.workflow == Workflow.DEBUG
    assert plan.route_source == "rule" or plan.route_source == "fallback"
    print(f"  Route successful without embedding: {plan.workflow.value} (source={plan.route_source})")
    print("  PASS")


def test_route_examples():
    """Test all labeled examples from route_examples.json"""
    import json
    print("Route examples test:")
    examples_path = "/path/to/skill-os-complete/routing_assets/route_examples.json"
    with open(examples_path, "r") as f:
        data = json.load(f)

    passed = 0
    failed = 0
    for ex in data["examples"]:
        normalized, plan = _route(ex["input"])
        expected_intent = ex["intent"]
        actual_intent = plan.intent.value if plan.intent else "unknown"

        # unknown 的示例不需要精确匹配
        if expected_intent == "unknown":
            if actual_intent == "unknown" or plan.confidence < 0.3:
                passed += 1
            else:
                failed += 1
                print(f"  FAIL: '{ex['input']}' → expected unknown, got {actual_intent}")
            continue

        if actual_intent == expected_intent:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: '{ex['input']}' → expected {expected_intent}, got {actual_intent}")

    print(f"  {passed}/{passed + failed} examples correct")
    success_rate = passed / (passed + failed) if (passed + failed) > 0 else 0
    assert success_rate >= 0.7, f"Success rate {success_rate:.1%} below 70% threshold"
    print("  PASS")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 3 — Rule Router Tests")
    print("=" * 60)
    print()
    test_scenario_1()
    print()
    test_scenario_2()
    print()
    test_scenario_3()
    print()
    test_scenario_4()
    print()
    test_slash_commands()
    print()
    test_fallback()
    print()
    test_no_embedding_dependency()
    print()
    test_route_examples()
    print()
    print("=" * 60)
    print("ALL RULE ROUTER TESTS PASSED")
    print("=" * 60)

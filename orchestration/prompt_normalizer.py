"""
Prompt Normalizer — 输入标准化器
Phase 3: 标准化用户输入，检测意图类型、slash 命令、multi-intent

职责：
- 去除无意义前缀/后缀
- 检测 /plan /debug /task /next 等 slash 命令
- 识别 repo_analysis / planning / debug / learning / construction_prompt 类型
- 检测 multi-intent（一个输入包含多个意图）
- 产出 NormalizedInput

不做：
- 不依赖 embedding
- 不做最终路由决策（那是 rule-router + workflow-resolver 的事）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ── Slash command patterns ────────────────────────────

SLASH_COMMANDS = {
    "/plan": "planning",
    "/debug": "debug",
    "/task": "task_ledger",
    "/next": "task_ledger",
    "/learn": "learning",
    "/review": "review",
    "/summarize": "summarize",
}

# ── Intent type indicators ────────────────────────────

# (type_name, zh_keywords, en_keywords, regex_patterns)
INTENT_TYPE_PATTERNS = [
    (
        "repo_analysis",
        ["读取项目", "分析项目", "评估功能", "审查代码", "看下这个项目",
         "分析这个仓库", "审计", "代码审计", "review 项目", "review 代码",
         "审阅", "看下代码", "了解这个项目", "熟悉项目", "读一下"],
        ["analyze", "audit", "review", "assess", "evaluate"],
        [
            r"(读取|分析|评估|审查|审计|审阅).+(项目|代码|仓库|功能)",
            r"(review|analyze|audit).+(project|code|repo)",
        ],
    ),
    (
        "planning",
        ["计划", "规划", "方案", "拆解", "步骤", "路线", "怎么做", "从哪开始",
         "设计", "架构", "重构方案", "升级方案", "施工", "施工单", "下一步",
         "当前进度", "进度", "任务列表"],
        ["plan", "design", "architecture", "roadmap", "breakdown"],
        [
            r"(出|写|生成|制定|帮我|给).+(计划|规划|方案|步骤|思路|路线)",
            r"(重构|升级|改进|优化).+(方案|计划|设计)",
        ],
    ),
    (
        "debug",
        ["报错", "bug", "诊断", "排查", "不工作", "异常", "莫名其妙",
         "不知道为什么", "不对劲", "卡住", "失败", "permission denied",
         "error", "exception", "traceback", "崩溃", "出错", "出问题了"],
        ["debug", "error", "bug", "fix", "diagnose", "troubleshoot", "broken"],
        [
            r"(为什么|怎么).+(报错|不工作|出问题|不对劲|卡住|失败)",
            r"(帮我|帮我看看|帮我诊断|帮我排查).+(报错|bug|问题|异常|错误)",
            r".+(报|出现|遇到|trigger).+(错误|异常|bug|error)",
        ],
    ),
    (
        "learning",
        ["我想学", "学会", "教我", "入门", "学习", "学习路线", "每日练习",
         "今天学什么", "复盘", "本周复盘", "学习复盘", "练习", "训练",
         "帮我设计学习", "学习计划", "讲明白", "梳理知识", "回顾"],
        ["learn", "study", "tutorial", "teach", "practice", "review"],
        [
            r"(我想学|我想.*学会|我要学).+",
            r"(教我|带我).+(学|入门|理解).+",
            r"(帮我|给我).+(学习|复盘|练习|设计学习).+",
            r"(今天|今日).+(学什么|学习|练习).+",
        ],
    ),
    (
        "construction_prompt",
        ["施工单", "生成施工单", "施工方案", "施工指令", "实施步骤",
         "执行计划", "操作指令", "Claude 施工", "AI 施工"],
        ["construction", "implementation prompt", "execution instruction"],
        [
            r"(生成|写|创建).+(施工单|施工方案|施工指令)",
            r"(Claude|AI|智能体).+(施工|执行)",
        ],
    ),
]


@dataclass
class NormalizedInput:
    """标准化后的用户输入"""
    raw: str = ""                           # 原始输入
    normalized: str = ""                    # 去 slash command 后的文本
    slash_commands: list[str] = field(default_factory=list)        # 检测到的 /command
    detected_types: list[str] = field(default_factory=list)        # 检测到的意图类型
    primary_intent_hint: Optional[str] = None   # 最可能的 intent (project_delivery/debug_issue/learn_topic)
    multi_intent: bool = False
    secondary_intent_hint: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "raw": self.raw,
            "normalized": self.normalized,
            "slash_commands": self.slash_commands,
            "detected_types": self.detected_types,
            "primary_intent_hint": self.primary_intent_hint,
            "multi_intent": self.multi_intent,
            "secondary_intent_hint": self.secondary_intent_hint,
            "confidence": self.confidence,
        }


# ── Normalizer ────────────────────────────────────────

class PromptNormalizer:
    """
    输入标准化器。

    用法:
        n = PromptNormalizer()
        result = n.normalize("读取项目并评估功能，再给升级方案")
        # result.primary_intent_hint = "project_delivery"
        # result.detected_types = ["repo_analysis", "planning"]
    """

    def __init__(self):
        self._slash_pattern = re.compile(
            r"^\s*(/\w+)\s*", re.IGNORECASE
        )
        # 预编译所有意图类型正则
        self._compiled_patterns = []
        for type_name, _, _, patterns in INTENT_TYPE_PATTERNS:
            for p in patterns:
                self._compiled_patterns.append((type_name, re.compile(p, re.IGNORECASE)))

    def normalize(self, raw_input: str) -> NormalizedInput:
        """标准化原始输入"""
        raw = raw_input.strip()
        result = NormalizedInput(raw=raw)

        # Step 1: 提取 slash commands
        normalized = raw
        slash_cmds = []
        # 检查所有已知 slash commands
        for cmd in SLASH_COMMANDS:
            if cmd in raw:
                slash_cmds.append(cmd)
                # 移除 slash command（保留后面的文本）
                normalized = normalized.replace(cmd, "", 1).strip()

        result.slash_commands = slash_cmds
        result.normalized = normalized if normalized else raw

        # Step 2: 检测意图类型
        text_lower = result.normalized.lower()
        detected = {}
        # 中文关键词匹配
        for type_name, zh_kw, en_kw, _ in INTENT_TYPE_PATTERNS:
            score = 0
            for kw in zh_kw:
                if kw in result.normalized:
                    score += 2
            for kw in en_kw:
                if kw in text_lower:
                    score += 2
            if score > 0:
                detected[type_name] = score

        # 正则匹配（加分）
        for type_name, pattern in self._compiled_patterns:
            if pattern.search(result.normalized):
                detected[type_name] = detected.get(type_name, 0) + 3

        # 排序 detected types
        sorted_types = sorted(detected.items(), key=lambda x: x[1], reverse=True)
        result.detected_types = [t for t, _ in sorted_types]

        # Step 3: 映射到 primary intent
        if sorted_types:
            # 优先级调整：debug 信号强于 planning（报错>计划）
            types_list = [t for t, _ in sorted_types]
            if "debug" in types_list:
                # debug 类型存在时优先作为 primary
                result.primary_intent_hint = "debug_issue"
                result.confidence = min(detected.get("debug", 1) / 10.0, 1.0)
            else:
                result.primary_intent_hint = self._type_to_intent(sorted_types[0][0])
                result.confidence = min(sorted_types[0][1] / 10.0, 1.0)

        # Step 4: multi-intent 检测
        intent_types_in_result = set()
        for t, _ in sorted_types:
            i = self._type_to_intent(t)
            if i:
                intent_types_in_result.add(i)

        if len(intent_types_in_result) > 1:
            result.multi_intent = True
            # 次要 intent
            intents_list = list(intent_types_in_result)
            if result.primary_intent_hint in intents_list:
                intents_list.remove(result.primary_intent_hint)
            if intents_list:
                result.secondary_intent_hint = intents_list[0]

        # 如果没有任何检测到，标记为 unknown
        if not result.detected_types:
            result.primary_intent_hint = "unknown"
            result.confidence = 0.0

        return result

    @staticmethod
    def _type_to_intent(type_name: str) -> Optional[str]:
        """意图类型 → intent 映射"""
        mapping = {
            "repo_analysis": "project_delivery",
            "planning": "project_delivery",
            "construction_prompt": "project_delivery",
            "debug": "debug_issue",
            "learning": "learn_topic",
        }
        return mapping.get(type_name)

    def is_delivery(self, result: NormalizedInput) -> bool:
        return result.primary_intent_hint == "project_delivery"

    def is_debug(self, result: NormalizedInput) -> bool:
        return result.primary_intent_hint == "debug_issue"

    def is_learning(self, result: NormalizedInput) -> bool:
        return result.primary_intent_hint == "learn_topic"

    def is_unknown(self, result: NormalizedInput) -> bool:
        return result.primary_intent_hint == "unknown" or not result.primary_intent_hint


# ── Singleton ─────────────────────────────────────────

_normalizer_instance: Optional[PromptNormalizer] = None


def get_normalizer() -> PromptNormalizer:
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = PromptNormalizer()
    return _normalizer_instance

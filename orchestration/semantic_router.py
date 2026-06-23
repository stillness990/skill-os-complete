"""
Semantic Router — 语义路由候选层
Phase 4: 基于 embedding 相似度的候选路由检索

职责：
- 对 routing_assets 做 embedding 索引
- 接收 normalized input → 计算语义相似度 → 返回候选 workflow
- embedding 不可用时 graceful degradation（不崩溃）

强制约束：
- embedding 不可用时不能崩溃，返回 degraded 状态
- 只能给候选，不能做最终决策
- 不修改 routing_assets 原始数据
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .embedding_provider import EmbeddingProvider, EmbeddingHealth

# Re-export for workflow_resolver compatibility
__all__ = ["SemanticRouter", "SemanticCandidate", "EmbeddingHealth"]

# ── 默认资源路径 ──
# semantic_router 在 orchestration/，routing_assets 在上层

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "routing_assets"
_DEFAULT_WORKFLOW_CARDS = _ASSETS_DIR / "workflow_cards.json"
_DEFAULT_SKILL_CARDS = _ASSETS_DIR / "skill_cards.json"


# ── SemanticCandidate ─────────────────────────────────

@dataclass
class SemanticCandidate:
    """语义路由候选"""
    workflow: str
    confidence: float           # 0.0 ~ 1.0
    similarity_score: float     # 原始相似度
    source: str = "semantic"
    matching_cards: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "workflow": self.workflow,
            "confidence": self.confidence,
            "similarity_score": self.similarity_score,
            "source": self.source,
            "matching_cards": self.matching_cards,
        }


# ── SemanticRouter ────────────────────────────────────

class SemanticRouter:
    """
    语义路由候选检索器。

    用法:
        sr = SemanticRouter()
        health = sr.check_health()
        if health.available:
            candidates = sr.get_candidates("读取项目并评估功能")
        else:
            # degraded mode — 使用 rule candidates only
    """

    def __init__(
        self,
        provider: Optional[EmbeddingProvider] = None,
        workflow_cards_path: Optional[Path] = None,
        skill_cards_path: Optional[Path] = None,
    ):
        self._provider = provider or EmbeddingProvider()
        self._wf_path = workflow_cards_path or _DEFAULT_WORKFLOW_CARDS
        self._sk_path = skill_cards_path or _DEFAULT_SKILL_CARDS
        self._workflow_cards = self._load_json(self._wf_path)
        self._skill_cards = self._load_json(self._sk_path)
        # 预建索引（lazy）
        self._index_built = False
        self._card_texts: list[str] = []
        self._card_workflows: list[str] = []
        self._card_embeddings: list[list[float]] = []

    @staticmethod
    def _load_json(path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ── Health Check ──────────────────────────────────

    def check_health(self) -> EmbeddingHealth:
        """检查 embedding 服务健康状态（委托给 provider）"""
        return self._provider.check_health()

    @property
    def is_available(self) -> bool:
        return self._provider.is_available

    @property
    def is_degraded(self) -> bool:
        return self._provider.is_degraded

    def get_health(self) -> EmbeddingHealth:
        """获取最近一次 health check 结果"""
        return self._provider.get_health()

    # ── Index Building ────────────────────────────────

    def _build_index(self) -> bool:
        """
        为所有 workflow/skill cards 建立 embedding 索引。
        返回是否成功。
        """
        if self._index_built:
            return True

        if not self.is_available:
            return False

        self._card_texts = []
        self._card_workflows = []

        # Workflow cards: description + zh keywords
        for wf in self._workflow_cards.get("workflows", []):
            desc = wf.get("description", "")
            keywords = " ".join(wf.get("trigger_keywords", {}).get("zh", []))
            text = f"{desc} {keywords}"
            self._card_texts.append(text)
            self._card_workflows.append(wf["name"])

        # Skill cards: description + zh keywords
        for sk in self._skill_cards.get("skills", []):
            desc = sk.get("description", "")
            keywords = " ".join(sk.get("keywords", {}).get("zh", []))
            text = f"{desc} {keywords}"
            self._card_texts.append(text)
            self._card_workflows.append(
                self._skill_to_workflow(sk)
            )

        # 获取每个 card 的 embedding
        self._card_embeddings = []
        success_count = 0
        for text in self._card_texts:
            emb = self._provider.get_embedding(text)
            if emb:
                self._card_embeddings.append(emb)
                success_count += 1
            else:
                # Fallback: 零向量 (nomic-embed-text dim=768)
                self._card_embeddings.append([0.0] * 768)

        self._index_built = success_count > 0
        return self._index_built

    @staticmethod
    def _skill_to_workflow(skill: dict) -> str:
        """Skill card → 关联 workflow name"""
        intents = skill.get("intents", [])
        intent_to_wf = {
            "project_delivery": "delivery_pipeline",
            "debug_issue": "debug_pipeline",
            "learn_topic": "learning_pipeline",
        }
        for intent in intents:
            wf = intent_to_wf.get(intent)
            if wf:
                return wf
        return "delivery_pipeline"

    # ── Cosine Similarity ─────────────────────────────

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """余弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ── Candidate Retrieval ───────────────────────────

    def get_candidates(
        self, query: str, top_k: int = 3
    ) -> tuple[list[SemanticCandidate], EmbeddingHealth]:
        """
        获取语义路由候选。

        Returns:
            (candidates, health) — 即使 embedding 不可用也返回有效 health
        """
        health = self.check_health()
        if not health.available:
            return [], health

        # Lazy build index
        if not self._index_built:
            ok = self._build_index()
            if not ok:
                health.error = "Failed to build embedding index"
                health.degraded = True
                return [], health

        # Get query embedding
        query_emb = self._provider.get_embedding(query)
        if query_emb is None:
            health.error = "Failed to get query embedding"
            health.degraded = True
            return [], health

        # Compute similarities
        scored = []
        for i, card_emb in enumerate(self._card_embeddings):
            sim = self._cosine_similarity(query_emb, card_emb)
            wf = self._card_workflows[i]
            scored.append((wf, sim, i))

        scored.sort(key=lambda x: x[1], reverse=True)

        # De-dup by workflow, keep highest score
        seen_wf: dict[str, tuple[float, int]] = {}
        for wf, sim, idx in scored[:top_k * 2]:
            if wf not in seen_wf or sim > seen_wf[wf][0]:
                seen_wf[wf] = (sim, idx)

        # Build candidates
        candidates = []
        for wf, (sim, _) in sorted(
            seen_wf.items(), key=lambda x: x[1][0], reverse=True
        )[:top_k]:
            # Similarity → confidence mapping
            confidence = min(sim + 0.2, 1.0) if sim > 0.3 else sim
            candidates.append(SemanticCandidate(
                workflow=wf,
                confidence=confidence,
                similarity_score=sim,
                source="semantic",
            ))

        return candidates, health


# ── Singleton ─────────────────────────────────────────

_semantic_router_instance: Optional[SemanticRouter] = None


def get_semantic_router() -> SemanticRouter:
    global _semantic_router_instance
    if _semantic_router_instance is None:
        _semantic_router_instance = SemanticRouter()
    return _semantic_router_instance

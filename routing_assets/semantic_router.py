"""
Semantic Router — 语义路由候选层
Phase 4: 基于 embedding 相似度的候选路由检索

职责：
- 对 routing_assets 做 embedding 索引
- 接收 normalized input → 计算语义相似度 → 返回候选 workflow
- embedding 不可用时 graceful degradation（不崩溃）

强制约束：
- 优先支持 nomic-embed-text:latest (via Ollama)
- embedding 不可用时不能崩溃，返回 degraded 状态
- 只能给候选，不能做最终决策
- 不修改 routing_assets 原始数据
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# ── 默认配置 ──────────────────────────────────────────

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_EMBED_MODEL = "nomic-embed-text:latest"
EMBED_HEALTH_TIMEOUT = 5  # seconds
EMBED_CALL_TIMEOUT = 10   # seconds

_ASSETS_DIR = Path(__file__).parent
_DEFAULT_WORKFLOW_CARDS = _ASSETS_DIR / "workflow_cards.json"
_DEFAULT_SKILL_CARDS = _ASSETS_DIR / "skill_cards.json"


# ── Health Status ─────────────────────────────────────

@dataclass
class EmbeddingHealth:
    """embedding 服务健康状态"""
    available: bool = False
    model: str = ""
    host: str = ""
    latency_ms: float = 0.0
    error: str = ""
    degraded: bool = True       # 默认 degraded（安全优先）

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "model": self.model,
            "host": self.host,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "degraded": self.degraded,
        }


# ── Semantic Candidate ────────────────────────────────

@dataclass
class SemanticCandidate:
    """语义路由候选"""
    workflow: str
    confidence: float           # 0.0 ~ 1.0
    similarity_score: float     # 原始相似度
    source: str = "semantic"
    matching_cards: list[str] = field(default_factory=list)  # 匹配到的 card 名称

    def to_dict(self) -> dict:
        return {
            "workflow": self.workflow,
            "confidence": self.confidence,
            "similarity_score": self.similarity_score,
            "source": self.source,
            "matching_cards": self.matching_cards,
        }


# ── Semantic Router ───────────────────────────────────

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
        host: str = DEFAULT_OLLAMA_HOST,
        model: str = DEFAULT_EMBED_MODEL,
        workflow_cards_path: Path = _DEFAULT_WORKFLOW_CARDS,
        skill_cards_path: Path = _DEFAULT_SKILL_CARDS,
    ):
        self._host = host.rstrip("/")
        self._model = model
        self._workflow_cards = self._load_json(workflow_cards_path)
        self._skill_cards = self._load_json(skill_cards_path)
        self._health: Optional[EmbeddingHealth] = None
        # 预建索引：workflow descriptions → embeddings (lazy)
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
        """
        检查 embedding 服务健康状态。

        检查项 (P4-2):
        - 服务可达性
        - 模型可调用性
        - 超时处理
        - 失败时返回 degraded 状态
        """
        health = EmbeddingHealth(host=self._host, model=self._model)

        # Check 1: Service reachable
        t0 = time.time()
        try:
            req = Request(f"{self._host}/api/tags", method="GET")
            resp = urlopen(req, timeout=EMBED_HEALTH_TIMEOUT)
            data = json.loads(resp.read().decode())
            health.latency_ms = (time.time() - t0) * 1000

            # Check 2: Model available
            models = [m.get("name", "") for m in data.get("models", [])]
            if self._model in models:
                health.available = True
                health.degraded = False
            else:
                health.error = f"Model '{self._model}' not found. Available: {models}"
                health.degraded = True

        except HTTPError as e:
            health.error = f"HTTP {e.code}: {e.reason}"
            health.latency_ms = (time.time() - t0) * 1000
        except URLError as e:
            health.error = f"Connection failed: {e.reason}"
            health.latency_ms = (time.time() - t0) * 1000
        except Exception as e:
            health.error = f"Health check error: {e}"
            health.latency_ms = (time.time() - t0) * 1000

        self._health = health
        return health

    @property
    def is_available(self) -> bool:
        if self._health is None:
            self.check_health()
        return self._health is not None and self._health.available

    @property
    def is_degraded(self) -> bool:
        if self._health is None:
            return True  # 未检查 = 假设不可用
        return self._health.degraded

    # ── Embedding API ─────────────────────────────────

    def _get_embedding(self, text: str) -> Optional[list[float]]:
        """获取文本 embedding。失败返回 None"""
        try:
            payload = json.dumps({
                "model": self._model,
                "prompt": text,
            }).encode("utf-8")
            req = Request(
                f"{self._host}/api/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urlopen(req, timeout=EMBED_CALL_TIMEOUT)
            data = json.loads(resp.read().decode())
            return data.get("embedding")
        except Exception:
            return None

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """余弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

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

        # Workflow cards: 每个 workflow 的 description + keywords
        for wf in self._workflow_cards.get("workflows", []):
            desc = wf.get("description", "")
            keywords = " ".join(wf.get("trigger_keywords", {}).get("zh", []))
            text = f"{desc} {keywords}"
            self._card_texts.append(text)
            self._card_workflows.append(wf["name"])

        # Skill cards: 每个 skill 的 description + keywords
        for sk in self._skill_cards.get("skills", []):
            desc = sk.get("description", "")
            keywords = " ".join(sk.get("keywords", {}).get("zh", []))
            text = f"{desc} {keywords}"
            self._card_texts.append(text)
            self._card_workflows.append(
                # skill → 关联 intent → workflow 映射
                self._skill_to_workflow(sk)
            )

        # 获取每个 card 的 embedding
        self._card_embeddings = []
        success_count = 0
        for text in self._card_texts:
            emb = self._get_embedding(text)
            if emb:
                self._card_embeddings.append(emb)
                success_count += 1
            else:
                # Fallback: 零向量
                self._card_embeddings.append([0.0] * 768)  # nomic-embed-text dim

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
        return "delivery_pipeline"  # fallback

    # ── Candidate Retrieval ───────────────────────────

    def get_candidates(self, query: str, top_k: int = 3) -> tuple[list[SemanticCandidate], EmbeddingHealth]:
        """
        获取语义路由候选。

        Returns:
            (candidates, health) — health 包含 degraded 状态信息
        """
        health = self.check_health()
        if not health.available:
            return [], health

        # Build index if needed
        if not self._index_built:
            ok = self._build_index()
            if not ok:
                health.error = "Failed to build embedding index"
                health.degraded = True
                return [], health

        # Get query embedding
        query_emb = self._get_embedding(query)
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
        seen_wf = {}
        for wf, sim, idx in scored[:top_k * 2]:  # check more to de-dup
            if wf not in seen_wf or sim > seen_wf[wf][0]:
                seen_wf[wf] = (sim, idx)

        # Build candidates
        candidates = []
        for wf, (sim, _) in sorted(seen_wf.items(), key=lambda x: x[1][0], reverse=True)[:top_k]:
            # Similarity → confidence mapping
            confidence = min(sim + 0.2, 1.0) if sim > 0.3 else sim
            candidates.append(SemanticCandidate(
                workflow=wf,
                confidence=confidence,
                similarity_score=sim,
                source="semantic",
            ))

        return candidates, health

    def get_health(self) -> EmbeddingHealth:
        """获取当前健康状态（不重新检查）"""
        if self._health is None:
            return EmbeddingHealth()
        return self._health


# ── Singleton ─────────────────────────────────────────

_semantic_router_instance: Optional[SemanticRouter] = None


def get_semantic_router() -> SemanticRouter:
    global _semantic_router_instance
    if _semantic_router_instance is None:
        _semantic_router_instance = SemanticRouter()
    return _semantic_router_instance

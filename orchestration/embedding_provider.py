"""
Embedding Provider — embedding 服务接口层
Phase 4: 封装 Ollama embedding API 调用，提供 health check 和向量获取

职责：
- 封装 embedding 服务连接（默认 Ollama）
- health check：服务可达 + 模型可用
- get_embedding：文本 → 向量
- 超时处理，失败不抛异常

不做：
- 不做索引管理（semantic_router 的事）
- 不做相似度计算（semantic_router 的事）
- 不加载 routing_assets（semantic_router 的事）
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# ── 默认配置 ──────────────────────────────────────────

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_EMBED_MODEL = "quentinz/bge-large-zh-v1.5:latest"
HEALTH_TIMEOUT = 5   # seconds
EMBED_TIMEOUT = 10   # seconds

# env flag 允许强制 embedding 失败（用于 SAFE MODE 真触发测试）
import os
FORCE_FAIL = os.environ.get("EMBEDDING_FORCE_FAIL", "") == "1"


# ── EmbeddingHealth ───────────────────────────────────

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


# ── EmbeddingProvider ─────────────────────────────────

class EmbeddingProvider:
    """
    embedding 服务提供者。

    用法:
        provider = EmbeddingProvider()
        health = provider.check_health()
        if health.available:
            vec = provider.get_embedding("hello world")
    """

    def __init__(
        self,
        host: str = DEFAULT_OLLAMA_HOST,
        model: str = DEFAULT_EMBED_MODEL,
    ):
        self._host = host.rstrip("/")
        self._model = model
        self._last_health: Optional[EmbeddingHealth] = None

    @property
    def host(self) -> str:
        return self._host

    @property
    def model(self) -> str:
        return self._model

    # ── Health Check ──────────────────────────────────

    def check_health(self) -> EmbeddingHealth:
        """
        检查 embedding 服务健康状态。

        检查项:
        1. 服务可达（连接超时 HEALTH_TIMEOUT）
        2. 指定模型可用
        3. 超时不抛异常，返回 degraded
        4. 支持 EMBEDDING_FORCE_FAIL 环境变量强制失败（测试用）
        """
        # 强制失败模式（用于 SAFE MODE 真触发测试）
        if FORCE_FAIL:
            health = EmbeddingHealth(
                host=self._host,
                model=self._model,
                error="EMBEDDING_FORCE_FAIL=1 — forced failure for testing",
            )
            self._last_health = health
            return health

        health = EmbeddingHealth(host=self._host, model=self._model)

        t0 = time.time()
        try:
            req = Request(f"{self._host}/api/tags", method="GET")
            resp = urlopen(req, timeout=HEALTH_TIMEOUT)
            data = json.loads(resp.read().decode())
            health.latency_ms = (time.time() - t0) * 1000

            models = [m.get("name", "") for m in data.get("models", [])]
            if self._model in models:
                health.available = True
                health.degraded = False
            else:
                health.error = f"Model '{self._model}' not found. Available: {models[:5]}"
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

        self._last_health = health
        return health

    @property
    def is_available(self) -> bool:
        if self._last_health is None:
            self.check_health()
        return self._last_health is not None and self._last_health.available

    @property
    def is_degraded(self) -> bool:
        if self._last_health is None:
            return True
        return self._last_health.degraded

    def get_health(self) -> EmbeddingHealth:
        """获取最近一次 health check 结果"""
        if self._last_health is None:
            return self.check_health()
        return self._last_health

    # ── Embedding API ─────────────────────────────────

    def get_embedding(self, text: str) -> Optional[list[float]]:
        """
        获取文本的 embedding 向量。

        Returns:
            list[float] on success, None on failure (never raises)
        """
        if FORCE_FAIL:
            return None

        if not self.is_available:
            return None

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
            resp = urlopen(req, timeout=EMBED_TIMEOUT)
            data = json.loads(resp.read().decode())
            return data.get("embedding")
        except Exception:
            return None

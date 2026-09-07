from __future__ import annotations

import json
from typing import Any

try:
    import redis
except ImportError:  # pragma: no cover - optional runtime dependency
    redis = None


class RedisClient:
    """Thin redis wrapper with a namespace and typed helpers."""

    def __init__(
        self,
        url: str | None = None,
        namespace: str = "ai",
        socket_timeout: float | None = None,
    ) -> None:
        self.namespace = namespace
        self.url = url
        self._client = (
            redis.Redis.from_url(url, socket_timeout=socket_timeout)
            if redis is not None and url
            else None
        )

    @property
    def client(self) -> Any:
        if self._client is None:
            raise RuntimeError("Redis is not configured; set REDIS_URL before using the store")
        return self._client

    def _key(self, key: str) -> str:
        if key.startswith(f"{self.namespace}:"):
            return key
        return f"{self.namespace}:{key}"

    def ping(self) -> bool:
        return bool(self.client.ping())

    def get(self, key: str) -> Any:
        raw = self.client.get(self._key(key))
        if raw is None:
            return None
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return raw

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
        ex: int | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        payload = value
        if not isinstance(value, (str, bytes, int, float, bool)):
            payload = json.dumps(value)
        return bool(self.client.set(self._key(key), payload, ex=ex or ttl_seconds, nx=nx, xx=xx))

    def delete(self, key: str) -> int:
        return int(self.client.delete(self._key(key)))

    def ttl(self, key: str) -> int:
        return int(self.client.ttl(self._key(key)))

    def incr(self, key: str, amount: int = 1) -> int:
        return int(self.client.incr(self._key(key), amount))

    def eval(self, script: str, numkeys: int, *keys_and_args: Any) -> Any:
        return self.client.eval(script, numkeys, *keys_and_args)
    
    def close(self) -> None:
        if self._client is not None:
            self._client.close()


class RedisStore:
    """Namespace-scoped store for short-lived interview and session metadata."""

    def __init__(self, client: Any, namespace: str = "ai") -> None:
        self.client = client
        self.namespace = namespace

    def _key(self, key: str) -> str:
        if key.startswith(f"{self.namespace}:"):
            return key
        return f"{self.namespace}:{key}"

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> bool:
        payload = value
        if not isinstance(value, (str, bytes, int, float, bool)):
            payload = json.dumps(value)
        return bool(self.client.set(self._key(key), payload, ex=ttl_seconds))

    def get(self, key: str) -> Any:
        raw = self.client.get(self._key(key))
        if raw is None:
            return None
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return raw

    def delete(self, key: str) -> int:
        return int(self.client.delete(self._key(key)))

    def ttl(self, key: str) -> int:
        return int(self.client.ttl(self._key(key)))


class DistributedStateStore(RedisStore):
    """Redis-backed state object for ephemeral session coordination."""

    pass

from __future__ import annotations

import pytest

from infrastructure.redis_store import RedisStore
from infrastructure.distributed_lock import DistributedLock
from infrastructure.rate_limiter import InMemoryRateLimiter, RateLimitExceeded
from infrastructure.provider_reliability import CircuitBreaker, ProviderErrorClassifier, ProviderHealthState


class FakeRedis:
    def __init__(self):
        self.data = {}
        self.ttls = {}

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.data:
            return False
        self.data[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    def get(self, key):
        return self.data.get(key)

    def delete(self, key):
        self.data.pop(key, None)
        self.ttls.pop(key, None)

    def incr(self, key):
        current = int(self.data.get(key, 0))
        current += 1
        self.data[key] = str(current)
        return current

    def ttl(self, key):
        return self.ttls.get(key, -1)

    def eval(self, script, numkeys, key, owner, *args):
        if "pexpire" in script:
            if self.data.get(key) != owner:
                return 0
            self.ttls[key] = int(args[0]) / 1000
            return 1
        if self.data.get(key) != owner:
            return 0
        self.delete(key)
        return 1


def test_redis_store_namespaces_keys_and_ttl():
    redis = FakeRedis()
    store = RedisStore(redis, namespace="interview")

    store.set("session:abc", {"status": "ready"}, ttl_seconds=30)

    assert "interview:session:abc" in redis.data
    assert redis.ttl("interview:session:abc") == 30


def test_distributed_lock_acquires_and_releases():
    redis = FakeRedis()
    lock = DistributedLock(redis, "lock:interview:123", ttl_seconds=15)

    assert lock.acquire()
    assert lock.acquire() is False

    lock.release()
    assert not redis.get("lock:interview:123")


def test_rate_limiter_blocks_after_limit():
    limiter = InMemoryRateLimiter(limit=2, window_seconds=60)

    assert limiter.allow("user-1") is True
    assert limiter.allow("user-1") is True
    with pytest.raises(RateLimitExceeded):
        limiter.allow("user-1")


def test_provider_circuit_breaker_opens_after_failures():
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=10)

    breaker.record_failure()
    breaker.record_failure()

    assert breaker.state == ProviderHealthState.OPEN


def test_provider_error_classifier_marks_transient_failures():
    classifier = ProviderErrorClassifier()

    assert classifier.is_retryable("timeout") is True
    assert classifier.is_retryable("auth_error") is False

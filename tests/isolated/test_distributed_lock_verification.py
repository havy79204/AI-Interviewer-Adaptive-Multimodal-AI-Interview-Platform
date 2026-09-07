from __future__ import annotations

import multiprocessing
import os
import time
from pathlib import Path

import pytest

from infrastructure.distributed_lock import (
    DistributedLock,
    LockAcquisitionTimeout,
    RedisUnavailableError,
)


class FakeRedis:
    def __init__(self):
        self.data = {}
        self.ttls = {}
        self.eval_calls = 0

    def set(self, key, value, ex=None, nx=False, **kwargs):
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
        return 1

    def eval(self, script, numkeys, key, owner, *args):
        self.eval_calls += 1
        if "pexpire" in script:
            if self.data.get(key) != owner:
                return 0
            self.ttls[key] = int(args[0]) / 1000
            return 1
        if self.data.get(key) != owner:
            return 0
        self.delete(key)
        return 1


class UnavailableRedis:
    def set(self, *args, **kwargs):
        raise OSError("connection refused")

    def eval(self, *args, **kwargs):
        raise OSError("connection refused")


def test_first_owner_acquires_and_second_owner_is_rejected():
    redis = FakeRedis()
    first = DistributedLock(redis, "lock:123", owner="owner-a")
    second = DistributedLock(redis, "lock:123", owner="owner-b")

    assert first.acquire() is True
    assert second.acquire() is False


def test_release_allows_next_owner_to_acquire():
    redis = FakeRedis()
    first = DistributedLock(redis, "lock:123", owner="owner-a")
    second = DistributedLock(redis, "lock:123", owner="owner-b")

    first.acquire()
    assert first.release() is True
    assert second.acquire() is True


def test_stale_owner_cannot_delete_new_owner_lock_atomically():
    redis = FakeRedis()
    first = DistributedLock(redis, "lock:123", owner="owner-a")
    second = DistributedLock(redis, "lock:123", owner="owner-b")

    first.acquire()
    redis.delete("lock:123")
    second.acquire()

    assert first.release() is False
    assert redis.get("lock:123") == "owner-b"
    assert redis.eval_calls == 1


def test_ttl_is_applied_and_expiration_allows_next_owner():
    redis = FakeRedis()
    first = DistributedLock(redis, "lock:123", ttl_seconds=7, owner="owner-a")
    assert first.acquire() is True
    assert redis.ttls["lock:123"] == 7

    redis.delete("lock:123")  # Simulate Redis TTL expiry.
    second = DistributedLock(redis, "lock:123", owner="owner-b")
    assert second.acquire() is True


def test_unavailable_redis_is_explicit_failure():
    lock = DistributedLock(UnavailableRedis(), "lock:123", owner="owner-a")
    with pytest.raises(RedisUnavailableError):
        lock.acquire()


def test_bounded_acquisition_timeout_is_explicit():
    redis = FakeRedis()
    holder = DistributedLock(redis, "lock:123", owner="owner-a")
    waiter = DistributedLock(redis, "lock:123", owner="owner-b", retry_interval_seconds=0.001)
    holder.acquire()

    started = time.monotonic()
    with pytest.raises(LockAcquisitionTimeout):
        waiter.acquire(timeout_seconds=0.02)
    elapsed = time.monotonic() - started

    assert elapsed < 0.5


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("REDIS_URL"), reason="Set REDIS_URL to run real Redis tests")
def test_real_redis_ttl_and_owner_release():
    import redis

    client = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    client.ping()
    key = f"phase11.5a:{os.getpid()}"
    client.delete(key)
    first = DistributedLock(client, key, ttl_seconds=1, owner="owner-a")
    second = DistributedLock(client, key, ttl_seconds=1, owner="owner-b")

    assert first.acquire() is True
    assert second.acquire() is False
    waiter = DistributedLock(client, key, owner="waiter", retry_interval_seconds=0.01)
    with pytest.raises(LockAcquisitionTimeout):
        waiter.acquire(timeout_seconds=0.05)
    assert first.extend(2) is True
    assert client.ttl(key) > 0
    assert first.release() is True
    assert second.acquire() is True
    assert first.release() is False
    assert client.get(key) == "owner-b"
    time.sleep(1.2)
    assert client.get(key) is None
    client.delete(key)


def _cross_process_worker(url: str, key: str, role: str, ready, release, result):
    import redis

    client = redis.Redis.from_url(url, decode_responses=True)
    lock = DistributedLock(client, key, ttl_seconds=5, owner=role)
    acquired = lock.acquire()
    result.put((role, "acquired", acquired, time.monotonic()))
    ready.set()
    if role == "owner-a":
        release.wait(3)
        lock.release()
        result.put((role, "released", True, time.monotonic()))
    else:
        result.put((role, "before_release", acquired, time.monotonic()))
        result.put((role, "after_release", lock.acquire(timeout_seconds=3), time.monotonic()))
        lock.release()
    client.close()


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("REDIS_URL"), reason="Set REDIS_URL to run real Redis tests")
def test_real_redis_crash_recovery():
    import redis

    url = os.environ["REDIS_URL"]
    client = redis.Redis.from_url(url, decode_responses=True)
    client.ping()
    key = f"phase11.5a:crash:{os.getpid()}"
    client.delete(key)
    context = multiprocessing.get_context("spawn")
    acquired = context.Event()
    process = context.Process(target=_crash_holder, args=(url, key, acquired))

    process.start()
    assert acquired.wait(3)
    assert client.get(key) == "crash-holder"
    process.terminate()
    process.join(5)
    assert process.exitcode is not None

    before_expiry = DistributedLock(client, key, ttl_seconds=1, owner="before-expiry")
    assert before_expiry.acquire() is False
    started = time.monotonic()
    while client.get(key) is not None and time.monotonic() - started < 3:
        time.sleep(0.05)
    elapsed = time.monotonic() - started
    after_expiry = DistributedLock(client, key, ttl_seconds=1, owner="after-expiry")
    assert client.get(key) is None
    assert after_expiry.acquire() is True
    print(f"crash_recovery_expiry_seconds={elapsed:.3f}")
    assert elapsed >= 0.8
    after_expiry.release()
    client.close()


def _crash_holder(url: str, key: str, acquired):
    import redis

    client = redis.Redis.from_url(url, decode_responses=True)
    lock = DistributedLock(client, key, ttl_seconds=1, owner="crash-holder")
    lock.acquire()
    acquired.set()
    time.sleep(10)


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("REDIS_URL"), reason="Set REDIS_URL to run real Redis tests")
def test_real_redis_cross_process_lock():
    import redis

    url = os.environ["REDIS_URL"]
    client = redis.Redis.from_url(url, decode_responses=True)
    client.ping()
    key = f"phase11.5a:cross-process:{os.getpid()}"
    client.delete(key)
    context = multiprocessing.get_context("spawn")
    ready_a = context.Event()
    ready_b = context.Event()
    release = context.Event()
    results = context.Queue()
    process_a = context.Process(target=_cross_process_worker, args=(url, key, "owner-a", ready_a, release, results))
    process_b = context.Process(target=_cross_process_worker, args=(url, key, "owner-b", ready_b, release, results))

    process_a.start()
    assert ready_a.wait(3)
    process_b.start()
    assert ready_b.wait(3)
    initial_results = [results.get(timeout=3) for _ in range(2)]
    assert ("owner-a", "acquired", True) in [item[:3] for item in initial_results]
    assert ("owner-b", "acquired", False) in [item[:3] for item in initial_results]
    release.set()
    process_a.join(5)
    process_b.join(5)
    assert process_a.exitcode == 0
    assert process_b.exitcode == 0
    remaining = [results.get(timeout=3) for _ in range(3)]
    all_results = initial_results + remaining
    origin = min(item[3] for item in all_results)
    print(
        "cross_process_events="
        + repr([(item[0], item[1], item[2], round(item[3] - origin, 3)) for item in all_results])
    )
    assert any(item[:3] == ("owner-a", "released", True) for item in remaining)
    assert any(item[:3] == ("owner-b", "after_release", True) for item in remaining)
    client.delete(key)
    client.close()


@pytest.mark.integration
def test_real_redis_unavailable_is_explicit_failure():
    import redis

    client = redis.Redis(
        host="127.0.0.1",
        port=6399,
        socket_connect_timeout=0.2,
        socket_timeout=0.2,
    )
    lock = DistributedLock(client, "phase11.5a:unavailable", owner="owner-a")
    with pytest.raises(RedisUnavailableError):
        lock.acquire()

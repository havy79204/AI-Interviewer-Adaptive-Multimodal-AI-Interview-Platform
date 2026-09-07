# Phase 11.5A Distributed Lock Verification

Date: 2026-09-07

## Result

The initial lock implementation was **not correct enough for production**. Inspection found a non-atomic `GET` followed by `DELETE` release race, timestamp-based owner tokens, and no bounded acquisition timeout. Those defects were fixed in the infrastructure layer before verification.

The isolated infrastructure tests pass. Real Redis and cross-process verification are blocked because Docker is installed but its Linux engine is not running, and no local `redis-server` is available.

## 1. Implementation Inspected

Inspected:

- `infrastructure/redis_store.py`
- `infrastructure/distributed_lock.py`
- `services/interview_service.py`
- `apps/api/main.py`
- `config/settings.py`

Redis is created by the FastAPI lifespan with the configured URL, namespace, and `REDIS_TIMEOUT_SECONDS` socket timeout. It is pinged during startup and closed during shutdown. `InterviewService` creates a namespaced `RedisClient` and `RedisStore`; its processing lock uses the `interview:processing:<interview_id>` key.

PostgreSQL remains the durable correctness layer. Redis only coordinates the short-lived processing critical section.

## 2. Lock Algorithm

Acquisition uses:

```text
SET lock_key owner_token NX EX ttl_seconds
```

The default acquisition timeout is `REDIS_LOCK_ACQUIRE_TIMEOUT_SECONDS`, currently `0.0`, which means immediate rejection if another owner holds the lock. A positive timeout retries until the deadline, then raises `LockAcquisitionTimeout`.

## 3. Ownership Model

Each lock receives an explicit owner token or a cryptographically random `secrets.token_urlsafe(32)` token. Timestamp-only ownership was removed because separate processes can generate the same millisecond timestamp.

Release uses an atomic Redis Lua script:

```text
if GET(lock_key) == owner_token then
    DEL(lock_key)
end
```

The implementation does not perform a separate client-side `GET` and `DELETE`. A stale owner therefore cannot delete a newer owner's lock.

Extension uses the same owner check atomically before `PEXPIRE`.

## 4. TTL Model

The acquisition command applies `EX ttl_seconds`. The configured interview lock TTL is `REDIS_LOCK_TTL_SECONDS`, default `30` seconds. If a process crashes without releasing, Redis removes the lock after the TTL and another process can acquire it. Actual expiry against a live Redis server remains unverified in this environment.

## 5. Failure Behavior

- Redis client construction does not connect immediately.
- FastAPI startup calls `PING`; an unavailable configured Redis causes startup to fail.
- Lock acquisition, release, and extension wrap Redis operation failures as `RedisUnavailableError`; the interview service converts acquisition failure into `InterviewForbiddenError("Cannot safely process distributed interview operation")`.
- Immediate contention returns `False`.
- Bounded waiting with a positive timeout raises `LockAcquisitionTimeout`.
- Interview answer processing is fail-closed when no lock can be acquired; it raises the existing `InterviewForbiddenError` path rather than proceeding without coordination.
- There is no unsafe degraded multi-instance mode.

## 6. Isolated Test Result

Command:

```text
python -m pytest -q tests/isolated/test_distributed_lock_verification.py -m not integration
```

Result:

```text
6 passed, 2 deselected
```

Covered:

- First owner acquires.
- Second owner is rejected.
- Release permits the next owner to acquire.
- A stale owner cannot delete a newer owner's lock.
- TTL is attached to acquisition; expiration is simulated in the fake store.
- Redis unavailability raises `RedisUnavailableError`.
- Bounded acquisition raises `LockAcquisitionTimeout` within the configured wait bound.

These tests verify control-flow and ownership behavior but cannot prove Redis server-side Lua execution or real expiry.

## 7. Redis Integration Result

**BLOCKED**.

Docker executable was present, but starting `redis:7-alpine` failed because the Docker Desktop Linux engine was unavailable. The attempted real test against `redis://localhost:6380/0` failed with `ConnectionRefusedError` / Windows error 10061.

No mock result is reported as a real Redis pass.

## 8. Cross-Process Result

**BLOCKED**.

The isolated suite contains a `multiprocessing` test using two spawned Python processes, separate Redis clients, and separate lock instances. It requires `REDIS_URL`, but could not execute because no Redis server was available.

Therefore there is no unsupported claim that two application processes have been verified.

## 9. Interview Concurrency Result

**BLOCKED**.

The actual `InterviewService` path now acquires the Redis processing lock before the existing PostgreSQL transaction and releases it in `finally`. However, an end-to-end duplicate-answer test requires the application dependency graph plus a live PostgreSQL database. The repository test environment remains blocked by dependency resolution and no PostgreSQL integration instance was available.

Redis alone is not treated as the durable correctness guarantee. The intended final guarantee is Redis coordination plus PostgreSQL transactions and uniqueness constraints on turns and assessments.

## 10. Dependency Blocker

**DEPENDENCY BLOCKER — no dependency changes made.**

Current `requirements.txt` pins:

- `langchain-openai==0.0.5`
- `openai==1.3.5`

`langchain-openai==0.0.5` requires `openai>=1.10.0,<2.0.0`, so the two exact pins are incompatible. The repository has no `requirements.lock`, `poetry.lock`, `Pipfile.lock`, or `uv.lock`.

The Python 3.14 environment also cannot import the pinned SQLAlchemy 2.0.23 stack. Attempts to resolve this by changing the AI dependency stack were intentionally not made.

## 11. Remaining Limitations

- Real Redis Lua release was not executed.
- Real TTL expiration was not executed.
- Cross-process lock ownership was not executed against Redis.
- Crash recovery was not executed against Redis; only the TTL design and isolated simulation were checked.
- Interview/PostgreSQL concurrency was not executed.
- The `ConnectionManager` WebSocket registry remains process-local and is outside this lock verification scope.
- Redis availability is required for the configured distributed interview path; no unsafe fallback is enabled.

## Test Classification

| Test | Classification |
|---|---|
| Isolated Redis/lock unit tests | PASS |
| Owner-only release algorithm test | PASS, isolated Lua behavior simulated |
| Bounded acquisition timeout | PASS |
| Redis unavailable behavior | PASS |
| Real Redis integration | BLOCKED — Docker engine unavailable |
| Cross-process lock | BLOCKED — no live Redis |
| TTL crash recovery | BLOCKED — no live Redis |
| InterviewService/PostgreSQL concurrency | BLOCKED — dependency and database environment |
| Full repository suite | BLOCKED — dependency resolution |

No production claim is made for the blocked real Redis or multi-process tests.

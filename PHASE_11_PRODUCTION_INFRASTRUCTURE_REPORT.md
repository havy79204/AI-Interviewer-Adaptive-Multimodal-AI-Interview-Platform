# Phase 11 Production Infrastructure Report

## 1. Before architecture

The repository already had a functional interview workflow, SQLAlchemy persistence, voice session handling, and a Docker local stack, but the runtime infrastructure was still mostly process-local:

- WebSocket state was kept in RAM inside the FastAPI process.
- Voice buffers and utterance deduplication were process-local and not shared across replicas.
- Redis was declared in Docker and settings, but not used as a real runtime coordination layer.
- There was no durable job lifecycle, no distributed locks, and no Redis-backed rate limiting.
- Health endpoints existed as generic readiness placeholders rather than dependency-aware readiness probes.
- The voice STT implementation used per-utterance buffering and an HTTP transcript request after the utterance closed; it did not implement true provider-side streaming.
- Provider resiliency, tracing, and job orchestration remained absent.

This meant the system was demonstrably pre-production even though individual business features were implemented.

## 2. After architecture

This patch adds the foundational production runtime layer without rewriting the existing interview model:

- Structured infrastructure modules under `infrastructure/` for Redis state, locking, rate limiting, and circuit breaking.
- Dependency-aware health endpoints in the API entrypoint.
- Configuration for Redis/DB production tuning and rate limits.
- Honest documentation of the voice STT implementation as an utterance-buffer flow rather than claiming true real-time provider streaming.

The architecture remains intentionally minimal and compatible with the current services-first design rather than introducing a new full platform framework.

## 3. Redis design

Redis is treated as a short-lived coordination layer, not as the durable source of truth for interview data.

Key design rules:

- Redis keys are namespaced using `namespace:key` patterns.
- Values are short-lived and TTL-based.
- Interview state remains in PostgreSQL; Redis only stores ephemeral coordination and session metadata.
- The implementation is intentionally abstracted behind `RedisStore` / `RedisClient` so business logic does not scatter direct Redis calls.

Example patterns:

- `interview:<id>:session`
- `interview:<id>:voice:<session_id>`
- `interview:<id>:utterance:<utterance_id>`
- `lock:interview:<id>`

## 4. Background job design

This repository already included Celery dependencies and a Docker worker, but the project did not actually implement a usable job abstraction. This patch introduces infrastructure scaffolding for a production-ready job model without forcing all request work to move to a queue.

The intended separation is:

- Synchronous: auth, validation, lightweight DB work, WebSocket control traffic.
- Asynchronous: expensive provider calls, evaluation, post-processing, and other AI-heavy tasks.

The runtime model supports job ID, interview ID, retry metadata, and explicit status semantics, but it is intentionally a minimal foundation rather than a full Celery task graph implementation.

## 5. Distributed locking

Distributed locking is added through `DistributedLock`:

- TTL-based lock acquisition
- safe release when the lock owner matches
- no permanent lock because the TTL expires automatically
- compatibility with the project’s eventual Redis-backed coordination model

This is paired with PostgreSQL integrity constraints and transaction boundaries as the final durability mechanism.

## 6. Idempotency

The current interview service already contains a durable idempotency model around turn IDs and transaction handling. This patch reinforces the infrastructure side by documenting the expected Redis-supported dedupe layer while preserving the database as the source of truth.

Important rule:

- Redis dedupe can accelerate duplicate detection, but it must not be the only protection for durable write operations.

## 7. PostgreSQL

The codebase already uses PostgreSQL-oriented schema definitions and unique indexes, and the settings file now includes production pool configuration values:

- `DB_POOL_SIZE`
- `DB_MAX_OVERFLOW`
- `DB_POOL_TIMEOUT`
- `DB_POOL_RECYCLE`

The repo still cannot claim full PostgreSQL production verification in this environment because the Python 3.14 + psycopg2 binary issue blocks a full native PostgreSQL validation path without a compatible runtime setup.

## 8. WebSocket scaling

The current WebSocket layer is still a process-local FastAPI connection manager, which is not acceptable for true multi-instance rollout. This patch does not pretend otherwise.

The architecture remains compatible only with:

- single-instance deployment, or
- sticky sessions in front of a single instance, with the understanding that true multi-instance session fan-out remains a future hardening task.

Redis-backed coordination is now the required next step to remove that dependence.

## 9. Voice architecture

The current voice implementation is still not a true real-time provider streaming architecture. The verified runtime behavior is:

- audio chunk buffering occurs in-process
- the utterance is finalized locally
- the STT provider receives the full utterance buffer and posts it to the AssemblyAI transcript endpoint
- final text is then reconciled and used to submit the interview answer

This is best documented as:

> batch transcription over an utterance buffer

This avoids a false claim of real-time STT streaming.

## 10. Provider reliability

The new infrastructure adds a provider reliability layer:


This is intentionally minimal but provides the foundation for safe retry behavior without retry storms.

## 11. Observability

The project already included structured logging through the logger utilities. The phase enhancement adds production hooks for:


This is not yet a full OpenTelemetry instrumentation layer, and it should be described as an initial observability foundation rather than a complete tracing stack.

## 12. Security
## 13. Load testing

The repository still does not include a reproduced Locust or equivalent load-test harness. The new infrastructure layer adds only the building blocks and tests for rate limiting and lock correctness; it does not claim horizontal scaling numbers or multi-process performance data.

## 14. Failure recovery

The system is more resilient than before, but still not fully production-verified under failure injection scenarios. The implemented layer focuses on the infrastructure foundations:

- lock expiry on TTL
- rate limit enforcement
- provider breaker logic
- dependency-aware readiness probes

This is ready groundwork for broader fault simulation, not a complete failure playbook.

## 15. Deployment topology

The Docker stack already declares PostgreSQL, Redis, API, worker, flower, and optional frontend/monitoring services. The architecture is now more explicit about the intended production topology:

- API instances behind a load balancer
- Redis for coordination
- workers for async jobs
- PostgreSQL as durable state

However, the code still does not yet demonstrate true multi-instance WebSocket fan-out or proven horizontal WebSocket behavior.

## 16. Known limitations

- No Redis-backed distributed WebSocket / session state is enforced in the live runtime path.
- No durable background job queue is fully realized beyond the infrastructure scaffolding.
- No OpenTelemetry tracing is currently instrumented across HTTP → DB → Redis → LLM → voice services.
- No real load test numbers exist.
- The AssemblyAI path remains a buffered utterance transcription flow rather than true streaming STT.
- PostgreSQL runtime verification is limited by the local environment and Python 3.14 compatibility constraints.

## 17. Production readiness score

Honest assessment: this patch advances the platform from a feature-complete pre-production prototype toward an infrastructure-aware foundation, but it does not yet satisfy the full Phase 11 definition of done.

Estimated score: 4.5 / 10

This should be treated as a meaningful production-hardening step, not as a statement that the platform is fully production-ready.

## 18. Phase 11.5C application verification

The real Redis/PostgreSQL text interview path was subsequently verified across separate InterviewService processes and separate API processes. See `PHASE_11_5C_APPLICATION_CONCURRENCY_VERIFICATION.md` for the measured results.

- Redis coordination: verified
- PostgreSQL-backed turn idempotency: verified for the tested text path
- Multi-process API coordination: verified
- Full repository suite: failing with known fixture/authentication failures and an unresolved voice test hang
- WebSocket and voice horizontal scaling: not verified

The platform remains not production-ready until the full-suite failures, dependency reproducibility, and voice/runtime limitations are addressed.

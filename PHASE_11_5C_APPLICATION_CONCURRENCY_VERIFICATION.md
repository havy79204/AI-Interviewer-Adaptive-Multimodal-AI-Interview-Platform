# Phase 11.5C Application Concurrency Verification

Date: 2026-09-07

## Conclusion

The real production-critical text interview path was verified across multiple independent Python processes and multiple independent API processes using real Redis 7.2.16 and PostgreSQL 15.19.

Verified behavior:

- One concurrent worker acquires the interview lock.
- The competing worker is rejected with the current fail-fast policy.
- Exactly one durable turn is created.
- Assessment rows are unique per turn and competency.
- Evidence and competency state are committed once for the winning turn.
- Duplicate replay is idempotent.
- The lock is released after duplicate replay and error/early-return paths.
- A subsequent valid turn proceeds.
- API processes share the same Redis and PostgreSQL services.
- Redis failure fails closed.
- PostgreSQL readiness reports unavailable when the database cannot be reached.

The platform as a whole is **not production-ready**: the full suite does not finish cleanly, a voice websocket test hangs, and several existing tests have fixture/authentication failures.

## A. Environment

Existing Compose infrastructure was used. No duplicate stack or new architecture was added.

```text
Docker Engine: 29.4.3
Redis image: redis:7.2-alpine
Redis server: 7.2.16
PostgreSQL image: pgvector/pgvector:pg15
PostgreSQL server: 15.19
Python: 3.11.9
Redis URL: redis://127.0.0.1:6379/0
PostgreSQL URL: postgresql://ai_interviewer:ai_interviewer_dev@127.0.0.1:5432/ai_interviewer
```

Services were started with:

```text
docker compose up -d redis postgres
```

Both containers reported `healthy`.

## B. Runtime Path Audited

The actual path is:

```text
HTTP POST /api/v1/interview/{interview_id}/answer
  -> apps/api/v1/routes/interview.py
  -> InterviewService.submit_answer
  -> Redis distributed lock
  -> PostgreSQL turn claim transaction
  -> InterviewAgentCore / evaluation / RAG
  -> PostgreSQL state, turn, evidence, assessment, competency writes
  -> atomic Redis lock release
```

Durable constraints include:

- unique `(interview_id, turn_id)` on interview turns
- unique `(interview_id, sequence_number)` on interview turns
- unique `(interview_id, turn_id, competency)` on assessments
- unique `(interview_id, competency)` on competency state

The Redis lock is interview-scoped, so concurrent turns for the same interview are serialized or rejected according to the configured acquisition policy.

## C. Code Corrections Required by Verification

Application-level testing exposed two real defects:

1. `RedisClient.set()` did not accept Redis `ex`/`nx` options, so `InterviewService` could not use the lock wrapper even though raw Redis tests passed.
2. Early returns in `submit_answer()` bypassed the later `finally`, leaving the lock held until TTL on duplicate replay and some initial-transaction error paths.

Both were corrected. A startup logging defect was also corrected so API workers could boot: standard-library logging now receives structured fields through `extra={...}`.

## D. Cross-Process InterviewService Test

Command:

```text
$env:REDIS_URL='redis://127.0.0.1:6379/0'
$env:DATABASE_URL='postgresql://ai_interviewer:ai_interviewer_dev@127.0.0.1:5432/ai_interviewer'
python -m pytest -s -q tests/integration/test_phase115c_application_concurrency.py::test_cross_process_interview_service_commits_one_turn_and_replays_idempotently
```

Result:

```text
1 passed
```

Observed run:

```text
interview_id: 3f4d1598-74ea-44ed-b3c5-68779c846f13
turn_id: turn-84bb02a1-eecb-46c6-827b-df9ca4719a37
worker A: rejected, lock wait/rejection 0.000s
worker B: committed, duration 0.109s
process group duration: 1.766s
```

Assertions verified:

- two independent spawned Python processes
- exactly one `committed` result and one `rejected` result
- one durable turn
- no duplicate assessment for the same turn and competency
- evidence and competency state present
- duplicate replay returns successfully without adding rows
- lock is released after replay
- a subsequent turn commits successfully

Classification: **PASS**

## E. Redis Failure Test

The service-level test used a real Redis client pointed at an unreachable local port. `InterviewService.submit_answer()` returned the documented fail-closed error:

```text
Cannot safely process distributed interview operation
```

Classification: **PASS**

## F. PostgreSQL Failure Test

An API worker was started with an unreachable PostgreSQL port while Redis remained healthy. The readiness endpoint returned:

```json
{"ready":false,"checks":{"database":false,"redis":true}}
```

Classification: **PASS**

## G. Multi-Process API Test

The test started two fresh independent Uvicorn processes:

```text
API process 1: port 8011, PID 15848, health 200
API process 2: port 8012, PID 25416, health 200
```

The test used the actual HTTP API and a shared Redis/PostgreSQL pair. It authenticated, created an interview, then sent the same answer and `turn_id` concurrently to both ports.

Result:

```text
1 passed in 3.71s
HTTP statuses: [200, 403]
request duration: 0.344s
```

The database assertions verified one durable turn and no duplicate assessment for the same turn and competency. Both API processes were cleaned up and no test-port listeners remained.

The `403` is expected under the current fail-fast lock policy: the winning request commits and the competing request is rejected while the interview is locked.

Classification: **PASS**

## H. Full Repository Suite

The full suite collected 104 tests and reached:

```text
95 passed
8 failed
0 skipped observed
0 collection errors
1 voice test hung and required termination
```

The exact failure categories were:

- 3 API/production-pipeline authentication failures because `admin@example.com` was absent or credentials differed in the shared database.
- 2 PostgreSQL foreign-key fixture failures using nonexistent user IDs.
- 1 existing concurrent-turn test expected `[200, 200]`, but the distributed fail-fast policy correctly produced `[200, 403]`.
- 1 voice websocket test hung during the authenticated final-flow scenario.

These are not silently converted to passes. The first five failures are test data/expectation issues; the voice hang remains unresolved and requires separate investigation.

Classification: **FAIL** for the full suite, with known failure categories above.

## I. WebSocket and Voice Distribution Audit

| State | Current location | Distribution status |
|---|---|---|
| Active WebSocket objects | `ConnectionManager.active_connections` | Process-local only |
| Standard WebSocket event routing | `ConnectionManager` | Process-local only; no Redis pub/sub |
| Voice audio buffers | `VoiceSessionService.buffers` | Process-local RAM |
| Committed voice utterance records | `VoiceSessionService.committed` | Process-local RAM |
| Interview state, turns, evidence, assessments | PostgreSQL | Durable/shared |
| Interview processing lock | Redis | Shared/TTL-bound |
| Short-lived Redis metadata | Redis abstractions | Shared when explicitly used |

A reconnect to another API process can authenticate and reload durable interview state, but active socket objects, audio buffers, and in-memory committed utterance deduplication do not survive process boundaries. Horizontal WebSocket/voice scaling is therefore **not verified or claimed**.

## J. Dependency Analysis

The smallest safe OpenAI change remains:

```diff
-openai==1.3.5
+openai==1.10.0
```

This satisfies `langchain-openai==0.0.5` and does not affect the application provider because it uses HTTPX directly.

The complete declared dependency set is still not reproducibly resolvable without broader maintenance:

- configured package index does not provide `PyJWT==2.8.1`
- `langchain==0.1.0` and `langchain-community==0.0.13` require `langsmith<0.1.0`
- `langgraph==0.0.30` does not export the `START` symbol used by the application
- a verification-only environment required newer compatible LangGraph/LangChain Core packages to import the existing graph

No broad dependency upgrade was committed. The remaining dependency work is separate from distributed coordination.

## K. Classification Table

| Area | Classification |
|---|---|
| Redis distributed lock | PASS |
| PostgreSQL connectivity | PASS |
| Cross-process InterviewService | PASS |
| Interview idempotent replay | PASS |
| Redis unavailable fail-closed behavior | PASS |
| PostgreSQL unavailable readiness | PASS |
| Multi-process API | PASS |
| PostgreSQL interview concurrency | PASS for the verified text path |
| WebSocket horizontal scaling | NOT VERIFIED |
| Full repository suite | FAIL |
| Voice final-flow regression | FAIL / unresolved hang |
| Dependency reproducibility | BLOCKED |

## L. Production-Readiness Conclusion

The critical text interview processing path now has real application-level evidence across Redis, PostgreSQL, separate InterviewService processes, and separate API processes. The lock protects the durable turn/evaluation path, duplicate replay is idempotent, and lock release behavior is verified.

The platform must not yet be called production-ready. The full suite is failing, the authenticated voice final-flow test hangs, dependency declarations are not reproducibly installable as written, and WebSocket/voice horizontal scaling remains process-local and unverified.

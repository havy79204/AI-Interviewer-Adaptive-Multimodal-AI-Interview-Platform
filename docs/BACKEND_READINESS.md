# Backend Readiness Assessment

**Scope:** Backend-only, bounded offline verification and a focused startup-safety fix.
**Overall:** Offline regression evidence is positive; live AI and production readiness remain **BLOCKED**.

## Executive summary

- The backend and UI are separate Git repositories. Work was confined to the backend repository; the UI worktree was clean and unchanged. No commits were created.
- Existing P0.1–P0.6 work was preserved. The backend still contains the prior milestone's uncommitted changes.
- Development/test startup previously enabled an administrator with an in-source, known password by default. This was reproduced by a failing regression test and fixed: bootstrap is now opt-in, credentials default to empty, and local API binding defaults to loopback.
- Database-filtered per-recruiter and candidate-self authorization, report gating, and HTTP/WebSocket interview ownership checks exist and passed the focused offline regression run.
- There is no organization membership model and no production recruiter-to-candidate account-linking workflow. Do not use the system for multi-company customer data.
- No provider credentials, live-test opt-ins, or `.env` file are present. No live requests were made. Live evaluation, semantic embeddings, and provider-backed E2E remain **BLOCKED**.
- The complete test suite was not run. CI currently has unbounded test commands and suppresses failures in several checks.

## Repository boundary and change preservation

| Check | Result |
|---|---|
| Backend repository | `D:\cac\AI-Interviewer-Adaptive-Multimodal-AI-Interview-Platform`, branch `main`, origin is the backend repository. |
| UI repository | `D:\cac\AI_platform_UI`, branch `master`, origin is the UI repository. |
| UI worktree | Clean before and after this work; not modified. |
| Existing backend work | P0.1–P0.6 changes remain in the worktree and were not reverted. |
| Commits or pushes | None. |

## Verified behavior

### Authentication, ownership, reports, and WebSockets

- Protected API routes use the authenticated database user and deny anonymous access.
- Candidate reads and writes are filtered to the authenticated candidate or owning recruiter. Candidate update fields are allow-listed; candidate and interview ownership are server controlled.
- Interview reads and turns are checked using database-side ownership queries. Recruiter access requires the interview owner and candidate owner to match the recruiter; candidate access requires the candidate profile to link to that candidate user.
- Report JSON/text export first obtains the interview through the same authorized interview service query before loading report data.
- Both interview WebSocket routes authenticate the token, resolve the user from the database, and authorize interview access before accepting/starting the session.
- Admin-wide reads are an explicit role and are recorded in `access_audit`; public registration creates candidate accounts, not admins.
- Deterministic offline authorization tests cover anonymous access, cross-owner access, forged ownership, reports/downloads, WebSockets, and successful authorized requests.

### Tenant and account-linking boundary

- There is no organization/company or membership table. Organization identifiers appear as RAG document metadata only.
- Existing data has nullable candidate owner/account-link fields. Legacy unowned records are not automatically attributed; controlled admin review/assignment is still required.
- Recruiter-created candidate records do not have a secure production flow for linking the candidate's later account. Direct linking in the live E2E fixture is test-only.
- RAG filters exclude scoped documents when a request is unscoped, but they are retrieval filters, not an API authorization boundary. Organization metadata must not be treated as authenticated tenant identity.
- **Supported boundary:** controlled, isolated single-tenant synthetic demo only. **Not supported:** multi-tenant demo or production customer data.

### Persistence, evaluation, RAG, and reports

- The active path is FastAPI → SQLAlchemy → configured database. Alembic owns schema changes; development startup initializes metadata only in development/test. Existing offline migration evidence reached `a4d2_resource_ownership (head)` on a temporary SQLite database; no migration was added in this task.
- Interview turn writes use transactions and preserve duplicate-turn replay and conflicting-answer rejection. The cross-process idempotency regression passed in the focused run.
- Structured evaluation is schema-validated and persisted with the interview turn. Controlled offline tests exercise malformed output, provider timeout handling, retryable state, and persistence failure paths; these do not establish provider quality.
- RAG stores document metadata and optional vectors in SQLAlchemy. When embeddings are unavailable or invalid, retrieval is explicitly labeled lexical-only rather than silently substituting hash vectors.
- Prior P0.6 lexical-only benchmark: 8 queries; Recall@5 0.893; MRR@5 0.929; 0 dense candidates; 8 lexical fallbacks; forbidden-scope checks 1/1. This is not semantic retrieval evidence.
- No Celery task decorators, shared-task entrypoints, or `.delay()` enqueue calls were found in the Python sources searched. The API's synchronous request paths were covered; a production worker deployment was not verified.

### Production/bootstrap safety

- `Settings` now defaults `ENABLE_DEV_ADMIN_BOOTSTRAP` to false and both bootstrap credentials to empty.
- `UserStore.ensure_default_admin` no longer has known-value default arguments. Explicitly enabling development/test bootstrap without credentials raises an error.
- Production startup validates `SECRET_KEY` (configured, non-placeholder, and at least 32 characters) and refuses enabled development-admin bootstrap. Production skips development database initialization and admin creation.
- The default local API host is now `127.0.0.1`. Docker Compose separately binds its container server to `0.0.0.0`; do not expose it publicly without deployment-specific controls.
- `.env.example` documents the disabled bootstrap defaults and local-only opt-in. No secrets were printed or added to source.
- `/health/ready` now disposes its database probe, closes its Redis probe, and returns HTTP 503 when a dependency is unavailable. Both ready and failed dependency behavior are covered by focused tests.

## Findings and priorities

| Priority | Finding | Status / required action |
|---|---|---|
| P0 | No organization-level authorization or tenant membership model. | **Open release blocker.** Keep use to an isolated single-tenant synthetic demo until the model, migrations, and cross-tenant tests exist. |
| P0 | Recruiter-to-candidate account linking and legacy ownership assignment are incomplete. | **Open release blocker.** Implement an authorized, auditable linking/assignment workflow before onboarding real candidate accounts or using legacy records. |
| P1 | Live model output, real embeddings, live E2E, PostgreSQL, and production deployment have not been verified in this environment. | **Blocked/unverified.** Run only with authorized credentials, isolated databases, operator-controlled spend caps, and human review. |
| P1 | CI's full unit command has no explicit timeout; integration tests and pylint, mypy, and bandit commands suppress failures with `|| true`. | **Open reliability gap.** The next smallest safe engineering task is to make CI bounded and failure-signaling, then split known slow tests into separately capped jobs. |
| P2 | Full-suite completion and provider-backed semantic quality remain unknown. | **Not run / blocked.** Do not infer a pass from focused tests or lexical metrics. |

## Current environment and live-provider status

Readiness was checked by printing only presence/absence, never values:

| Variable/resource | Status |
|---|---|
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | Absent |
| `RUN_LIVE_AI_TESTS`, `RUN_LIVE_AI_E2E` | Absent |
| `LIVE_AI_E2E_DATABASE_URL`, `DATABASE_URL` | Absent in the process environment during preflight |
| `LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `LIVE_AI_SPEND_CAP_USD` | Absent |
| Backend `.env` file | Absent |

**Live provider calls:** none. The live smoke/E2E tests were not run as live tests. Prior P0.6 evidence recorded all four as skipped with opt-in flags unset; a skip is not a pass. No live cost was incurred in this assessment.

Before an authorized live run, follow the setup/runbook and the USD $5 maximum provider-side spend limit documented in [P0_6_LIVE_AI_VERIFICATION.md](./P0_6_LIVE_AI_VERIFICATION.md). Use a fresh dedicated SQLite database for E2E, bounded provider timeouts and no automatic retries, synthetic data only, and human review of all six actual model outputs. Never target a shared or production database.

## Validation performed in this task

Tests used the project's Python 3.11 virtual environment. The grouped API/regression command used a unique SQLite file under `storage/` and a 110-second subprocess timeout; the standalone security-default test and skipped opt-in test command used 30- and 60-second subprocess timeouts, respectively. The whole test suite was not run.

| Command / check | Result |
|---|---|
| Reproduction: `python -m pytest tests/unit/test_security_defaults.py -q` | **Exit 1**, 1 failed in 0.13s (0.94s wall). The new test observed that admin bootstrap defaulted to enabled. |
| Focused regressions: `python -m pytest tests/unit/test_security_defaults.py tests/unit/test_api_readiness.py tests/unit/test_api_interview.py tests/unit/test_auth_candidate_db.py tests/unit/test_production_pipeline.py tests/unit/test_resource_authorization.py tests/unit/test_report_service.py tests/unit/test_semantic_evaluation.py tests/unit/test_evaluation_domain.py tests/unit/test_adaptive_graph.py tests/unit/test_rag_retrieval.py tests/unit/test_rag_semantic_retrieval.py tests/unit/test_voice_websocket.py tests/unit/test_interview_hardening.py tests/integration/test_phase115c_application_concurrency.py::test_cross_process_interview_service_commits_one_turn_and_replays_idempotently -q -rs` | **Exit 0**, 80 passed, 1 skipped; pytest 16.83s, wall 17.77s. Skip: live embedding test requires credentials/provider configuration. |
| Recheck: `python -m pytest tests/unit/test_security_defaults.py -q` | **Exit 0**, 2 passed; pytest 0.79s, wall 1.70s. |
| Opt-in tests without live configuration: `python -m pytest tests/unit/test_live_provider_smoke.py tests/integration/test_live_interview_e2e.py -q -rs` | **Exit 0**, 4 skipped; pytest 0.26s, wall 1.14s. Three smoke cases required `RUN_LIVE_AI_TESTS=1`; E2E required `RUN_LIVE_AI_E2E=1`. No live request was made. |
| Live readiness preflight | **BLOCKED**, all required credentials/flags/database configuration listed above were absent; no request was attempted. |
| `ruff check services/user_store.py tests/unit/test_api_readiness.py tests/unit/test_security_defaults.py tests/unit/test_api_interview.py tests/unit/test_production_pipeline.py` | **Exit 0**. |
| `ruff check config/settings.py services/user_store.py apps/api/main.py tests/unit/test_api_readiness.py tests/unit/test_security_defaults.py tests/unit/test_api_interview.py tests/unit/test_production_pipeline.py` | **Exit 1**, five pre-existing findings: `W293` at `apps/api/main.py:72,74`; `UP007` at `config/settings.py:140,141`; `UP011` at `config/settings.py:166`. These unrelated lines were not changed. |
| `git diff --check` | **Exit 0**. |
| Pylance `checkSignatureCompatibility` for `UserStore.ensure_default_admin` | All 1 call site compatible with the explicit `email` and `password` parameters. |
| Full test suite | **NOT RUN**, to avoid the previously observed unbounded/hanging workflow. |

The focused regression command was run after changing startup defaults and explicitly seeding test admins. It covers the production bootstrap guard, API authentication, ownership authorization, reports, WebSockets, RAG fallback/scope, evaluation persistence, adaptive graph, and cross-process idempotency. It does not prove live provider behavior, production PostgreSQL operation, or multi-tenant isolation.

## Safe operator commands

Run offline tests from the backend repository using its `.venv` and a fresh, dedicated SQLite file. In PowerShell:

```powershell
$runId = [guid]::NewGuid().ToString("N")
New-Item -ItemType Directory -Force storage | Out-Null
$dbFile = "storage\test_backend_readiness_$runId.db"
if (Test-Path -LiteralPath $dbFile) { throw "Refusing to reuse test database: $dbFile" }
$env:DATABASE_URL = "sqlite:///./" + ($dbFile -replace '\\', '/')
$env:ENVIRONMENT = "test"
$env:ENABLE_DEV_ADMIN_BOOTSTRAP = "false"
.\.venv\Scripts\python.exe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Isolated test database migration failed." }
.\.venv\Scripts\python.exe -m pytest tests\unit\test_security_defaults.py tests\unit\test_api_readiness.py tests\unit\test_api_interview.py tests\unit\test_auth_candidate_db.py tests\unit\test_production_pipeline.py tests\unit\test_resource_authorization.py tests\unit\test_report_service.py tests\unit\test_semantic_evaluation.py tests\unit\test_evaluation_domain.py tests\unit\test_adaptive_graph.py tests\unit\test_rag_retrieval.py tests\unit\test_rag_semantic_retrieval.py tests\unit\test_voice_websocket.py tests\unit\test_interview_hardening.py tests\integration\test_phase115c_application_concurrency.py::test_cross_process_interview_service_commits_one_turn_and_replays_idempotently -q -rs
```

The pytest safety guard accepts this `storage\test_*.db` URL and rejects missing, default, and non-SQLite database URLs. The command refuses to reuse an existing file before migration. Before migrations or live E2E, confirm the database URL is a new SQLite test path and not equal to any shared or production URL. Preserve the live-run limits and spend cap in the P0.6 runbook. Never print secret values, put them in command history, or commit `.env`.

## Changed files in this assessment

- `config/settings.py`: safe local bind and opt-in/empty development bootstrap defaults.
- `services/user_store.py`: require explicit admin bootstrap credentials.
- `.env.example`, `README.md`: describe explicit local bootstrap and loopback behavior.
- `tests/unit/test_security_defaults.py` (new): test safe defaults and explicit credential requirement.
- `tests/unit/test_api_interview.py`, `tests/unit/test_production_pipeline.py`: create isolated test admins rather than relying on a default account.
- `apps/api/main.py`, `tests/unit/test_api_readiness.py` (already changed during this assessment): readiness status and probe cleanup fix with regression tests.

## Next steps

1. Make CI test/quality checks bounded and remove failure suppression; keep integration tests independently capped.
2. Complete organization membership, tenant-scoped database queries, migrations, and cross-organization tests before any multi-tenant use.
3. Design a secure candidate account-linking and legacy-record assignment workflow.
4. Have an authorized operator run P0.6 live smoke/E2E verification with a dedicated SQLite database and the documented spend cap; require human review of the six real outputs.
5. Verify PostgreSQL and deployment configuration in a controlled environment before production use.

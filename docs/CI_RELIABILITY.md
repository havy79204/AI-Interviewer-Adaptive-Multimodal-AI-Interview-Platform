# CI Reliability

## CI audit findings

Findings recorded before editing:

- `.github/workflows/test.yml:58,70,74,88` used `|| true` on pylint, mypy, bandit, and the integration suite, so those failures were reported as success.
- `.github/workflows/test.yml:47-88` had no job-level timeout; the full unit suite had no per-test timeout, and integration tests were run without a limit.
- `.github/workflows/test.yml:46` installed `requirements-dev.txt`, which is absent from the repository. Test/development dependencies are declared in `requirements.txt` and `pyproject.toml`.
- `.github/workflows/test.yml:95-101` treated Codecov upload failure as non-fatal; coverage was not made a required check in the replacement workflow.
- `.github/workflows/test.yml:104-112` contained a staging “deployment” that only echoed text. It was removed so CI no longer reports a placeholder as a deployment.
- `pyproject.toml:182-200` registered test markers but did not configure per-test timeouts or a timeout plugin.
- `tests/integration/test_phase115c_application_concurrency.py:118-158` starts multiprocessing workers and waits on a result queue; before this change it had no `finally` cleanup if a wait/assertion failed.
- `tests/integration/test_phase115c_application_concurrency.py:201-240` starts Uvicorn subprocesses; its cleanup used `terminate()` followed by a bounded 10-second wait that could raise without killing the child.
- `tests/isolated/test_distributed_lock_verification.py:214` contains a 10-second sleep in a worker process; the parent test has bounded waits, but a test timeout is also needed to contain failures.
- `tests/integration/test_live_interview_e2e.py:18,45-68,502-505` already has a 300-second workflow deadline, explicit opt-in, required credential checks, and a dedicated SQLite URL requirement. Live tests already skip with reasons when opt-in/configuration is absent; they are not considered passes.
- Test exception handling inspected in the concurrency worker reports an error outcome that parent assertions reject; the live E2E helper turns errors into `pytest.fail`. These were not silent success paths.

## Workflow structure

`.github/workflows/test.yml` now defines:

| Job | Scope | Python | Maximum job time |
|---|---|---|---:|
| `quality` | Focused Ruff checks and `git diff --check` on the push/PR change range | 3.11 | 10 minutes |
| `test-groups` | `fast-unit`, `api-security-report`, `database-concurrency`, `websocket-voice`, and synthetic `rag` groups | 3.11 and 3.12 | 30 minutes per group/runtime |
| `live-provider` | Optional real-provider smoke plus isolated interview E2E; manual dispatch only | 3.11 | 20 minutes |

Test groups run independently (`fail-fast: false`) with a Redis service. Test databases use per-run/per-group/per-Python-version SQLite paths. Each group applies Alembic migrations to its isolated URL before tests; the database/concurrency group also records `alembic current`. PostgreSQL is not part of this workflow and remains unverified here.

The test job installs `requirements.txt`; the nonexistent `requirements-dev.txt` installation was removed. The redundant black/isort checks and lint/type/security commands whose results were suppressed were removed. Ruff is the required lint tool in CI and includes import ordering under project configuration. The previous coverage upload is omitted because the new group commands do not generate a coverage artifact.

## Timeout policy and process cleanup

- `pytest-timeout==2.3.1` is pinned in both `requirements.txt` and the `dev` optional dependency list in `pyproject.toml`.
- Pytest defaults to a **90-second per-test timeout** using the portable thread method. Linux CI overrides this with signal mode, which raises a pytest failure and allows fixture teardown to clean up child processes. CLI options repeat the timeout policy so the group command remains explicit.
- CI group jobs are capped at **30 minutes**; quality is capped at **10 minutes**.
- The live smoke tests use a 90-second test timeout. The live E2E has a **360-second pytest timeout**, allowing its existing **300-second internal deadline** plus cleanup.
- The live tests set a 10-second provider timeout, disable provider retries, cap model output at 900 tokens, and enforce their existing finite request budgets (up to 40 LLM and 40 embedding calls for E2E; the smoke tests contain a fixed small set of synthetic cases). The optional job requires an operator to confirm a provider-side spend cap of no more than **USD $5**.
- The concurrency test now terminates/joins spawned Python workers in `finally`, killing a worker if graceful termination does not finish within five seconds. The Uvicorn fixture similarly terminates, waits five seconds, and kills/reaps a child that remains alive.
- The thread method works on Windows but terminates the pytest process if a test remains blocked; it does not run fixture teardown at that point. CI uses Linux signal mode so normal test cleanup runs. The integration fixtures also have their own bounded terminate/wait/kill cleanup.

No automatic retries were added to CI. Live tests remain disabled on push/PR and require a manual `workflow_dispatch` with both `run_live_ai` and `confirm_live_ai_spend_cap` enabled. If the operator enables that job but the `OPENAI_API_KEY` secret is absent, the credential preflight fails rather than silently skipping. The E2E uses a fresh SQLite file under `RUNNER_TEMP`, named with the workflow run and attempt identifiers; no shared database secret is used.

## Required versus optional checks

Required on push and pull request:

- Focused Ruff on the CI-sensitive readiness, bootstrap, provider smoke, concurrency, and live E2E test files.
- `git diff --check` on the event change range.
- Quality job probes verify Bash exit-code propagation and confirm a timed-out pytest test reports failure and reaps its child process.
- All five offline test groups on Python 3.11 and 3.12.
- Isolated SQLite Alembic upgrade in each group, and `alembic current` in the database/concurrency group on Python 3.11.

Optional:

- Live provider job is available only by manual dispatch and explicit spend-limit confirmation. A skipped live job is not evidence of provider success.
- Codecov upload is no longer a check and no longer runs without a generated coverage report.
- Staging deploy was a no-op placeholder, not a real deployment, and has been removed.

Ruff findings outside the focused target are not claimed as clean. The prior backend-wide Ruff probe found legacy issues including long lines and import/unused-import findings, plus earlier checks found existing `W293`, `UP007`, and `UP011` findings in `apps/api/main.py` and `config/settings.py`. Those unrelated issues are recorded rather than hidden by broad automatic formatting.

## Local reproduction

Run from the backend repository with the project virtual environment. On PowerShell:

```powershell
$runId = [guid]::NewGuid().ToString("N")
$env:REDIS_URL = "redis://localhost:6379/0"
$env:ENVIRONMENT = "test"
$env:ENABLE_DEV_ADMIN_BOOTSTRAP = "false"
New-Item -ItemType Directory -Force storage | Out-Null

function Initialize-IsolatedTestDatabase([string]$Group) {
    $databasePath = "storage\ci_local_${runId}_${Group}.db"
    $storageItem = Get-Item -LiteralPath "storage" -Force
    if ($storageItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Refusing to migrate through a storage symlink or junction."
    }
    if (Test-Path -LiteralPath $databasePath) {
        throw "Refusing to reuse an existing test database: $databasePath"
    }
    $env:DATABASE_URL = "sqlite:///./storage/ci_local_${runId}_${Group}.db"
    @'
import os
from pathlib import PurePosixPath
from sqlalchemy.engine import make_url
url = make_url(os.environ["DATABASE_URL"])
path = PurePosixPath(url.database.replace("\\", "/"))
assert url.drivername == "sqlite" and len(path.parts) == 2
assert path.parts[0] == "storage" and path.name.startswith("ci_local_")
assert path.name.endswith(".db") and ".." not in path.parts
assert os.environ.get("ENVIRONMENT") == "test"
'@ | .\.venv\Scripts\python.exe -
    if ($LASTEXITCODE -ne 0) {
        throw "Refusing migration: isolated test database preflight failed."
    }
    .\.venv\Scripts\python.exe -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Isolated test database migration failed."
    }
}
```

The helper creates a unique database per group, refuses to reuse an existing file, rejects a storage symlink/junction, checks its SQLite URL and `storage\ci_local_...` name, sets test mode, and only then runs Alembic. `tests\conftest.py` independently refuses pytest if `DATABASE_URL` is missing, non-SQLite, outside the approved test-file naming convention, does not resolve directly under repository `storage`, or if `ENVIRONMENT` is not `test`. The sole absolute-path exception requires the live-E2E opt-in, identical `DATABASE_URL` and `LIVE_AI_E2E_DATABASE_URL`, and a fresh, non-symlink database file directly under `RUNNER_TEMP` (or the system temporary directory locally). The CI migration preflight applies the same repository-local and no-symlink checks and rejects an already existing database file before migration. Do not run Alembic manually against `ai_interviewer.db`, a production URL, or a shared database. Use a dedicated Redis instance for the concurrency group; its Redis tests use namespaced keys but still perform real writes.

Focused quality checks:

```powershell
.\.venv\Scripts\python.exe -m ruff check tests\unit\test_api_readiness.py tests\unit\test_security_defaults.py tests\unit\test_live_provider_smoke.py tests\integration\test_phase115c_application_concurrency.py tests\integration\test_live_interview_e2e.py
git diff --check
```

Fast unit/domain:

```powershell
Initialize-IsolatedTestDatabase "fast-unit"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_adaptive_graph.py tests\unit\test_evaluation_domain.py tests\unit\test_interview_core.py tests\unit\test_llm_provider.py tests\unit\test_phase11_infrastructure.py tests\unit\test_security_defaults.py tests\unit\test_turn_state.py -m "not live" --timeout=90 --timeout-method=thread -ra --durations=20
```

API, authorization, evaluation, and reports:

```powershell
Initialize-IsolatedTestDatabase "api-security-report"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_api_interview.py tests\unit\test_api_readiness.py tests\unit\test_auth_candidate_db.py tests\unit\test_interview_hardening.py tests\unit\test_production_pipeline.py tests\unit\test_report_service.py tests\unit\test_resource_authorization.py tests\unit\test_semantic_evaluation.py -m "not live" --timeout=90 --timeout-method=thread -ra --durations=20
```

Database/migrations/concurrency:

```powershell
Initialize-IsolatedTestDatabase "database-concurrency"
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m pytest tests\unit\test_database_integrity.py tests\integration\test_phase115c_application_concurrency.py tests\isolated\test_distributed_lock_verification.py -m "not live" --timeout=90 --timeout-method=thread -ra --durations=20
```

This group needs a reachable Redis at `REDIS_URL` for the Redis-backed integration tests. Do not point it at shared data; test keys are namespaced, but a dedicated local/CI Redis is preferred.

WebSocket and voice:

```powershell
Initialize-IsolatedTestDatabase "websocket-voice"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_voice_phase10.py tests\unit\test_voice_session.py tests\unit\test_voice_websocket.py -m "not live" --timeout=90 --timeout-method=thread -ra --durations=20
```

Synthetic RAG:

```powershell
Initialize-IsolatedTestDatabase "rag"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_rag_evaluation.py tests\unit\test_rag_metrics.py tests\unit\test_rag_retrieval.py tests\unit\test_rag_semantic_retrieval.py -m "not live" --timeout=90 --timeout-method=thread -ra --durations=20
```

The five groups above cover the current offline collection. Keep each `Initialize-IsolatedTestDatabase` call in the same PowerShell session as its matching pytest command; the helper assigns a distinct SQLite file and migrates only that file. Do not reuse the URL after the session; obtain a new `$runId` for the next diagnostic run.

The `live-provider` workflow job is deliberately not reproducible from a normal push/PR job. Authorized operators should use `workflow_dispatch`, configure `OPENAI_API_KEY` as a repository/environment secret, set both confirmation inputs, and review [P0_6_LIVE_AI_VERIFICATION.md](./P0_6_LIVE_AI_VERIFICATION.md). The job creates its own dedicated SQLite E2E database.

## Validation of timeout and failure propagation

Local validation used Python 3.11.9, a separate migrated SQLite database per group, `--timeout=90`, and the Windows-compatible thread timeout mode:

| Group | Result | Pytest duration | Command exit |
|---|---:|---:|---:|
| `fast-unit` | 38 passed | 1.60 s | 0 |
| `api-security-report` | 35 passed | 11.49 s | 0 |
| `database-concurrency` | 18 passed | 10.07 s | 0 |
| `websocket-voice` | 34 passed | 1.84 s | 0 |
| `rag` | 25 passed, 1 skipped | 0.79 s | 0 |

The elapsed time including each isolated migration and process startup was 8.45 s, 21.31 s, 16.87 s, 11.51 s, and 10.45 s respectively. Each migration reached `a4d2_resource_ownership (head)`. The RAG skip is the opt-in live embedding smoke test, skipped because it requires `OPENAI_API_KEY` and `EMBEDDING_PROVIDER=openai`; it is not counted as a pass.

Additional checks:

- PyYAML parsed the workflow, and structural assertions passed for all three jobs, explicit job timeouts, all five groups, existing test paths, and both quality probes. This is YAML parsing and structural inspection, not GitHub Actions schema validation. `actionlint` was not available locally.
- Focused Ruff completed with exit 0; `git diff --check` completed with exit 0.
- Under Git Bash `-e -o pipefail`, a deliberate `exit 23` was observed as exit 23 by the caller.
- A disposable 30-second test run with `--timeout=1 --timeout-method=thread` was stopped by pytest and returned exit 1 with timeout diagnostics. The temporary test was removed. Windows thread mode does not run fixture teardown on a hard timeout, so this local probe does not verify child cleanup.
- The Linux CI quality job now runs the corresponding signal-mode timeout probe with a subprocess fixture and checks that teardown reaps the child. That Linux-only child-cleanup probe is defined but has not yet been executed in GitHub Actions.

The initial P0.8 voice run emitted a `RuntimeWarning` about an unawaited `AsyncMockMixin._execute_mock_call` in `test_tts_error_does_not_remove_question`; P0.9 traces and fixes this test-double issue below. The full suite was not run. Python 3.12 CI matrix jobs, live-provider tests, PostgreSQL support, and tenant isolation are not verified by those local results.

These focused passes do not establish full-suite completion, live provider behavior, PostgreSQL support, or tenant isolation.

## P0.9 — GitHub CI and voice warning verification

### GitHub Actions execution status

The latest available GitHub run when checked was [run #16](https://github.com/tri01012002/AI-Interviewer-Adaptive-Multimodal-AI-Interview-Platform/actions/runs/37752953942), on commit `722b45e623977b70d749e603e0b8d06aacbebbb6` (2026-10-08). It failed before checkout or test execution: both jobs attempted to start the PostgreSQL service image `pgvector/pgvector:pg15-latest`, which failed to pull because the manifest was not found. The Python 3.11 job was cancelled and the Python 3.12 job failed during container initialization. **Neither runtime reached setup or ran tests, and this was the previous workflow revision—not the P0.8 workflow currently in the worktree.**

The current worktree version is still uncommitted. Therefore there is no GitHub Actions result for the current workflow, no verified Python 3.11/3.12 CI matrix result, and no actual Linux signal-timeout/child-cleanup result. Do not treat run #16 as validation of those changes.

To execute the current offline workflow without making provider calls:

1. An authorized repository owner must publish the existing worktree changes in a branch/PR targeting `main` or `develop` (or merge them there). No commit or push was made for this task.
2. Confirm the `Backend CI` workflow is present on the branch being tested. It runs on pushes to `main`/`develop`, pull requests targeting either branch, and manual dispatch.
3. In GitHub Actions, select **Backend CI → Run workflow**, choose the branch containing the workflow, and leave both `run_live_ai` and `confirm_live_ai_spend_cap` false. Both default to false; the live-provider job must remain skipped for this offline validation.
4. After the first completed run, configure branch protection/rulesets to require the quality job and each desired `test-groups` Python-version/group check. Check names should be taken from the actual run; the group matrix produces five groups across Python 3.11 and 3.12. Branch-protection configuration was not accessible for this local verification.

### Voice warning reproduction and correction

The warning reproduced in the smallest test:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_voice_phase10.py::TestProviderErrorNormalization::test_tts_error_does_not_remove_question -W always::RuntimeWarning --timeout=30 --timeout-method=thread -ra
```

It came from the test setup, not production code. `VoiceSessionService` iterates `self.tts.stream(...)` as an async iterator. The test assigned an `AsyncMock` with an exception `side_effect`; calling it returned a coroutine, not an async generator. The async iteration raised a `TypeError` before the mock coroutine could be awaited, and the coroutine was later reported as unawaited. The broad TTS failure handler let the existing TTS error assertion pass despite the inaccurate mock.

The test now supplies an async-generator mock that raises the intended `TTSProviderError` when iterated. The focused test passed **1/1, exit 0**, with `RuntimeWarning` visible and absent. With an isolated, migrated SQLite database, the full voice/session/WebSocket regression group passed **34/34, exit 0**, with no unawaited-`AsyncMock` warning. A separate first attempt without an explicit database override failed in the authenticated WebSocket test because the configured database schema lacked `candidates.owner_user_id`. The test calls `UserStore.create` first; a read-only inspection found the synthetic `voice-websocket@example.com` user already existed with a creation timestamp from the prior day, so this failed attempt returned the existing record instead of inserting another. No explicit cleanup was performed against the configured default database; only named disposable P0.9 SQLite files were removed.

### Provider opt-in and collection

Collection used Python 3.11.9 and:

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q -m "not live" --timeout=90 --timeout-method=thread
```

It completed in under one second with **150/155 tests collected and 5 deselected** (exit 0). The selected tests mapped exactly once to the five workflow groups:

| CI test group | Collected tests |
|---|---:|
| `fast-unit` | 38 |
| `api-security-report` | 35 |
| `database-concurrency` | 18 |
| `websocket-voice` | 34 |
| `rag` | 25 |

The five deselected tests are explicitly marked live: three provider smoke cases, the live interview E2E, and the OpenAI embedding smoke test. The latter previously relied only on `skipif` and could have made a real call in an offline group if credentials happened to be present; it now carries the `live` marker as well. During this check the configured OpenAI credential was absent, `LLM_PROVIDER` was `none`, and live opt-in flags were false. Secret values were not printed. Collection did not execute tests or contact providers. The database/concurrency group requires its isolated SQLite database and Redis service; the existing cross-process tests also launch local API subprocesses with bounded health/request/process waits.

The full suite was **not executed**. Collection is not a pass for test behavior. Current bounded group evidence is the P0.8 table above plus the P0.9 voice rerun (**34 passed**) and RAG rerun (**25 passed, 1 deselected; exit 0**). The RAG rerun confirms the provider test is filtered out under `-m "not live"`.

### Local workflow and lint validation

- PyYAML parsing and structural assertions passed: all three jobs declare timeouts (10/30/20 minutes), Python 3.11 and 3.12 are configured, all five group paths exist and map the selected collection without overlap, offline test commands use `-m "not live"`, and group databases are run-specific SQLite files. The workflow uses a Redis service, has explicit manual live opt-in and spend confirmation, and contains no `continue-on-error` or `|| true` suppression.
- The live key is injected as an Actions secret and only checked for non-emptiness; the workflow does not echo or print its value. The E2E database is unique under `RUNNER_TEMP`.
- `actionlint` is unavailable locally. No GitHub-hosted validation ran against the current uncommitted workflow, so GitHub expression/schema validation remains outstanding.
- The changed RAG test file passes Ruff. The voice test file has 26 pre-existing Ruff diagnostics elsewhere in the file (import ordering/unused imports and whitespace); none falls in the changed test region. Those unrelated findings were not mass-fixed. `git diff --check` passed.
- The Linux signal-mode timeout-cleanup contract remains unverified until the current workflow actually runs on GitHub. The local Windows thread-mode timeout probe proves a hung test fails but cannot prove Linux fixture cleanup.

**Next step:** publish the current workflow changes only with repository-owner authorization, then inspect the actual `Backend CI` run for both Python versions and the Linux timeout-cleanup result. Do not run the full suite until that workflow succeeds and the previously unexplained long-running full-suite stall is localized or safely bounded by the CI job deadline.

## P0.10 — Database isolation and bounded full-suite diagnosis

### Infrastructure finding

The available GitHub run #16 logs establish that the prior workflow failed during service-container initialization because the `pgvector/pgvector:pg15-latest` image manifest could not be pulled; no test ran in that run. The current workflow definition has no PostgreSQL or pgvector service. Its offline groups use SQLite, synthetic fixtures, and a Redis service for the distributed-lock and cross-process tests. PostgreSQL remains unsupported/unverified by this offline workflow; a missing PostgreSQL container is not replaced with a fake success.

The current workflow's migration step first checks that `DATABASE_URL` is repository-local SQLite under `storage/`, uses the `ci_*.db` naming convention, and has `ENVIRONMENT=test`. The new `tests/conftest.py` enforces test mode and an isolated SQLite URL before pytest collection, rejecting missing URLs, non-SQLite URLs, parent traversal, and non-test filenames. Unit/integration tests that call `Base.metadata.create_all` use their explicit test engine or the isolated group URL; migration-bearing workflow and local commands initialize a unique database before use. The live E2E separately requires its dedicated `live_ai_e2e_*.db` URL. No existing default application database was cleaned, migrated, or otherwise modified by this validation.

### Current bounded test evidence

After adding the pytest safety guard, the five workflow groups were each rerun on Python 3.11.9 against separate, fresh, migrated SQLite files; all returned exit code 0:

| Group | Result | Pytest duration | Command duration |
|---|---:|---:|---:|
| `fast-unit` | 38 passed | 1.54 s | 2.79 s |
| `api-security-report` | 35 passed | 12.84 s | 14.06 s |
| `database-concurrency` | 18 passed | 12.13 s | 13.31 s |
| `websocket-voice` | 34 passed | 1.97 s | 3.24 s |
| `rag` | 25 passed, 1 live test deselected | 0.70 s | 2.16 s |

These five bounded group runs cover the current offline group definitions: **150 passed** and one live-provider test was deselected. The RAG run was offline; no provider calls were made. Redis was reachable for the concurrency group, and each migration reached `a4d2_resource_ownership (head)`. After adding the pytest startup guard, a fresh migrated test database was used for collection: `pytest --collect-only -q -m "not live" --timeout=90 --timeout-method=thread` completed with **150/155 collected, 5 deselected**, exit 0, in 5.83 seconds including migration/startup.

The historical single full-suite run's exact last test and blocking operation were not retained, and the 69% stall was not reproduced. The current five groups passed separately, but this is not evidence that the historical cause is known or that a single-process full-suite run passes. No unbounded/full-suite run was started. Collection alone also does not establish test behavior.

The pytest guard was checked with both a missing database URL and the application's default database URL; pytest refused both with exit code 4 before collection, giving the required isolated-database guidance. A valid isolated URL was accepted by all five group runs. A pre-existing synthetic user in the default local database was left untouched.

After tightening the guard to reject storage/database symlinks and extracting its path checks for lintability, the fresh-database fast group was rerun: **38 passed**, exit 0 (1.34 seconds); guarded collection again returned **150/155 collected, 5 deselected**, exit 0 (0.78 seconds). The documented local database helper also completed its isolated preflight and Alembic migration. No database changes targeted the default application SQLite file.

### Timeout probe and CI validation status

The Linux quality job's fault-injection probe uses a dedicated process group for its temporary pytest process, registers fixture cleanup for its disposable child, enforces a 1-second test timeout and a 15-second outer deadline, and terminates only that probe-owned process group if the outer deadline is exceeded or the child remains. This revised probe has **not** run on Linux yet; its cleanup result is **NOT VERIFIED**. Local Windows thread-timeout evidence does not establish Linux signal handling or child cleanup.

The workflow has explicit 10-minute quality, 30-minute offline test-group, and 20-minute live-job deadlines; uses Python 3.11/3.12 in its matrix; filters offline groups using `-m "not live"`; and does not define a PostgreSQL service. Offline jobs do not inject provider credentials. Live tests require manual dispatch, both opt-in confirmations, and the `OPENAI_API_KEY` secret. The workflow source avoids printing the secret. Local `actionlint` is unavailable; prior YAML parsing and structural assertions are not a substitute for GitHub Actions schema validation. No completed GitHub Actions run has used this current uncommitted workflow, so both matrix runtimes, Linux timeout cleanup, and actual GitHub workflow validation remain **NOT VERIFIED**.

### Safe local reproduction and owner publication

Use the PowerShell setup and `Initialize-IsolatedTestDatabase` helper under **Local reproduction** above, then run each matching group command in the same session. Those commands use a new group database and bounded per-test timeouts; the concurrency group additionally needs a dedicated reachable Redis. To repeat guarded collection, initialize a fresh database and run:

```powershell
Initialize-IsolatedTestDatabase "collect"
.\.venv\Scripts\python.exe -m pytest --collect-only -q -m "not live" --timeout=90 --timeout-method=thread
```

The local Windows thread timeout is not equivalent to the workflow's Linux signal timeout. Do not run Alembic against the app's default database, and do not reuse a group DB name on a later run; use a new `$runId`.

**Publication checklist for the repository owner:**

1. Review the uncommitted backend changes and publish them through the normal authorized branch/PR process; this task did not commit, push, or dispatch a workflow.
2. Trigger **Backend CI** on that published revision with both live-provider inputs false.
3. Confirm the quality checks and all five groups complete for Python 3.11 and 3.12. Verify the disposable-child timeout cleanup output on the Linux quality job.
4. Only after observing the run, configure branch protection to require the actual check names shown by GitHub. Keep provider-backed verification as a separately authorized manual run with its dedicated secret and spend cap.

UI repository was not modified. Remaining limitations: historic stall cause unresolved; no monolithic full-suite run; no local actionlint or GitHub schema result for the current worktree; no current-workflow GitHub result; and Linux signal/child cleanup is unverified until that workflow runs.

## P0.11 — Pre-publication review status

No files were staged, committed, pushed, or dispatched. The pre-publication review found that the earlier pytest guard accepted any absolute path with a `live_ai_e2e_` filename. It now additionally requires explicit `RUN_LIVE_AI_E2E=1`, a `LIVE_AI_E2E_DATABASE_URL` equal to `DATABASE_URL`, and a fresh non-symlink database directly under `RUNNER_TEMP` (or the system temporary directory for local runs). The local database instructions in `docs/BACKEND_READINESS.md` now use a fresh `storage/test_*.db` file and reject reuse before applying migrations.

Guard checks after this correction: approved relative `storage/ci_*.db` URL accepted; missing URL, application default URL, PostgreSQL URL, and an absolute live-style path outside the temporary root each refused with pytest exit 4; a fresh live-style SQLite path under the temporary root was accepted with explicit opt-in and collection completed (155 tests; exit 0). The test guard passes Ruff, and `git diff --check` passes. No test databases, `.env`, logs, or API credentials were staged; the only credential-like matches in source/documentation scans were synthetic test bootstrap values and an operator placeholder, with values withheld.

The corrected `docs/BACKEND_READINESS.md` setup was also exercised using a unique `storage/test_backend_readiness_*.db`: Alembic upgraded it to `a4d2_resource_ownership (head)`, the focused security-default tests passed (**2 passed, exit 0**), and the named disposable database was removed.

**Publication and GitHub result:** authorization to publish has not yet been given. The worktree is on `main`; no current-revision GitHub run exists. Python 3.11/3.12 GitHub execution, five group results on GitHub, Linux timeout-child cleanup, and GitHub workflow schema validation remain **NOT RUN** for this revision. Do not interpret the local collection or prior P0.10 groups as GitHub verification.

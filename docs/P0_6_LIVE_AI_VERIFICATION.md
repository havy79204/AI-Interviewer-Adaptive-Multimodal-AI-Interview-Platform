# P0.6 Live AI Verification

**Overall status:** BLOCKED for live-provider acceptance; focused offline validation passed.

P0.6 does not pass its live acceptance criteria in this environment. Provider credentials, opt-in flags, and a dedicated E2E database URL were unavailable. No live provider request was made, and no live success is inferred from the skipped tests or lexical benchmark.

## Environment and safety

- Python: project `.venv`, Python 3.11.9.
- `.env` file: absent.
- `OPENAI_API_KEY`: not configured. `ANTHROPIC_API_KEY`: not configured.
- `RUN_LIVE_AI_TESTS`, `RUN_LIVE_AI_E2E`, `LIVE_AI_E2E_DATABASE_URL`, `LLM_PROVIDER`, and `EMBEDDING_PROVIDER`: not configured in the process environment.
- Provider/model values and credentials are not recorded here. No credentials were printed or added to source control.
- Live E2E, real evaluation, and real embedding calls: **none**.
- No shared or production database was migrated or reset. Offline regression tests and migration checks used distinct temporary SQLite files.
- All examples and fixtures use synthetic job, candidate, and answer data.

The opt-in implementation enforces 10-second provider request timeouts, disables provider retries, limits the E2E run to at most 40 LLM calls and 40 embedding calls, and caps LLM output at 900 tokens per request. The E2E has a 300-second overall deadline. The separate live smoke tests are bounded to one structured-evaluation call, six quality-case calls, and three embedding calls at most. These controls cap requests and generated output, but do not calculate or enforce a dollar amount; actual price depends on the configured models and current provider pricing. Before enabling live calls, an authorized operator must configure a provider-side spend limit of **USD $5 maximum for this validation run** and confirm the selected models fit within it. No live cost was incurred in this run.

## Results

| Validation | Status | Result |
|---|---|---|
| Live structured evaluation and response-schema validation | **BLOCKED** | No API key or opt-in configuration; provider was not invoked. Offline typed-output and failure-path tests passed in the focused regression run. |
| Six-case synthetic evaluation quality sample | **BLOCKED** | The live test is prepared, but there are no actual model outputs to assess. Human review was not performed. |
| Real embeddings, persisted retrieval, and fresh-session read | **BLOCKED** | No embedding provider was invoked. The live test checks vector dimensions/numeric values, stored model metadata, fresh retrieval, and unscoped job-data exclusion when enabled. |
| Lexical-only retrieval benchmark | **PASS** | Eight queries; Recall@5 **0.893**; MRR@5 **0.929**; dense candidates **0**; lexical fallback cases **8/8**; forbidden-scope checks **1/1 passed**. This is not a semantic-retrieval result. |
| Semantic retrieval benchmark | **BLOCKED** | No provider was configured; semantic query count was **0**. |
| Complete live interview/report E2E | **BLOCKED** | Opt-in flag, provider key, and dedicated `LIVE_AI_E2E_DATABASE_URL` were unavailable. No migrations, LLM calls, embedding calls, or E2E data writes were made by that skipped test. |
| Focused offline regressions | **PASS** | **98 passed, 1 skipped** across the two offline pytest commands. The skip is a pre-existing opt-in live-embedding case. |
| Isolated SQLite migration check | **PASS** | `alembic upgrade head` succeeded; `alembic current` reported `a4d2_resource_ownership (head)`. |
| Ruff and diff whitespace checks | **PASS** | Focused Ruff passed for both changed Python test files; `git diff --check` passed. |

### Retrieval results, kept distinct

The benchmark ran against the versioned synthetic corpus and evaluation set with no embedding provider configured:

- **Lexical-only baseline:** 8 queries, mean Recall@5 **0.892857**, mean MRR@5 **0.928571**.
- **Semantic/hybrid:** not measured. Dense retrieval candidates: **0**; the benchmark explicitly labeled all 8 cases as lexical fallback.
- **Forbidden scope:** **1/1** benchmark cases excluded the forbidden document. This tests retrieval filtering only; it is not evidence of API authorization or tenant isolation.
- One case had an empty filtered corpus. No hash-based embedding was substituted.

No semantic result set is reported because none was produced by a real embedding provider.

### Synthetic evaluation quality cases prepared, not run

The opt-in live test makes one real structured evaluation call per case and records the expected behavior alongside the validated response fields. The actual-output and human-review columns remain unavailable:

| Case | Expected rubric behavior | Actual provider output |
|---|---|---|
| Strong answer with specific evidence | Recognize owned actions, design detail, and a measured outcome. | **BLOCKED — not invoked** |
| Weak answer with missing evidence | Keep evidence insufficient and request follow-up. | **BLOCKED — not invoked** |
| Partial rubric coverage | Credit the described async choice while retaining missing trade-offs/outcomes. | **BLOCKED — not invoked** |
| Irrelevant answer | Find little or no evidence for Python concurrency. | **BLOCKED — not invoked** |
| Competency gap | Preserve gaps around overload control and failure handling. | **BLOCKED — not invoked** |
| Keyword-only answer | Do not infer ownership or impact from terminology alone. | **BLOCKED — not invoked** |

Schema validity can be asserted automatically by the test; semantic quality and fairness still require human review. No accuracy claim is made from this unexecuted small sample.

### Offline error and authorization coverage

The focused offline tests exercised invalid structured output, normalized provider timeout handling and retryable interview state, provider configuration without credentials, embedding dimension/provider failures, lexical fallback labels, empty filtered retrieval, incomplete/failed report behavior, ownership authorization, WebSocket authorization, and duplicate-turn replay/conflict behavior. These tests do **not** verify provider-side invalid-key, rate-limit, or service-availability behavior against a live service. The provider timeout and malformed-output tests use controlled test doubles.

## End-to-end test contract prepared

When credentials and an isolated database are supplied, the opt-in E2E is intended to verify:

1. Apply Alembic migrations and ingest the synthetic RAG corpus.
2. Verify scoped dense retrieval and persist vectors.
3. Create a synthetic recruiter and candidate; link the candidate profile to the candidate user only inside the isolated test database.
4. Start a two-question interview with a known synthetic competency plan.
5. Submit two synthetic answers and verify live structured evaluation plus adaptive question generation.
6. Replay each identical `turn_id` and answer without duplicating the transcript; reject reuse of that ID with a different answer.
7. Verify the interview and report for the owning recruiter and the candidate; reject another recruiter/candidate for interview access and report JSON/TXT downloads.
8. Verify two persisted completed turns, two assessments, evidence, and a final report based on persisted records.

The direct candidate-profile link above is a test fixture only. It does not implement production account linking. The E2E uses only a SQLite URL containing `live_ai_e2e_`, refuses to proceed if settings were loaded with another database URL, and writes report files under pytest's temporary directory.

## Exact validation commands and results

Commands ran from `D:\cac\AI-Interviewer-Adaptive-Multimodal-AI-Interview-Platform` using `.venv\Scripts\python.exe`. Pytest commands were run through a Python `subprocess.run` wrapper with a 115-second timeout; the retrieval benchmark had a 60-second timeout.

1. `python -m pytest tests/unit/test_live_provider_smoke.py tests/integration/test_live_interview_e2e.py -q -rs`
   **Exit 0; 4 skipped; 1.09 seconds wall time (final rerun).** Three provider smoke tests skipped because `RUN_LIVE_AI_TESTS=1` was not set. The E2E skipped because `RUN_LIVE_AI_E2E=1` was not set. The skip is not a live pass.
2. `python -m pytest tests/unit/test_api_interview.py tests/unit/test_auth_candidate_db.py tests/unit/test_production_pipeline.py tests/unit/test_resource_authorization.py tests/unit/test_report_service.py tests/unit/test_semantic_evaluation.py tests/unit/test_evaluation_domain.py tests/unit/test_rag_semantic_retrieval.py tests/unit/test_rag_retrieval.py tests/unit/test_rag_evaluation.py tests/unit/test_interview_hardening.py tests/unit/test_voice_websocket.py tests/unit/test_llm_provider.py tests/integration/test_phase115c_application_concurrency.py::test_cross_process_interview_service_commits_one_turn_and_replays_idempotently -q -rs`
   **Exit 0; 70 passed, 1 skipped; 6.70 seconds wall time.** Used a unique temporary SQLite URL. The skip was the separate opt-in live embedding case in `test_rag_semantic_retrieval.py`.
3. `python -m pytest tests/unit/test_database_integrity.py tests/unit/test_adaptive_graph.py tests/unit/test_phase11_infrastructure.py tests/unit/test_turn_state.py -q -rs`
   **Exit 0; 28 passed; 1.72 seconds wall time.** Used another unique temporary SQLite URL.
4. `python -m rag.run_evaluation`
   **Exit 0; 0.45 seconds.** Produced the lexical-only figures above; provider/model were null and no dense queries ran.
5. `python -m alembic upgrade head` followed by `python -m alembic current`
   **Both exit 0; 2.81 seconds total.** Used a new temporary SQLite file; current revision was `a4d2_resource_ownership (head)`.
6. `python -m ruff check tests/unit/test_live_provider_smoke.py tests/integration/test_live_interview_e2e.py`
   **Exit 0; 0.12 seconds.**
7. `git diff --check`
   **Exit 0.**

The outputs include existing Pydantic/FastAPI and LangGraph deprecation warnings. No full test suite was run.

## Working-tree changes and remaining limitations

P0.1–P0.5 changes were preserved. P0.6 added/updated only the live-verification test fixtures/assertions, opt-in environment examples, and this report. No application authorization, evaluation, RAG, or frontend code was weakened or changed for this milestone. `git status` showed the earlier P0.1–P0.5 files still uncommitted; they were not reverted.

The existing ownership model is recruiter ownership plus candidate self-access; there is no complete organization/company membership model or production recruiter-to-candidate account-linking flow. RAG scope filters are not an API authorization boundary. The current evidence supports only an isolated single-tenant synthetic demo, not multi-company production or customer data. The live provider behavior, semantic retrieval quality, and full live report flow remain unverified.

## Authorized operator runbook

Provide the key through the approved secret manager or process environment; never add it to `.env.example`, source control, logs, or command history. Set these variables for the smoke run:

```powershell
$env:OPENAI_API_KEY = '<retrieve securely; do not echo>'
$env:LLM_PROVIDER = 'openai'
$env:EMBEDDING_PROVIDER = 'openai'
$env:RUN_LIVE_AI_TESTS = '1'
```

Then run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_live_provider_smoke.py -q -rs
```

For E2E, choose a fresh unique SQLite path and set both database variables to that same path. Do not use a shared or production database:

```powershell
$dbFile = Join-Path $env:TEMP ("live_ai_e2e_{0}.db" -f [guid]::NewGuid().ToString("N"))
$dbUrl = "sqlite:///" + ($dbFile -replace '\\', '/')
$env:LIVE_AI_E2E_DATABASE_URL = $dbUrl
$env:DATABASE_URL = $dbUrl
$env:RUN_LIVE_AI_E2E = '1'
.\.venv\Scripts\python.exe -m pytest tests\integration\test_live_interview_e2e.py -q -rs
```

Keep the approved provider-side spend cap at or below **USD $5** for this bounded synthetic run. Review the recorded provider/model, request counts, latency, schema checks, retrieval ranks, and E2E assertions after execution. Have a human review all six evaluation outputs before making any quality claim. Do not interpret the benchmark's lexical-only numbers as semantic performance.

## Next release blocker

P0.6 live acceptance remains blocked until an authorized operator supplies the provider configuration and isolated E2E database, runs the smoke and E2E commands above, and reviews the resulting outputs. Multi-tenant organization isolation and production candidate-account linking remain separate release blockers before using customer data across companies.

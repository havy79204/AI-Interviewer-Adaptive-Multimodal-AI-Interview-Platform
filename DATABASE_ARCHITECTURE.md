# Database Architecture

## Architecture

The active application path is:

```text
FastAPI -> SQLAlchemy session -> configured database
```

Interview routes retain the existing `InterviewStore` method names temporarily, but the implementation now uses SQLAlchemy and writes `InterviewRecord` plus normalized question and turn records. This compatibility layer is not the STEP 2 repository layer.

The legacy `storage/interviews.db` SQLite file is no longer opened by the application runtime. It is retained for manual migration or archival handling.

## SQLAlchemy Configuration

`services/database.py` reads `DATABASE_URL` through application settings. PostgreSQL and explicit SQLite URLs are used directly. The default local database is `storage/ai_interviewer.db` for development and tests.

Sessions are created per operation with `SessionLocal()`. `SessionLocal.begin()` is used for atomic interview writes and rolls back when an exception escapes the context. No global shared session is used.

## PostgreSQL Configuration

Set `DATABASE_URL` to a PostgreSQL URL, for example:

```text
postgresql://user:password@localhost:5432/ai_interviewer
```

The project currently uses `psycopg2-binary`. PostgreSQL execution was not verified in this environment because Docker is unavailable; this remains an explicit verification item.

## Alembic Workflow

Schema changes are managed by Alembic. Application startup does not call `Base.metadata.create_all()`.

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic downgrade -1
python -m alembic upgrade head
```

The current head is `a4d2_resource_ownership`.

## Schema Overview

- `users`: authentication records.
- `candidates`: candidate records with optional recruiter owner and candidate account link.
- `interviews`: core interview record; `state_json` remains as a compatibility snapshot.
- `interview_questions`: normalized question history.
- `interview_turns`: normalized answer-turn records with unique interview/turn and interview/sequence indexes.
- `interview_evidence`: minimal future evidence storage.
- `interview_competency_state`: minimal future competency state storage.
- `rag_documents`: versioned, active/inactive retrieval chunks, scope metadata, and optional embedding vectors.
- `access_audit`: durable audit events for privileged admin resource access.

## Retrieval corpus and embeddings

The RAG MVP stores document chunks and embedding vectors in the configured SQLAlchemy database.
Vectors are JSON-serialized float arrays with model, version, and dimension columns; dense retrieval
uses exact cosine scoring after SQL metadata filtering. This is durable and works with the existing
SQLite development database and PostgreSQL without requiring an extension, but it scans matching
vectors in application code and is intended for the small demo corpus, not a large production index.
Job and optional organization identifiers are metadata filters. When a request has no job or
organization scope, rows bound to either scope are excluded; only explicitly global corpus rows can
be used. Supplying one scope still excludes rows bound to a different scope.
The application does not yet define organization authentication or authorization, so organization
IDs must only be supplied from a trusted server-side identity when that capability is added.
The configured backend name is `sqlalchemy_json`. The former `supabase` value is treated as a
deprecated alias and logs a warning; it does not mean that Supabase or pgvector is being used.

The checked-in demo corpus is synthetic and includes interview questions, competency descriptions,
rubrics, follow-up guidance, and general technical knowledge. To apply the schema and reproducibly
index it:

```powershell
python -m alembic upgrade head
python -m rag.ingest
python -m rag.run_evaluation
```

Set `EMBEDDING_PROVIDER=openai`, `OPENAI_API_KEY`, `EMBEDDING_MODEL` (default
`text-embedding-3-small`), and `EMBEDDING_DIMENSION` (default `1536`) to index real semantic
vectors. If credentials are absent, corpus text is still indexed for BM25 and retrieval results
explicitly report `semantic_embeddings_unconfigured_lexical_only`. An embedding timeout or invalid
vector also yields explicitly labeled lexical-only retrieval; it does not produce synthetic dense
scores. The benchmark reports Recall@5 and MRR@5 against
`rag/corpus/retrieval_eval_v1.json`; without credentials it measures only the lexical fallback and
does not claim semantic quality.

The normalized tables contain foreign keys for interview-to-question, interview-to-turn, evidence-to-interview, evidence-to-turn, and competency-state-to-interview relationships. Organizations and tenant tables are intentionally not present because the current application does not implement multi-tenancy.

## Live AI validation and release boundary

Live provider checks are opt-in and use synthetic answers only. Configure `LLM_PROVIDER=openai`,
`OPENAI_API_KEY`, `OPENAI_MODEL`, `EMBEDDING_PROVIDER=openai`, `EMBEDDING_MODEL`, and
`EMBEDDING_DIMENSION`. Then run:

```powershell
$env:RUN_LIVE_AI_TESTS = "1"
python -m pytest -q tests/unit/test_live_provider_smoke.py
python -m rag.run_evaluation
```

The complete live interview workflow additionally requires `RUN_LIVE_AI_E2E=1` and
`LIVE_AI_E2E_DATABASE_URL` pointing to a dedicated SQLite database file whose name contains
`live_ai_e2e_`. It applies Alembic migrations, idempotently ingests the synthetic corpus, bounds
individual provider calls to ten seconds, and has a five-minute total budget:

```powershell
$env:RUN_LIVE_AI_E2E = "1"
python -m pytest -q tests/integration/test_live_interview_e2e.py
```

These live commands must not be used with production or shared databases. Credentials are read
from environment variables or an untracked local `.env`; they must not be added to source control.

## Resource authorization and release boundary

The `a4d2_resource_ownership` migration adds nullable `candidates.owner_user_id` for the recruiter
who created/manages a candidate, nullable unique `candidates.user_id` for an explicitly
self-created candidate profile, and durable `access_audit` rows. Existing records are deliberately
left unassigned by the migration; they are not attributed to a recruiter based on email or other
inferred identity and remain accessible only to an explicit admin until an operator completes a
separate, controlled assignment process.

Candidate users can create and access only a profile linked to their authenticated user ID and
interviews belonging to that profile. Recruiters can access only candidate records they created
and interviews whose owner and candidate owner both match their authenticated user ID. Candidate
ownership, user links, and interview owners are server-controlled; request payloads reject unknown
ownership fields. Recruiters are read-only on interviews. Reports are generated only after the
same scoped interview authorization succeeds. HTTP and both WebSocket interview routes require
authentication and use the same interview authorization query. Unspecified user roles default to
`candidate`, including the database server default. Admin access is explicit and recorded in
`access_audit`; admin accounts must be provisioned through controlled operations, not public
registration.

This is per-recruiter isolation for a controlled single-tenant demo, not organization-level
multi-tenancy. There is no organization or membership model, no secure candidate-account linking
or recruiter assignment workflow for recruiter-created profiles, and RAG job/organization
metadata is not an API authorization boundary. Multi-tenant customer use remains a release
blocker. Legacy unassigned records require reviewed administrative assignment before a recruiter
can access them. Development/test startup may bootstrap the configured admin, but production
startup skips both development database initialization and admin bootstrap.

## Timestamps

Application timestamps use UTC-aware `datetime` values. Database columns use SQLAlchemy `DateTime(timezone=True)`. SQLite does not preserve timezone metadata in storage, so PostgreSQL verification is still required before making stronger cross-database claims.

## Legacy `state_json` Transition

`state_json` has not been deleted. New interview writes create normalized interview, question, and turn records and retain the JSON snapshot for compatibility with the current response shape and report exporter. The current compatibility layer still reads the snapshot to reconstruct fields not yet represented by the normalized schema.

The safe next transition is:

1. Add complete normalized fields needed by the application.
2. Verify normalized reads against existing snapshots.
3. Stop reading `state_json`.
4. Remove the column in a later migration.

No automatic migration of the 24 rows in the legacy `storage/interviews.db` file has been performed. That file was inspected and preserved.

## Local Development and Tests

Run migrations before starting the application:

```powershell
python -m alembic upgrade head
```

Integrity tests use an isolated in-memory SQLite database with foreign-key enforcement enabled. They do not use development data. The existing API tests use the configured local database and should be run against disposable development data.

## Migration Procedure

1. Back up the target database.
2. Set `DATABASE_URL` for the target environment.
3. Run `python -m alembic upgrade head`.
4. Confirm `python -m alembic current` reports the expected revision.
5. Run application and integrity tests.

## Rollback Procedure

For the tested local database, `python -m alembic downgrade -1` followed by `python -m alembic upgrade head` succeeds. Review the migration and take a backup before applying a downgrade to a database containing business data. The initial migration rollback drops the schema and must not be used as a data-preserving production rollback.

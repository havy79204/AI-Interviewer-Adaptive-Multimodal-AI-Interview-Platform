from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from config import settings
from rag.corpus_loader import load_demo_corpus
from rag.service import (
    DenseRetriever,
    DocumentChunk,
    EmbeddingProviderError,
    HybridRetriever,
    OpenAIEmbeddingProvider,
    RAGQuestionService,
    RetrievalFilters,
    RetrievalResult,
    SQLAlchemyVectorStore,
)
from services.database import RAGDocumentRecord


class FakeSemanticEmbedding:
    model = "fake-semantic"
    version = "fake-semantic-v1"
    dimension = 3

    def embed(self, text: str) -> list[float]:
        lowered = text.lower()
        if any(token in lowered for token in ("async", "external calls", "backpressure")):
            return [1.0, 0.0, 0.0]
        if any(token in lowered for token in ("cache", "stale", "invalidation")):
            return [0.0, 0.0, 1.0]
        return [0.0, 1.0, 0.0]


def _vector_store(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'rag-test.db'}")
    RAGDocumentRecord.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, factory, SQLAlchemyVectorStore(factory)


def test_sqlite_database_url_is_respected(monkeypatch, tmp_path):
    from services.database import _resolve_database_url

    database_url = f"sqlite:///{tmp_path / 'configured.db'}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)

    assert _resolve_database_url() == database_url


def test_openai_embedding_provider_uses_configured_model_dimension_and_validates(monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "test-embedding-model")
    monkeypatch.setattr(settings, "EMBEDDING_DIMENSION", 3)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    calls = []

    class FakeClient:
        class embeddings:
            @staticmethod
            def create(**kwargs):
                calls.append(kwargs)
                return SimpleNamespace(data=[SimpleNamespace(embedding=[1.0, 0.0, 0.0])])

    provider = OpenAIEmbeddingProvider(FakeClient())

    assert provider.embed("a semantic query") == [1.0, 0.0, 0.0]
    assert provider.model == "test-embedding-model"
    assert provider.dimension == 3
    assert calls == [{
        "model": "test-embedding-model",
        "input": "a semantic query",
        "dimensions": 3,
    }]


def test_embedding_provider_rejects_invalid_dimensions_and_provider_failures(monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "test-embedding-model")
    monkeypatch.setattr(settings, "EMBEDDING_DIMENSION", 3)

    class InvalidClient:
        class embeddings:
            @staticmethod
            def create(**kwargs):
                assert kwargs["input"]
                return SimpleNamespace(data=[SimpleNamespace(embedding=[1.0, 0.0])])

    with pytest.raises(EmbeddingProviderError, match="dimension mismatch"):
        OpenAIEmbeddingProvider(InvalidClient()).embed("query")

    class BrokenClient:
        class embeddings:
            @staticmethod
            def create(**kwargs):
                assert kwargs["input"]
                raise TimeoutError

    with pytest.raises(EmbeddingProviderError, match="TimeoutError"):
        OpenAIEmbeddingProvider(BrokenClient()).embed("query")


def test_provider_configuration_is_explicit_without_credentials(monkeypatch):
    from rag.service import configured_embedding_provider

    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    assert configured_embedding_provider() is None

    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "unknown-provider")
    with pytest.raises(EmbeddingProviderError, match="unsupported embedding provider"):
        configured_embedding_provider()


def test_durable_ingestion_reindex_and_dense_semantic_ranking(tmp_path):
    engine, factory, store = _vector_store(tmp_path)
    provider = FakeSemanticEmbedding()
    documents = [
        DocumentChunk(
            "python-async-knowledge",
            "chunk-1",
            "Async I/O uses an event loop and backpressure.",
            competency="python",
            source_type="technical_knowledge",
            job_id="ai_engineer",
            source="test-corpus",
        ),
        DocumentChunk(
            "database-transaction-knowledge",
            "chunk-1",
            "Database transactions use locks to coordinate writes.",
            competency="databases",
            source_type="technical_knowledge",
            job_id="software_engineer",
            source="test-corpus",
        ),
    ]

    assert store.upsert(documents, provider, replace_source=True) == 2
    assert store.upsert(documents, provider, replace_source=True) == 2

    with factory() as session:
        assert session.query(func.count(RAGDocumentRecord.id)).scalar() == 2

    reopened_store = SQLAlchemyVectorStore(factory)
    results = reopened_store.retrieve(
        "Keep a service available while many external calls are pending",
        RetrievalFilters(competency="python", job_id="ai_engineer"),
        2,
        provider,
    )
    assert results[0].chunk.document_id == "python-async-knowledge"
    assert results[0].dense_score == 1.0
    assert reopened_store.documents(
        RetrievalFilters(competency="python", job_id="software_engineer")
    ) == []
    engine.dispose()


def test_missing_or_stale_semantic_vectors_use_labeled_lexical_results(tmp_path):
    engine, _, store = _vector_store(tmp_path)
    documents = [
        DocumentChunk(
            "redis-cache",
            "chunk",
            "Redis cache invalidation prevents stale values.",
            competency="distributed_systems",
            job_id="software_engineer",
            source_type="technical_knowledge",
        )
    ]
    store.upsert(documents, None)
    retriever = HybridRetriever(
        dense=DenseRetriever(FakeSemanticEmbedding()),
        vector_store=store,
    )
    missing = retriever.retrieve(
        "Redis cache invalidation",
        RetrievalFilters(competency="distributed_systems", job_id="software_engineer"),
    )
    assert missing.chunks
    assert missing.dense_count == 0
    assert missing.fallback_reason == "no_matching_semantic_vectors"

    store.upsert(documents, FakeSemanticEmbedding())

    class NewEmbeddingVersion(FakeSemanticEmbedding):
        version = "fake-semantic-v2"

    stale = HybridRetriever(
        dense=DenseRetriever(NewEmbeddingVersion()),
        vector_store=store,
    ).retrieve(
        "Redis cache invalidation",
        RetrievalFilters(competency="distributed_systems", job_id="software_engineer"),
    )
    assert stale.chunks
    assert stale.dense_count == 0
    assert stale.fallback_reason == "no_matching_semantic_vectors"
    engine.dispose()


def test_metadata_filters_scope_job_competency_difficulty_and_active(tmp_path):
    engine, _, store = _vector_store(tmp_path)
    docs = [
        DocumentChunk(
            "target",
            "chunk",
            "Transaction locking, isolation, and retries.",
            competency="databases",
            job_id="software_engineer",
            difficulty="hard",
            source_type="evaluation_rubric",
            source="test-corpus",
            organization_id="org-a",
        ),
        DocumentChunk(
            "other-job",
            "chunk",
            "Transaction locking and retries.",
            competency="databases",
            job_id="ai_engineer",
            difficulty="hard",
            source_type="evaluation_rubric",
            source="test-corpus",
            organization_id="org-a",
        ),
        DocumentChunk(
            "other-organization",
            "chunk",
            "Transaction locking, isolation, and retries.",
            competency="databases",
            job_id="software_engineer",
            difficulty="hard",
            source_type="evaluation_rubric",
            source="test-corpus",
            organization_id="org-b",
        ),
        DocumentChunk(
            "inactive",
            "chunk",
            "Transaction isolation.",
            competency="databases",
            job_id="software_engineer",
            difficulty="hard",
            source_type="evaluation_rubric",
            source="test-corpus",
            active=False,
        ),
        DocumentChunk(
            "other-competency",
            "chunk",
            "Cache invalidation and consistency.",
            competency="distributed_systems",
            job_id="software_engineer",
            difficulty="hard",
            source_type="evaluation_rubric",
            source="test-corpus",
        ),
        DocumentChunk(
            "global",
            "chunk",
            "Database transactions and retries.",
            competency="databases",
            source_type="evaluation_rubric",
            source="test-corpus",
        ),
    ]
    store.upsert(docs, None)
    filtered = store.documents(
        RetrievalFilters(
            competency="databases",
            job_id="software_engineer",
            difficulty="hard",
            source_type="evaluation_rubric",
            organization_id="org-a",
        )
    )
    assert {document.document_id for document in filtered} == {"target", "global"}
    org_b = store.documents(
        RetrievalFilters(
            competency="databases",
            job_id="software_engineer",
            organization_id="org-b",
        )
    )
    assert {document.document_id for document in org_b} == {"other-organization", "global"}
    unscoped = store.documents(RetrievalFilters())
    assert [document.document_id for document in unscoped] == ["global"]
    engine.dispose()


def test_unscoped_retrieval_excludes_job_scoped_chunks():
    documents = [
        DocumentChunk(
            "ai-only",
            "chunk",
            "Redis cache invalidation prevents stale values.",
            job_id="ai_engineer",
        )
    ]

    result = HybridRetriever(documents).retrieve("Redis cache invalidation")

    assert result.chunks == []
    assert result.fallback_reason == "empty_filtered_corpus"


def test_provider_failure_keeps_lexical_results_and_labels_reduced_capability():
    class BrokenEmbedding:
        model = "broken"
        version = "broken-v1"
        dimension = 3

        def embed(self, text):
            assert text
            raise EmbeddingProviderError("provider unavailable")

    documents = [
        DocumentChunk("redis", "cache", "Redis cache invalidation handles stale values.")
    ]
    result = HybridRetriever(
        documents,
        dense=DenseRetriever(BrokenEmbedding()),
    ).retrieve("Redis cache invalidation")

    assert result.chunks
    assert result.dense_count == 0
    assert result.fallback_reason == "embedding_provider_failed:EmbeddingProviderError"


def test_empty_corpus_returns_no_results_and_chunk_ids_are_document_scoped():
    empty = HybridRetriever().retrieve("database transactions")
    assert empty.chunks == []
    assert empty.lexical_count == 0
    assert empty.fallback_reason == "empty_filtered_corpus"

    documents = [
        DocumentChunk("document-a", "shared-chunk", "Redis cache invalidation."),
        DocumentChunk("document-b", "shared-chunk", "Redis cache consistency."),
    ]
    result = HybridRetriever(documents).retrieve("Redis cache")
    assert len(result.chunks) == 2


def test_question_context_uses_answer_question_history_and_job_scope():
    class CapturingRetriever:
        def retrieve(self, query, filters=None, top_k=5):
            self.query = query
            self.filters = filters
            self.top_k = top_k
            return RetrievalResult(
                query,
                [],
                0,
                0,
                False,
                fallback_reason="semantic_embeddings_unconfigured_lexical_only",
            )

    retriever = CapturingRetriever()
    service = RAGQuestionService(retriever)
    result = service.retrieve_context(
        "AI Engineer",
        "python",
        ["cancellation"],
        question="How did you handle an async service failure?",
        answer_evidence=["I used bounded queues"],
        previous_questions=["Describe your event loop"],
        difficulty="hard",
    )

    assert "bounded queues" in retriever.query
    assert "async service failure" in retriever.query
    assert "Describe your event loop" in retriever.query
    assert retriever.filters.job_id == "ai_engineer"
    assert retriever.filters.competency == "python"
    assert retriever.top_k == settings.RETRIEVAL_TOP_K
    assert result.fallback_reason == "semantic_embeddings_unconfigured_lexical_only"
    assert "[LEXICAL_ONLY]" in service.format_context(result)


def test_demo_corpus_is_versioned_and_contains_requested_document_types():
    docs = load_demo_corpus()

    assert len(docs) >= 15
    assert {doc.source_type for doc in docs} >= {
        "interview_question",
        "competency_description",
        "evaluation_rubric",
        "technical_knowledge",
        "follow_up_guidance",
    }
    assert all(doc.document_id and doc.chunk_id and doc.version and doc.source for doc in docs)


def test_question_retrieval_reads_persisted_vectors_and_respects_job_scope(tmp_path):
    engine, _, store = _vector_store(tmp_path)
    provider = FakeSemanticEmbedding()
    documents = load_demo_corpus()
    store.upsert(documents, provider, replace_source=True)
    service = RAGQuestionService(
        HybridRetriever(
            dense=DenseRetriever(provider),
            vector_store=store,
        )
    )

    result = service.retrieve_context(
        "AI Engineer",
        "python",
        ["cancellation", "backpressure"],
        question="How did you prevent overload?",
        answer_evidence=["I used bounded queues"],
        previous_questions=["Describe the event loop"],
        difficulty="medium",
    )
    context = service.format_context(result)

    assert result.chunks
    assert all(item.chunk.competency == "python" for item in result.chunks)
    assert all(item.chunk.job_id == "ai_engineer" for item in result.chunks)
    assert "UNTRUSTED_CONTEXT" in context
    assert all(item.chunk.job_id != "software_engineer" for item in result.chunks)

    from services.interview_service import InterviewService

    interview_service = InterviewService.__new__(InterviewService)
    interview_service.rag = service
    graph_context = interview_service._retrieve_graph_context({
        "position": "AI Engineer",
        "current_competency": "python",
        "identified_gaps": ["cancellation", "backpressure"],
        "current_question": "How did you prevent overload?",
        "candidate_answer": "I used bounded queues",
        "asked_questions": ["Describe the event loop"],
        "difficulty": "medium",
    })
    assert "UNTRUSTED_CONTEXT" in graph_context
    assert "RETRIEVAL_CAPABILITY" not in graph_context
    engine.dispose()


@pytest.mark.live
@pytest.mark.skipif(
    not getattr(settings, "OPENAI_API_KEY", "") or settings.EMBEDDING_PROVIDER.lower() != "openai",
    reason="live embedding smoke test requires OPENAI_API_KEY and EMBEDDING_PROVIDER=openai",
)
def test_live_openai_embedding_smoke():
    provider = OpenAIEmbeddingProvider()
    vector = provider.embed("A short retrieval smoke-test query.")
    assert len(vector) == settings.EMBEDDING_DIMENSION

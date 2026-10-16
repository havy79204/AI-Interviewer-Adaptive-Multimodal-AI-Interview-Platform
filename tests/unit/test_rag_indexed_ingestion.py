import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rag import ingest
from rag.service import HybridRetriever, RetrievalFilters, SQLAlchemyVectorStore
from services.database import RAGDocumentRecord


SAMPLE_DOCUMENTS = {
    "cv": {
        "doc_id": "sample-candidate",
        "text": "Sample candidate has experience with Python async cancellation.",
        "query": "Python async cancellation",
        "expected_source": "indexed:cv/cv_sample.md",
    },
    "jd": {
        "doc_id": "sample-job",
        "text": "Required skills include Kubernetes container orchestration deployment.",
        "query": "Kubernetes container orchestration",
        "expected_source": "indexed:jd/jd_sample.md",
    },
    "company": {
        "doc_id": "sample-company",
        "text": "Company handbook covers engineering security policies and access controls.",
        "query": "engineering security policies",
        "expected_source": "indexed:company/company_sample.md",
    },
    "knowledge": {
        "doc_id": "sample-knowledge",
        "text": "Knowledge guide explains database transaction isolation and locking.",
        "query": "database transaction isolation",
        "expected_source": "indexed:knowledge/knowledge_sample.md",
    },
}


def _write_indexed_samples(root):
    for doc_type, sample in SAMPLE_DOCUMENTS.items():
        folder = root / doc_type
        folder.mkdir(parents=True)
        payload = {
            "doc_id": sample["doc_id"],
            "doc_type": doc_type,
            "source_file": f"{doc_type}_sample.md",
            "metadata": {"language": "en"},
            "chunks": [
                {
                    "chunk_id": f"{sample['doc_id']}#c001",
                    "doc_id": sample["doc_id"],
                    "doc_type": doc_type,
                    "start_line": 1,
                    "end_line": 1,
                    "heading_path": [],
                    "text": sample["text"],
                    "metadata": {
                        "topics": ["sample topic"],
                        "keywords": ["sample"],
                    },
                }
            ],
            "warnings": [],
        }
        (folder / f"{sample['doc_id']}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )


def _create_sample_retriever(tmp_path, monkeypatch):
    indexed_root = tmp_path / "indexed"
    _write_indexed_samples(indexed_root)

    engine = create_engine(f"sqlite:///{tmp_path / 'rag-indexed-test.db'}")
    RAGDocumentRecord.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    store = SQLAlchemyVectorStore(factory)
    monkeypatch.setattr(ingest, "SQLAlchemyVectorStore", lambda: store)
    monkeypatch.setattr(ingest, "configured_embedding_provider", lambda: None)

    count, indexed_vectors, capability = ingest.ingest_runtime_corpus(indexed_root)
    return engine, store, HybridRetriever(vector_store=store), count, indexed_vectors, capability


@pytest.fixture
def indexed_sample_retriever(tmp_path, monkeypatch):
    engine, _, retriever, *_ = _create_sample_retriever(tmp_path, monkeypatch)
    yield retriever
    engine.dispose()


def test_runtime_ingestion_indexes_four_document_types_and_retrieves_by_source(
    tmp_path, monkeypatch
):
    engine, store, retriever, count, indexed_vectors, capability = (
        _create_sample_retriever(tmp_path, monkeypatch)
    )

    assert count == len(ingest.load_demo_corpus()) + len(SAMPLE_DOCUMENTS)
    assert indexed_vectors == 0
    assert capability.startswith("lexical-only:")

    for doc_type, sample in SAMPLE_DOCUMENTS.items():
        result = retriever.retrieve(
            sample["query"],
            RetrievalFilters(source_type=doc_type),
            top_k=1,
        )

        assert len(result.chunks) == 1
        chunk = result.chunks[0].chunk
        assert chunk.document_id == f"{doc_type}:{sample['doc_id']}"
        assert chunk.source_type == doc_type
        assert chunk.source == sample["expected_source"]
        assert chunk.text == sample["text"]

    demo_results = retriever.retrieve(
        "Python service network requests responsive overload",
        RetrievalFilters(job_id="ai_engineer"),
        top_k=1,
    )
    assert demo_results.chunks
    assert demo_results.chunks[0].chunk.source == "synthetic-demo-corpus"
    engine.dispose()


@pytest.mark.parametrize("doc_type", SAMPLE_DOCUMENTS)
def test_sample_query_returns_expected_answer_and_source_without_cross_group_mix(
    indexed_sample_retriever, doc_type
):
    sample = SAMPLE_DOCUMENTS[doc_type]

    unfiltered = indexed_sample_retriever.retrieve(sample["query"], top_k=4)
    assert unfiltered.chunks
    best_match = unfiltered.chunks[0].chunk
    assert best_match.text == sample["text"]
    assert best_match.source_type == doc_type
    assert best_match.source == sample["expected_source"]

    source_filtered = indexed_sample_retriever.retrieve(
        sample["query"], RetrievalFilters(source_type=doc_type), top_k=4
    )
    assert source_filtered.chunks
    assert all(item.chunk.source_type == doc_type for item in source_filtered.chunks)
    assert any(item.chunk.text == sample["text"] for item in source_filtered.chunks)


def test_sample_query_without_a_matching_document_returns_no_chunks(
    indexed_sample_retriever,
):
    result = indexed_sample_retriever.retrieve(
        "quasar nucleosynthesis interstellar neutrino",
        top_k=4,
    )

    assert result.chunks == []
    assert result.lexical_count == 0


def test_lexical_only_ingestion_can_exclude_demo_corpus(tmp_path, monkeypatch):
    indexed_root = tmp_path / "indexed"
    for doc_type in ("cv", "jd"):
        sample = SAMPLE_DOCUMENTS[doc_type]
        folder = indexed_root / doc_type
        folder.mkdir(parents=True)
        payload = {
            "doc_id": sample["doc_id"],
            "doc_type": doc_type,
            "source_file": f"{doc_type}_sample.md",
            "metadata": {"language": "en"},
            "chunks": [
                {
                    "chunk_id": f"{sample['doc_id']}#c001",
                    "doc_id": sample["doc_id"],
                    "doc_type": doc_type,
                    "text": sample["text"],
                    "metadata": {"keywords": ["sample"], "topics": []},
                }
            ],
        }
        (folder / f"{sample['doc_id']}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    engine = create_engine(f"sqlite:///{tmp_path / 'rag-lexical-only.db'}")
    RAGDocumentRecord.__table__.create(engine)
    store = SQLAlchemyVectorStore(
        sessionmaker(bind=engine, expire_on_commit=False)
    )
    monkeypatch.setattr(ingest, "SQLAlchemyVectorStore", lambda: store)
    monkeypatch.setattr(
        ingest,
        "configured_embedding_provider",
        lambda: pytest.fail("lexical-only ingestion must not configure embeddings"),
    )

    count, indexed_vectors, capability = ingest.ingest_runtime_corpus(
        indexed_root,
        include_demo=False,
        lexical_only=True,
    )

    documents = store.documents(RetrievalFilters())
    assert count == 2
    assert indexed_vectors == 0
    assert capability == "lexical-only: embedding disabled by request"
    assert {document.source_type for document in documents} == {"cv", "jd"}
    assert all(document.source.startswith("indexed:") for document in documents)
    for doc_type in ("cv", "jd"):
        result = HybridRetriever(vector_store=store).retrieve(
            SAMPLE_DOCUMENTS[doc_type]["query"],
            RetrievalFilters(source_type=doc_type),
            top_k=2,
        )
        assert result.chunks
        assert all(item.chunk.source_type == doc_type for item in result.chunks)
    engine.dispose()

"""Upsert the demo corpus and indexed source-document chunks into runtime RAG."""

from __future__ import annotations

from pathlib import Path

from rag.corpus_loader import load_demo_corpus
from rag.indexed_corpus_loader import load_indexed_documents
from rag.service import DocumentChunk, SQLAlchemyVectorStore, configured_embedding_provider

INDEXED_DOCUMENTS_PATH = Path(__file__).resolve().parent / "documents" / "indexed"


def ingest_demo_corpus() -> tuple[int, int, str]:
    documents = load_demo_corpus()
    return _ingest_documents(documents)


def ingest_runtime_corpus(
    indexed_root: Path = INDEXED_DOCUMENTS_PATH,
    *,
    include_demo: bool = True,
    lexical_only: bool = False,
) -> tuple[int, int, str]:
    """Ingest indexed documents, optionally alongside demo data or without embeddings."""
    documents = load_demo_corpus() if include_demo else []
    documents.extend(load_indexed_documents(indexed_root))
    return _ingest_documents(documents, lexical_only=lexical_only)


def _ingest_documents(
    documents: list[DocumentChunk],
    *,
    lexical_only: bool = False,
) -> tuple[int, int, str]:
    provider = None if lexical_only else configured_embedding_provider()
    indexed_vectors = SQLAlchemyVectorStore().upsert(
        documents,
        provider,
        replace_source=True,
    )
    if lexical_only:
        capability = "lexical-only: embedding disabled by request"
    elif provider is None:
        capability = "lexical-only:embedding credentials unavailable"
    else:
        capability = "semantic"
    return len(documents), indexed_vectors, capability


if __name__ == "__main__":
    count, vectors, capability = ingest_runtime_corpus()
    print(f"upserted {count} chunks; {vectors} semantic vectors; retrieval capability={capability}")

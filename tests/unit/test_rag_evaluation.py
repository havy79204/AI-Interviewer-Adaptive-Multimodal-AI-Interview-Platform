from rag import run_evaluation
from rag.service import EmbeddingProviderError


class FakeEmbeddingProvider:
    model = "evaluation-fake"
    version = "evaluation-fake-v1"
    dimension = 2

    def embed(self, _text: str) -> list[float]:
        return [1.0, 0.0]


class BrokenEmbeddingProvider(FakeEmbeddingProvider):
    def embed(self, _text: str) -> list[float]:
        raise EmbeddingProviderError("provider unavailable")


def test_retrieval_benchmark_claims_semantic_only_when_dense_search_runs(monkeypatch):
    monkeypatch.setattr(
        run_evaluation, "configured_embedding_provider", lambda: FakeEmbeddingProvider()
    )

    report = run_evaluation.run()

    assert report["semantic_embeddings_enabled"] is True
    assert report["semantic_query_count"] > 0
    assert report["quality_claim"] == (
        "semantic hybrid retrieval measured; compare against the lexical baseline"
    )


def test_retrieval_benchmark_does_not_claim_semantics_after_provider_failures(monkeypatch):
    monkeypatch.setattr(
        run_evaluation, "configured_embedding_provider", lambda: BrokenEmbeddingProvider()
    )

    report = run_evaluation.run()

    assert report["embedding_model"] == "evaluation-fake"
    assert report["semantic_embeddings_enabled"] is False
    assert report["semantic_query_count"] == 0
    assert report["lexical_fallback_case_count"] == len(report["cases"])
    assert report["quality_claim"] == (
        "embedding provider is configured but dense retrieval did not run; "
        "lexical-only metrics measured"
    )
    assert all(case["hybrid"]["fallback_reason"] for case in report["cases"])

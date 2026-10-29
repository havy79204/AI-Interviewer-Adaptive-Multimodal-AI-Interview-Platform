from types import SimpleNamespace

import pytest
import torch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from rag.service import (
    EmbeddingProviderError,
    QwenLocalEmbeddingProvider,
    RetrievalFilters,
    SQLAlchemyVectorStore,
    DocumentChunk,
    configured_embedding_provider,
)
from services.database import RAGDocumentRecord


class FakeTokenizer:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def __call__(self, texts: list[str], **kwargs):
        self.texts.extend(texts)
        return {
            "input_ids": torch.tensor([[1, 2]]),
            "attention_mask": torch.tensor([[1, 1]]),
        }


class FakeModel:
    config = SimpleNamespace(hidden_size=3)

    def __init__(self, hidden_state: torch.Tensor | None = None) -> None:
        self.hidden_state = (
            hidden_state
            if hidden_state is not None
            else torch.tensor([[[1.0, 1.0, 1.0], [0.0, 3.0, 4.0]]])
        )

    def to(self, device: str):
        assert device == "cpu"
        return self

    def eval(self):
        return self

    def __call__(self, **kwargs):
        return SimpleNamespace(last_hidden_state=self.hidden_state)


def _provider(
    tokenizer: FakeTokenizer | None = None,
    model: FakeModel | None = None,
) -> tuple[QwenLocalEmbeddingProvider, FakeTokenizer]:
    selected_tokenizer = tokenizer or FakeTokenizer()
    return (
        QwenLocalEmbeddingProvider(
            tokenizer=selected_tokenizer,
            model=model or FakeModel(),
            revision="test-revision",
        ),
        selected_tokenizer,
    )


def test_qwen_provider_instruction_document_encoding_and_actual_dimension():
    provider, tokenizer = _provider()

    query_vector = provider.embed("Which cloud skills are listed?")
    document_vector = provider.embed_document("AWS and Kubernetes experience.")

    assert provider.dimension == 3
    assert len(query_vector) == provider.dimension
    assert query_vector == pytest.approx([0.0, 0.6, 0.8])
    assert document_vector == pytest.approx([0.0, 0.6, 0.8])
    assert sum(value * value for value in query_vector) == pytest.approx(1.0)
    assert tokenizer.texts[0].startswith("Instruct: ")
    assert "\nQuery:Which cloud skills are listed?" in tokenizer.texts[0]
    assert tokenizer.texts[1] == "AWS and Kubernetes experience."
    assert provider.version == (
        "Qwen/Qwen3-Embedding-0.6B@test-revision:"
        "last-token-query-instruction-v1:3"
    )


def test_qwen_provider_rejects_empty_text_wrong_dimensions_and_non_finite_values():
    provider, _ = _provider()

    with pytest.raises(EmbeddingProviderError, match="cannot embed empty text"):
        provider.embed("  ")

    wrong_dimension, _ = _provider(
        model=FakeModel(torch.tensor([[[1.0, 2.0], [3.0, 4.0]]]))
    )
    with pytest.raises(EmbeddingProviderError, match="output dimension"):
        wrong_dimension.embed("query")

    non_finite, _ = _provider(
        model=FakeModel(torch.tensor([[[1.0, 2.0, 3.0], [float("nan"), 0.0, 1.0]]]))
    )
    with pytest.raises(EmbeddingProviderError, match="non-finite"):
        non_finite.embed_document("document")


def test_qwen_provider_wraps_local_inference_errors_without_echoing_input():
    class BrokenTokenizer(FakeTokenizer):
        def __call__(self, texts: list[str], **kwargs):
            raise RuntimeError("internal tokenization failure")

    provider, _ = _provider(tokenizer=BrokenTokenizer())

    with pytest.raises(EmbeddingProviderError, match="local Qwen embedding failed: RuntimeError"):
        provider.embed("private CV text")


def test_qwen_provider_configuration_is_opt_in_and_never_falls_back_to_openai(
    monkeypatch,
):
    class ConfiguredLocalProvider:
        model = "Qwen/Qwen3-Embedding-0.6B"

    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "qwen_local")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(
        "rag.service.QwenLocalEmbeddingProvider",
        lambda: ConfiguredLocalProvider(),
    )
    monkeypatch.setattr(
        "rag.service.OpenAIEmbeddingProvider",
        lambda: pytest.fail("qwen_local configuration must not initialize OpenAI"),
    )

    provider = configured_embedding_provider()

    assert isinstance(provider, ConfiguredLocalProvider)


def test_vector_store_uses_document_encoding_and_records_qwen_identity(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'qwen-provider-test.db'}")
    RAGDocumentRecord.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    store = SQLAlchemyVectorStore(factory)
    provider, tokenizer = _provider()
    document = DocumentChunk(
        document_id="cv:selected-cv",
        chunk_id="selected_cv#c001",
        text="AWS and Kubernetes experience.",
        source_type="cv",
        source="indexed:cv/selected_cv.md",
    )

    assert store.upsert([document], provider) == 1
    assert tokenizer.texts == [document.text]

    retrieved = store.retrieve(
        "Which cloud skills are listed?",
        RetrievalFilters(source_type="cv"),
        1,
        provider,
    )
    assert len(retrieved) == 1
    assert retrieved[0].chunk.source_type == "cv"
    assert retrieved[0].chunk.source == "indexed:cv/selected_cv.md"
    assert tokenizer.texts[-1].startswith("Instruct: ")

    with factory() as session:
        row = session.query(RAGDocumentRecord).one()
        assert row.embedding_model == provider.model
        assert row.embedding_dimension == provider.dimension
        assert row.embedding_version == provider.version
    engine.dispose()

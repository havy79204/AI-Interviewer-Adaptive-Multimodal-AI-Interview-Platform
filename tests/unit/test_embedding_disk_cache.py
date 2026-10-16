from pathlib import Path

import json

from rag.service import DiskCachedEmbeddingProvider


class FakeEmbeddingProvider:
    model = "fake-embedding"
    version = "v1"
    dimension = 3

    def __init__(self):
        self.embed_calls = 0
        self.document_calls = 0

    def embed(self, text):
        self.embed_calls += 1
        return [1.0, 0.0, 0.0]

    def embed_document(self, text):
        self.document_calls += 1
        return [0.0, 1.0, 0.0]


def test_query_embedding_is_cached_on_disk(tmp_path):
    provider = FakeEmbeddingProvider()
    cache = DiskCachedEmbeddingProvider(provider, cache_dir=tmp_path)

    first = cache.embed("hello")
    second = cache.embed("hello")

    assert first == second
    assert provider.embed_calls == 1
    assert list(Path(tmp_path).glob("*.json"))


def test_document_embedding_is_cached_separately(tmp_path):
    provider = FakeEmbeddingProvider()
    cache = DiskCachedEmbeddingProvider(provider, cache_dir=tmp_path)

    first = cache.embed_document("hello")
    second = cache.embed_document("hello")

    assert first == second
    assert provider.document_calls == 1
    assert provider.embed_calls == 0


def test_cache_survives_provider_wrapper_recreation(tmp_path):
    provider = FakeEmbeddingProvider()
    first_cache = DiskCachedEmbeddingProvider(provider, cache_dir=tmp_path)
    first = first_cache.embed("hello")

    second_provider = FakeEmbeddingProvider()
    second_cache = DiskCachedEmbeddingProvider(
        second_provider, cache_dir=tmp_path
    )
    second = second_cache.embed("hello")

    assert second == first
    assert second_provider.embed_calls == 0


def test_corrupt_cache_is_recomputed(tmp_path):
    provider = FakeEmbeddingProvider()
    cache = DiskCachedEmbeddingProvider(provider, cache_dir=tmp_path)

    cache.embed("hello")

    for cache_file in Path(tmp_path).glob("*.json"):
        cache_file.write_text("{invalid json", encoding="utf-8")

    result = cache.embed("hello")

    assert result == [1.0, 0.0, 0.0]
    assert provider.embed_calls == 2

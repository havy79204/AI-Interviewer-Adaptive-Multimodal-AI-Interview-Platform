"""Adapt indexed-document JSON files to the runtime RAG chunk schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rag.service import DocumentChunk

INDEXED_DOCUMENT_TYPES = ("cv", "jd", "company", "knowledge")
INDEXED_DOCUMENT_VERSION = "indexed-v1"


def load_indexed_documents(root: Path) -> list[DocumentChunk]:
    """Load indexer JSON outputs from `<root>/<document_type>/*.json`."""
    indexed_root = Path(root)
    if not indexed_root.is_dir():
        raise FileNotFoundError(f"indexed documents directory does not exist: {indexed_root}")

    documents: list[DocumentChunk] = []
    seen: set[tuple[str, str, str]] = set()
    for doc_type in INDEXED_DOCUMENT_TYPES:
        for path in sorted((indexed_root / doc_type).glob("*.json")):
            payload = _read_indexed_document(path, doc_type)
            document_id = f"{doc_type}:{payload['doc_id']}"
            version = payload.get("version", INDEXED_DOCUMENT_VERSION)
            if not isinstance(version, str) or not version.strip():
                raise ValueError(f"invalid version in indexed document: {path}")
            source_file = payload.get("source_file", path.name)
            if not isinstance(source_file, str) or not source_file.strip():
                raise ValueError(f"invalid source_file in indexed document: {path}")
            source_name = Path(source_file.replace("\\", "/")).name
            if not source_name:
                raise ValueError(f"invalid source_file in indexed document: {path}")
            source = f"indexed:{doc_type}/{source_name}"
            document_metadata = payload.get("metadata", {})

            for chunk in payload["chunks"]:
                if not isinstance(chunk, dict):
                    raise ValueError(f"chunk entries must be objects in indexed document: {path}")
                chunk_id = _required_string(chunk, "chunk_id", path)
                text = _required_string(chunk, "text", path)
                if chunk.get("doc_type", doc_type) != doc_type:
                    raise ValueError(f"chunk document type does not match folder in: {path}")
                if chunk.get("doc_id", payload["doc_id"]) != payload["doc_id"]:
                    raise ValueError(f"chunk document id does not match parent document in: {path}")
                identity = (document_id, chunk_id, version)
                if identity in seen:
                    raise ValueError(f"duplicate indexed chunk identity: {identity}")
                seen.add(identity)

                chunk_metadata = chunk.get("metadata", {})
                tags = _metadata_tags(chunk_metadata, path)
                language = chunk_metadata.get("language") or document_metadata.get("language") or "vi"
                if not isinstance(language, str) or not language.strip():
                    raise ValueError(f"invalid language metadata in indexed document: {path}")

                documents.append(
                    DocumentChunk(
                        document_id=document_id,
                        chunk_id=chunk_id,
                        text=text,
                        source_type=doc_type,
                        version=version,
                        language=language,
                        tags=tuple(tags),
                        source=source,
                    )
                )
    return documents


def _read_indexed_document(path: Path, expected_type: str) -> dict[str, Any]:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read indexed document {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"indexed document must be a JSON object: {path}")
    doc_id = _required_string(payload, "doc_id", path)
    doc_type = _required_string(payload, "doc_type", path)
    if doc_type != expected_type:
        raise ValueError(f"indexed document type does not match folder in: {path}")
    chunks = payload.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError(f"indexed document must contain at least one chunk: {path}")
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError(f"document metadata must be an object in: {path}")
    return {**payload, "doc_id": doc_id, "doc_type": doc_type, "metadata": metadata}


def _required_string(payload: dict[str, Any], field: str, path: Path) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"indexed document field '{field}' must be a non-empty string: {path}")
    return value


def _metadata_tags(metadata: Any, path: Path) -> list[str]:
    if not isinstance(metadata, dict):
        raise ValueError(f"chunk metadata must be an object in indexed document: {path}")
    tags: list[str] = []
    for field in ("topics", "keywords"):
        values = metadata.get(field, [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"chunk metadata '{field}' must be a list of strings: {path}")
        tags.extend(value for value in values if value.strip())
    return list(dict.fromkeys(tags))

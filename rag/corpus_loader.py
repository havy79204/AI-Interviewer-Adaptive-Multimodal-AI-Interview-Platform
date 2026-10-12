"""Load and validate the versioned, synthetic interview retrieval corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings
from rag.service import DocumentChunk

DEMO_CORPUS_PATH = Path(__file__).resolve().parent / "corpus" / "demo_v1.json"


def load_demo_corpus(path: Path = DEMO_CORPUS_PATH) -> list[DocumentChunk]:
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    version = payload.get("version") if isinstance(payload, dict) else None
    if version != settings.RAG_DEMO_CORPUS_VERSION:
        raise ValueError(
            f"demo corpus version mismatch: configured {settings.RAG_DEMO_CORPUS_VERSION}, found {version}"
        )
    rows = payload.get("documents")
    if not isinstance(rows, list) or not rows:
        raise ValueError("demo corpus must contain at least one document chunk")
    documents: list[DocumentChunk] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        document = _document_from_row(row, version)
        identity = (document.document_id, document.chunk_id, document.version)
        if identity in seen:
            raise ValueError(f"duplicate demo corpus chunk identity: {identity}")
        seen.add(identity)
        documents.append(document)
    return documents


def _document_from_row(row: Any, version: str) -> DocumentChunk:
    if not isinstance(row, dict):
        raise ValueError("demo corpus entries must be objects")
    required = ("document_id", "chunk_id", "text", "document_type", "source")
    if any(not isinstance(row.get(field), str) or not row[field].strip() for field in required):
        raise ValueError("demo corpus entry is missing a required string field")
    if not isinstance(row.get("active"), bool):
        raise ValueError(f"active must be boolean for corpus chunk {row['document_id']}:{row['chunk_id']}")
    difficulty = row.get("difficulty")
    if difficulty not in (None, "easy", "medium", "hard"):
        raise ValueError(f"invalid difficulty for corpus chunk {row['document_id']}:{row['chunk_id']}")
    for optional_field in ("competency_id", "job_id", "organization_id"):
        value = row.get(optional_field)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{optional_field} must be a string or null")
    tags = row.get("tags", [])
    if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
        raise ValueError(f"tags must be a list of strings for corpus chunk {row['document_id']}:{row['chunk_id']}")
    job_id = row.get("job_id")
    return DocumentChunk(
        document_id=row["document_id"],
        chunk_id=row["chunk_id"],
        text=row["text"],
        competency=row.get("competency_id"),
        job_id=job_id,
        organization_id=row.get("organization_id"),
        job_role=job_id,
        source_type=row["document_type"],
        version=version,
        language=row.get("language", "en"),
        tags=tuple(tags),
        difficulty=difficulty,
        source=row["source"],
        active=row["active"],
    )

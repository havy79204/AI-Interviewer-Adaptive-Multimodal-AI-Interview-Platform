import json
import math
import time

from rag.service import configured_embedding_provider
from services.database import SessionLocal, RAGDocumentRecord


def main():
    provider = configured_embedding_provider()
    started = time.time()

    with SessionLocal() as session:
        ids = [
            row.id
            for row in session.query(RAGDocumentRecord.id)
            .filter(
                RAGDocumentRecord.active.is_(True),
                RAGDocumentRecord.embedding_json.is_(None),
            )
            .all()
        ]

    total = len(ids)
    print(f"Found {total} active records missing embeddings", flush=True)

    for index, record_id in enumerate(ids, start=1):
        with SessionLocal.begin() as session:
            row = session.query(RAGDocumentRecord).filter(
                RAGDocumentRecord.id == record_id,
                RAGDocumentRecord.active.is_(True),
                RAGDocumentRecord.embedding_json.is_(None),
            ).one_or_none()

            if row is None:
                continue

            vector = provider.embed_document(row.text)

            if len(vector) != provider.dimension:
                raise ValueError(f"Invalid vector dimension for record {record_id}")

            if not all(math.isfinite(float(value)) for value in vector):
                raise ValueError(f"Invalid vector values for record {record_id}")

            row.embedding_json = json.dumps(vector, separators=(",", ":"))
            row.embedding_model = provider.model
            row.embedding_dimension = provider.dimension
            row.embedding_version = provider.version

        elapsed = time.time() - started
        print(
            f"Progress: {index}/{total} | elapsed: {elapsed:.1f}s",
            flush=True,
        )

    print(f"Finished in {time.time() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()

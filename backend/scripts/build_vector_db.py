from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = REPO_ROOT / "data" / "processed" / "jobs_computer_with_text_v2.json"
DEFAULT_QDRANT_PATH = REPO_ROOT / "data" / "vector" / "qdrant"
DEFAULT_EXPORT_PATH = REPO_ROOT / "data" / "processed" / "jobs_computer_with_embeddings.json"
DEFAULT_COLLECTION = "jobs_computer"
DEFAULT_EMBED_DIM = 256

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_+#./-]+|[\u4e00-\u9fff]")
HEX_32_PATTERN = re.compile(r"^[0-9a-fA-F]{32,}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build local Qdrant vector DB from jobs_computer_with_text_v2.json and export embeddings JSON."
   
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Input JSON path")
    parser.add_argument("--qdrant-path", default=str(DEFAULT_QDRANT_PATH), help="Local Qdrant storage directory")
    parser.add_argument("--export", default=str(DEFAULT_EXPORT_PATH), help="Export JSON with embeddings")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="Qdrant collection name")
    parser.add_argument("--dim", type=int, default=DEFAULT_EMBED_DIM, help="Embedding dimension")
    parser.add_argument("--batch-size", type=int, default=256, help="Upsert batch size")
    return parser.parse_args()


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return TOKEN_PATTERN.findall(text.lower())


def _normalize_vector(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in values))
    if norm <= 1e-12:
        return values
    return [v / norm for v in values]


def generate_hash_embedding(text: str, dim: int) -> list[float]:
    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * dim

    vector = [0.0] * dim
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        idx = int.from_bytes(digest[:8], "big") % dim
        sign = 1.0 if (digest[8] & 1) == 0 else -1.0
        weight = 1.0 + ((digest[9] % 5) * 0.1)
        vector[idx] += sign * weight
    return _normalize_vector(vector)


def canonical_key_to_qdrant_id(canonical_key: str) -> str:
    key = (canonical_key or "").strip()
    try:
        return str(uuid.UUID(key))
    except Exception:
        pass

    if HEX_32_PATTERN.match(key):
        hex32 = key[:32].lower()
        uuid_text = f"{hex32[0:8]}-{hex32[8:12]}-{hex32[12:16]}-{hex32[16:20]}-{hex32[20:32]}"
        try:
            return str(uuid.UUID(uuid_text))
        except Exception:
            pass

    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"career_planning:{key}"))


def build_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["id"] = record.get("canonical_key")
    return payload


def export_record(record: dict[str, Any], embedding: list[float]) -> dict[str, Any]:
    return {
        "canonical_key": record.get("canonical_key"),
        "position_name": record.get("position_name"),
        "position_name_normalized": record.get("position_name_normalized"),
        "job_category": record.get("job_category"),
        "industry": record.get("industry"),
        "work_city": record.get("work_city"),
        "salary_range": record.get("salary_range"),
        "job_tags": record.get("job_tags"),
        "embedding_text": record.get("embedding_text"),
        "embedding": embedding,
    }


def load_records(input_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw = input_path.read_text(encoding="utf-8-sig")
    payload = json.loads(raw)
    records = payload.get("records", [])
    if not isinstance(records, list):
        raise ValueError("Input JSON field 'records' must be a list")
    typed_records = [item for item in records if isinstance(item, dict)]
    return payload, typed_records


def build_vector_db(
    input_path: Path,
    qdrant_path: Path,
    export_path: Path,
    collection_name: str,
    dim: int,
    batch_size: int,
) -> dict[str, Any]:
    payload, records = load_records(input_path)

    qdrant_path.mkdir(parents=True, exist_ok=True)
    export_path.parent.mkdir(parents=True, exist_ok=True)

    client = QdrantClient(path=str(qdrant_path))
    try:
        if client.collection_exists(collection_name):
            client.delete_collection(collection_name=collection_name)
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

        points_batch: list[PointStruct] = []
        exported_records: list[dict[str, Any]] = []

        for record in records:
            canonical_key = str(record.get("canonical_key") or "")
            embedding_text = str(record.get("embedding_text") or "")
            embedding = generate_hash_embedding(embedding_text, dim=dim)
            qdrant_id = canonical_key_to_qdrant_id(canonical_key)

            point = PointStruct(
                id=qdrant_id,
                vector=embedding,
                payload=build_payload(record),
            )
            points_batch.append(point)
            exported_records.append(export_record(record, embedding))

            if len(points_batch) >= batch_size:
                client.upsert(collection_name=collection_name, points=points_batch, wait=True)
                points_batch.clear()

        if points_batch:
            client.upsert(collection_name=collection_name, points=points_batch, wait=True)

        export_payload = {
            "source_file": str(input_path),
            "source_batch_id": payload.get("batch_id"),
            "source_batch_name": payload.get("batch_name"),
            "collection": collection_name,
            "embedding_model": f"hash_bow_{dim}d_v1",
            "record_count": len(exported_records),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "records": exported_records,
        }
        export_path.write_text(json.dumps(export_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "input_file": str(input_path),
            "qdrant_path": str(qdrant_path),
            "collection": collection_name,
            "export_file": str(export_path),
            "record_count": len(exported_records),
            "embedding_dim": dim,
        }
    finally:
        client.close()


def main() -> None:
    args = parse_args()
    summary = build_vector_db(
        input_path=Path(args.input).resolve(),
        qdrant_path=Path(args.qdrant_path).resolve(),
        export_path=Path(args.export).resolve(),
        collection_name=args.collection,
        dim=args.dim,
        batch_size=args.batch_size,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

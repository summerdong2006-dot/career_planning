from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.db.session import SessionLocal
from app.services.job_graph import build_job_graph, generate_career_paths

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = REPO_ROOT / "data" / "processed" / "jobs_master.json"


def load_job_ids(limit: int = 50) -> list[int]:
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    records = payload.get("records", [])[:limit]
    job_ids = [int(r["source_row_number"]) for r in records if r.get("source_row_number") is not None]
    return job_ids


async def main() -> None:
    job_ids = load_job_ids(50)
    print(f"Loaded source_clean_ids: {len(job_ids)}")
    print(f"First 10 ids: {job_ids[:10]}")

    async with SessionLocal() as session:
        print("\n===== Building Graph =====")
        graph = await build_job_graph(session, job_ids=job_ids)

        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        print(f"Graph nodes: {len(nodes)}")
        print(f"Graph edges: {len(edges)}")

        promotion_edges = [e for e in edges if e.get("type") == "promotion"]
        transition_edges = [e for e in edges if e.get("type") == "transition"]

        print(f"Promotion edges: {len(promotion_edges)}")
        print(f"Transition edges: {len(transition_edges)}")

        print("\n===== Career Path Samples =====")
        for job_id in job_ids[:5]:
            try:
                paths = await generate_career_paths(session, job_id=job_id)
                print(f"\njob_id={job_id}")
                print(paths)
            except Exception as e:
                print(f"\njob_id={job_id} 璺緞鐢熸垚澶辫触: {e}")


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.job_graph import build_job_graph, generate_career_paths

OUTPUT_DIR = Path(r"E:\Codex\backend\output\card6_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def main():
    async with SessionLocal() as session:

        # ⭐ 从数据库取真实 job_id
        result = await session.execute(
            text("SELECT id FROM job_posting_profiles ORDER BY id LIMIT 50")
        )
        job_ids = [row[0] for row in result.fetchall()]

        print("===== REAL JOB IDS =====")
        print(job_ids[:10], "... total =", len(job_ids))

        print("\n===== Building Graph =====")
        graph = await build_job_graph(session, job_ids=job_ids)

        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        stats = {
            "nodes": len(nodes),
            "edges": len(edges),
            "promotion_edges": sum(1 for e in edges if e.get("type") == "promotion"),
            "transition_edges": sum(1 for e in edges if e.get("type") == "transition"),
        }

        print(stats)

        # 保存图谱统计
        (OUTPUT_DIR / "card6_stats_first50.json").write_text(
            json.dumps(stats, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print("\n===== Generating Paths =====")

        results = []

        for job_id in job_ids[:5]:  # ⭐ 用真实ID
            try:
                paths = await generate_career_paths(session, job_id=job_id)

                results.append({
                    "job_id": job_id,
                    "paths": paths
                })

                print(f"\njob_id={job_id}")
                print(paths)

            except Exception as e:
                print(f"\njob_id={job_id} failed: {e}")

        # 保存路径样例
        (OUTPUT_DIR / "card6_paths_first50.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )


if __name__ == "__main__":
    asyncio.run(main())
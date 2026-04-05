from __future__ import annotations

import argparse
import asyncio
import json

from app.db.session import build_session_factory
from app.modules.matching.schema import MatchingWeights
from app.modules.matching.service import recommend_jobs_for_student, recommend_jobs_for_students_batch


async def _run(args: argparse.Namespace) -> None:
    session_factory = build_session_factory(args.database_url)
    async with session_factory() as session:
        weights = MatchingWeights()
        if args.command == "recommend":
            result = await recommend_jobs_for_student(
                session=session,
                student_profile_id=args.student_profile_id,
                top_k=args.top_k,
                weights=weights,
                persist=not args.no_persist,
            )
        else:
            result = await recommend_jobs_for_students_batch(
                session=session,
                student_profile_ids=args.student_profile_ids,
                top_k=args.top_k,
                weights=weights,
                persist=not args.no_persist,
            )
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Matching module CLI")
    parser.add_argument("--database-url", default=None, help="Optional database URL. Defaults to configured async URL.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    recommend_parser = subparsers.add_parser("recommend", help="Recommend jobs for one student profile")
    recommend_parser.add_argument("--student-profile-id", type=int, required=True)
    recommend_parser.add_argument("--top-k", type=int, default=5)
    recommend_parser.add_argument("--no-persist", action="store_true")

    batch_parser = subparsers.add_parser("recommend-batch", help="Recommend jobs for multiple student profiles")
    batch_parser.add_argument("--student-profile-ids", type=int, nargs="+", required=True)
    batch_parser.add_argument("--top-k", type=int, default=5)
    batch_parser.add_argument("--no-persist", action="store_true")
    return parser



def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()


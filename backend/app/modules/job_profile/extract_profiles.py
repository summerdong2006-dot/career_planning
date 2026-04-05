from __future__ import annotations

import argparse
import asyncio
import json

from app.db.session import build_session_factory
from app.modules.job_profile.profile_service import extract_job_profiles_batch, extract_single_job_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract structured job profiles from cleaned job data.")
    parser.add_argument("--source-clean-id", type=int, default=None, help="Extract a single clean job record by ID.")
    parser.add_argument("--batch-id", type=int, default=None, help="Extract a limited batch by import batch ID.")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of records to extract in batch mode. Default and recommended limit is 50.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional database URL. Defaults to configured PostgreSQL async URL.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Do not write extracted profiles back to the database.",
    )
    return parser


def _print_json(payload: object) -> None:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


async def _run() -> None:
    args = build_parser().parse_args()
    session_factory = build_session_factory(args.database_url)
    async with session_factory() as session:
        if args.source_clean_id is not None:
            result = await extract_single_job_profile(
                session=session,
                source_clean_id=args.source_clean_id,
                persist=not args.no_persist,
            )
            _print_json(result)
            return

        if args.batch_id is not None:
            result = await extract_job_profiles_batch(
                session=session,
                batch_id=args.batch_id,
                limit=args.limit,
                persist=not args.no_persist,
            )
            _print_json(result)
            return

        raise SystemExit("Either --source-clean-id or --batch-id must be provided")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()

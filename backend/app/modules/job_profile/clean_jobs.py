from __future__ import annotations

import argparse
import asyncio
import json

from app.modules.job_profile.service import clean_job_records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean, deduplicate and export imported job postings.")
    parser.add_argument("--batch-id", required=True, type=int, help="Imported batch id returned by import_jobs.")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional database URL. Defaults to configured PostgreSQL async URL.",
    )
    parser.add_argument(
        "--export-path",
        default=None,
        help="Optional path for standardized job data JSON export.",
    )
    parser.add_argument(
        "--log-path",
        default=None,
        help="Optional path for cleaning log JSON export.",
    )
    return parser


async def _run() -> None:
    args = build_parser().parse_args()
    summary = await clean_job_records(
        batch_id=args.batch_id,
        database_url=args.database_url,
        export_path=args.export_path,
        log_path=args.log_path,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()

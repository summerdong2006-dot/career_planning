from __future__ import annotations

import argparse
import asyncio
import json

from app.modules.job_profile.data_loader import DEFAULT_RAW_DATA_DIR, resolve_input_path
from app.modules.job_profile.service import import_job_records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import raw job postings from the official source table into the database.")
    parser.add_argument(
        "--input",
        default=None,
        help="Optional path to a CSV/XLS/XLSX job data file. If omitted, the latest supported file under data/raw/official is used.",
    )
    parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_RAW_DATA_DIR),
        help="Official raw data directory used when --input is omitted.",
    )
    parser.add_argument("--batch-name", default=None, help="Optional business batch name.")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional database URL. Defaults to configured PostgreSQL async URL.",
    )
    return parser


async def _run() -> None:
    args = build_parser().parse_args()
    input_path = resolve_input_path(args.input, args.raw_dir)
    summary = await import_job_records(
        input_path=str(input_path),
        batch_name=args.batch_name,
        database_url=args.database_url,
    )
    summary["resolved_input"] = str(input_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()


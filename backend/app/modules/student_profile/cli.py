from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.db.session import build_session_factory
from app.modules.student_profile.schema import ScoringWeights, StudentProfileSource
from app.modules.student_profile.service import (
    batch_build_student_profiles,
    build_student_profile,
    export_student_profile,
    rebuild_student_profile,
)



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and manage structured student profiles.")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional database URL. Defaults to configured PostgreSQL async URL.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("single", help="Build a single student profile.")
    single.add_argument("--student-id", required=True)
    single.add_argument("--resume-file", default=None)
    single.add_argument("--manual-json", default=None)
    single.add_argument("--supplement-file", default=None)
    single.add_argument("--basic-info-json", default=None)
    single.add_argument("--no-persist", action="store_true")

    batch = subparsers.add_parser("batch", help="Build student profiles from a JSON array file.")
    batch.add_argument("--input", required=True)
    batch.add_argument("--no-persist", action="store_true")

    rebuild = subparsers.add_parser("rebuild", help="Rebuild the latest or target version for a student.")
    rebuild.add_argument("--student-id", required=True)
    rebuild.add_argument("--version", type=int, default=None)
    rebuild.add_argument("--no-persist", action="store_true")

    export = subparsers.add_parser("export", help="Export a stored student profile as JSON.")
    export.add_argument("--student-id", required=True)
    export.add_argument("--version", type=int, default=None)
    export.add_argument("--output", default=None)

    return parser



def _read_text(path: str | None) -> str:
    if not path:
        return "未明确"
    return Path(path).read_text(encoding="utf-8")



def _read_json(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))



def _print_json(payload: object, output: str | None = None) -> None:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(data, encoding="utf-8")
        return
    print(data)


async def _run() -> None:
    args = build_parser().parse_args()
    session_factory = build_session_factory(args.database_url)
    async with session_factory() as session:
        if args.command == "single":
            result = await build_student_profile(
                session=session,
                source=StudentProfileSource(
                    student_id=args.student_id,
                    resume_text=_read_text(args.resume_file),
                    manual_form=_read_json(args.manual_json),
                    supplement_text=_read_text(args.supplement_file),
                    basic_info=_read_json(args.basic_info_json),
                    resume_filename=Path(args.resume_file).name if args.resume_file else "未明确",
                ),
                persist=not args.no_persist,
                scoring_weights=ScoringWeights(),
            )
            _print_json(result)
            return

        if args.command == "batch":
            payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
            items = [StudentProfileSource.model_validate(item) for item in payload]
            result = await batch_build_student_profiles(
                session=session,
                items=items,
                persist=not args.no_persist,
                scoring_weights=ScoringWeights(),
            )
            _print_json(result)
            return

        if args.command == "rebuild":
            result = await rebuild_student_profile(
                session=session,
                student_id=args.student_id,
                version=args.version,
                persist=not args.no_persist,
            )
            _print_json(result)
            return

        if args.command == "export":
            result = await export_student_profile(
                session=session,
                student_id=args.student_id,
                version=args.version,
            )
            _print_json(result, output=args.output)
            return



def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()

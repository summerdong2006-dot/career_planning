from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from app.modules.job_profile.evaluation import evaluate_profiles
from app.modules.job_profile.profile_schema import JobProfileSourceRecord
from app.modules.job_profile.profile_service import extract_job_profile_from_source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate job profile extraction against gold annotations.")
    parser.add_argument("--gold-file", required=True, help="Path to a gold JSON file, for example ../data/seeds/job_profile_gold_sample.json.")
    parser.add_argument(
        "--predictions-file",
        default=None,
        help="Optional path to prediction JSON. If omitted, predictions are generated from gold.job_data on the fly.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5,
        help="Number of sample cases to keep in the evaluation output.",
    )
    return parser


async def _generate_predictions_from_gold(gold_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    predictions: list[dict[str, Any]] = []
    for item in gold_items:
        source = JobProfileSourceRecord.model_validate(item["job_data"])
        profile, raw_payload, extractor_name = await extract_job_profile_from_source(source)
        predictions.append(
            {
                "case_id": item.get("case_id") or item.get("source_clean_id"),
                "source_clean_id": item.get("source_clean_id"),
                "extractor_name": extractor_name,
                "profile": profile.model_dump(),
                "raw_profile_payload": raw_payload,
            }
        )
    return predictions


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


async def _run() -> None:
    args = build_parser().parse_args()
    gold_payload = _load_json(args.gold_file)
    gold_items = gold_payload["items"] if isinstance(gold_payload, dict) else gold_payload

    if args.predictions_file:
        prediction_payload = _load_json(args.predictions_file)
        predicted_items = prediction_payload.get("items", prediction_payload)
    else:
        predicted_items = await _generate_predictions_from_gold(gold_items)

    report = evaluate_profiles(gold_items, predicted_items)
    report["samples"] = report["samples"][: max(args.sample_size, 0)]
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()


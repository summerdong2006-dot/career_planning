from __future__ import annotations

from typing import Any, Mapping

from app.modules.job_profile.profile_schema import JobProfilePayload

COMPARABLE_FIELDS = [
    "job_title",
    "job_level",
    "education_requirement",
    "years_experience_requirement",
    "must_have_skills",
    "nice_to_have_skills",
    "certificates",
    "soft_skills",
    "internship_requirement",
    "industry_tags",
    "promotion_path",
    "summary",
]


def _normalize_text(value: Any) -> str:
    return "".join(str(value).lower().split()) if value is not None else ""


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    normalized = []
    for item in value:
        token = _normalize_text(item)
        if token and token not in normalized:
            normalized.append(token)
    return normalized


def _field_hit(expected: Any, predicted: Any) -> bool:
    if isinstance(expected, list):
        expected_set = set(_normalize_list(expected))
        predicted_set = set(_normalize_list(predicted))
        if not expected_set:
            return False
        return bool(expected_set & predicted_set)
    expected_text = _normalize_text(expected)
    predicted_text = _normalize_text(predicted)
    if not expected_text:
        return False
    return expected_text == predicted_text or expected_text in predicted_text or predicted_text in expected_text


def _field_exact_match(expected: Any, predicted: Any) -> bool:
    if isinstance(expected, list):
        return set(_normalize_list(expected)) == set(_normalize_list(predicted))
    return _normalize_text(expected) == _normalize_text(predicted)


def evaluate_profiles(gold_items: list[Mapping[str, Any]], predicted_items: list[Mapping[str, Any]]) -> dict[str, Any]:
    predicted_by_key: dict[str, JobProfilePayload] = {}
    for item in predicted_items:
        key = str(item.get("case_id") or item.get("source_clean_id") or item.get("id") or "")
        profile = item.get("profile", item)
        if key:
            predicted_by_key[key] = JobProfilePayload.model_validate(profile)

    per_field: dict[str, dict[str, Any]] = {
        field_name: {"gold_populated": 0, "predicted_populated": 0, "hit": 0, "exact_match": 0}
        for field_name in COMPARABLE_FIELDS
    }
    sample_results: list[dict[str, Any]] = []
    fully_correct = 0

    for gold_item in gold_items:
        key = str(gold_item.get("case_id") or gold_item.get("source_clean_id") or gold_item.get("id") or "")
        expected = JobProfilePayload.model_validate(gold_item["expected"])
        predicted = predicted_by_key.get(key, JobProfilePayload())
        record_ok = True
        field_details: dict[str, Any] = {}

        for field_name in COMPARABLE_FIELDS:
            expected_value = getattr(expected, field_name)
            predicted_value = getattr(predicted, field_name)
            expected_populated = bool(expected_value and expected_value != "未明确")
            predicted_populated = bool(predicted_value and predicted_value != "未明确")
            if expected_populated:
                per_field[field_name]["gold_populated"] += 1
            if predicted_populated:
                per_field[field_name]["predicted_populated"] += 1
            if expected_populated and _field_hit(expected_value, predicted_value):
                per_field[field_name]["hit"] += 1
            else:
                if expected_populated:
                    record_ok = False
            if expected_populated and _field_exact_match(expected_value, predicted_value):
                per_field[field_name]["exact_match"] += 1
            field_details[field_name] = {
                "expected": expected_value,
                "predicted": predicted_value,
            }

        if record_ok:
            fully_correct += 1
        sample_results.append({
            "case_id": key,
            "all_expected_fields_hit": record_ok,
            "details": field_details,
        })

    total_cases = len(gold_items)
    summary = {}
    for field_name, counters in per_field.items():
        gold_populated = counters["gold_populated"]
        summary[field_name] = {
            **counters,
            "hit_rate": round(counters["hit"] / gold_populated, 4) if gold_populated else 0.0,
            "exact_match_rate": round(counters["exact_match"] / gold_populated, 4) if gold_populated else 0.0,
        }

    return {
        "total_cases": total_cases,
        "sample_accuracy": round(fully_correct / total_cases, 4) if total_cases else 0.0,
        "field_metrics": summary,
        "samples": sample_results,
    }

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = REPO_ROOT / "data" / "processed" / "jobs_master.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "jobs_computer_only.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "data" / "interim" / "jobs_computer_filter_report.json"


TECH_CATEGORIES = {"前端开发", "后端开发", "测试开发", "算法/AI", "安全", "数据开发", "数据分析"}
CORE_TECH_TAGS = {
    "Java",
    "Python",
    "Go",
    "C++",
    "前端",
    "后端",
    "全栈",
    "测试",
    "运维",
    "数据分析",
    "数据开发",
    "算法",
    "AI",
    "SQL",
    "Linux",
    "云计算",
    "网络安全",
}
IT_INDUSTRY_KEYWORDS = (
    "互联网",
    "计算机软件",
    "IT服务",
    "人工智能",
    "信息安全",
    "数据服务",
    "通信网络",
    "云计算",
    "物联网",
)
AMBIGUOUS_TECH_TITLES = {"技术支持工程师", "实施工程师", "科研人员", "质量管理/测试"}

TECH_TITLE_REGEX = re.compile(
    r"(java|python|golang|go|c\+\+|前端|后端|全栈|测试|运维|devops|sre|算法|机器学习|深度学习|ai|"
    r"数据分析|数据开发|数仓|etl|bi|爬虫|数据库|架构师|研发工程师|软件工程师|开发工程师|"
    r"信息安全|网络安全|系统工程师|技术支持工程师|实施工程师|软件测试|硬件测试)",
    re.IGNORECASE,
)
TECH_ROLE_REGEX = re.compile(r"(工程师|开发|测试|运维|架构|算法|数据|技术支持|实施|程序员|研发)")
EXCLUDE_TITLE_REGEX = re.compile(
    r"(销售|客服|律师|翻译|培训|大客户代表|猎头|法务|广告|电话销售|网络销售|"
    r"储备干部|管培生|质检|风电|招投标|BD|推广|资料管理|档案管理|统计员|"
    r"专员|助理|经理人|运营|审核)"
)


@dataclass(slots=True)
class FilterDecision:
    keep: bool
    reason: str


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _contains_it_industry(industry: str) -> bool:
    return any(keyword in industry for keyword in IT_INDUSTRY_KEYWORDS)


def _has_core_tech_tag(tags: list[str]) -> bool:
    return any(tag in CORE_TECH_TAGS for tag in tags)


def decide_keep(record: dict[str, Any]) -> FilterDecision:
    position_name = _normalize_text(record.get("position_name"))
    position_name_normalized = _normalize_text(record.get("position_name_normalized"))
    title_corpus = f"{position_name} {position_name_normalized}".strip()
    industry = _normalize_text(record.get("industry"))
    job_category = _normalize_text(record.get("job_category"))
    job_tags_raw = record.get("job_tags") or []
    job_tags = [str(tag) for tag in job_tags_raw if str(tag).strip()]

    is_excluded_title = bool(EXCLUDE_TITLE_REGEX.search(position_name))
    has_it_title = bool(TECH_TITLE_REGEX.search(title_corpus))
    has_tech_role = bool(TECH_ROLE_REGEX.search(position_name))
    has_it_category = job_category in TECH_CATEGORIES
    has_core_tag = _has_core_tech_tag(job_tags)
    has_it_industry = _contains_it_industry(industry)
    is_ambiguous_title = position_name in AMBIGUOUS_TECH_TITLES

    if is_excluded_title and not has_it_title:
        return FilterDecision(keep=False, reason="exclude_title_keyword")

    if has_it_title:
        if is_ambiguous_title and not (has_it_industry or has_core_tag):
            return FilterDecision(keep=False, reason="ambiguous_without_it_context")
        return FilterDecision(keep=True, reason="position_name_match")

    if has_it_category and has_tech_role and not is_excluded_title:
        return FilterDecision(keep=True, reason="job_category_role_match")

    if has_core_tag and has_tech_role and not is_excluded_title:
        return FilterDecision(keep=True, reason="job_tags_role_match")

    if has_it_industry and has_tech_role and not is_excluded_title:
        return FilterDecision(keep=True, reason="industry_role_match")

    return FilterDecision(keep=False, reason="no_it_signal")


def _sample_item(record: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "position_name": record.get("position_name"),
        "position_name_normalized": record.get("position_name_normalized"),
        "job_category": record.get("job_category"),
        "industry": record.get("industry"),
        "job_tags": record.get("job_tags"),
        "salary_range": record.get("salary_range"),
        "work_city": record.get("work_city"),
        "canonical_key": record.get("canonical_key"),
        "reason": reason,
    }


def run_filter(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    records = payload.get("records") or []
    if not isinstance(records, list):
        raise ValueError("Input JSON field 'records' must be a list")

    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    kept_examples: list[dict[str, Any]] = []
    removed_examples: list[dict[str, Any]] = []
    keep_reason_counter: dict[str, int] = {}
    remove_reason_counter: dict[str, int] = {}

    for record in records:
        if not isinstance(record, dict):
            continue
        decision = decide_keep(record)
        if decision.keep:
            kept.append(record)
            keep_reason_counter[decision.reason] = keep_reason_counter.get(decision.reason, 0) + 1
            if len(kept_examples) < 10:
                kept_examples.append(_sample_item(record, decision.reason))
        else:
            removed.append(record)
            remove_reason_counter[decision.reason] = remove_reason_counter.get(decision.reason, 0) + 1
            if len(removed_examples) < 10:
                removed_examples.append(_sample_item(record, decision.reason))

    filtered_payload = {
        "batch_id": payload.get("batch_id"),
        "batch_name": payload.get("batch_name"),
        "source_file": str(input_path),
        "filter_version": "computer_jobs_v1",
        "record_count": len(kept),
        "records": kept,
    }

    report_payload = {
        "source_file": str(input_path),
        "output_file": str(output_path),
        "filter_version": "computer_jobs_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "original_count": len(records),
        "kept_count": len(kept),
        "removed_count": len(removed),
        "keep_reason_breakdown": keep_reason_counter,
        "remove_reason_breakdown": remove_reason_counter,
        "kept_examples": kept_examples,
        "removed_examples": removed_examples,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(filtered_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "original_count": len(records),
        "kept_count": len(kept),
        "removed_count": len(removed),
        "output_path": str(output_path),
        "report_path": str(report_path),
    }


def main() -> None:
    summary = run_filter()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

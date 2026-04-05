from __future__ import annotations

from collections.abc import Iterable

from app.modules.matching.utils import normalize_list, normalize_text

JOB_FAMILY_TECH_DEV = "tech_dev"
JOB_FAMILY_DATA = "data"
JOB_FAMILY_PRODUCT = "product"
JOB_FAMILY_OPS = "ops"
JOB_FAMILY_ADMIN = "admin"
JOB_FAMILY_LEGAL = "legal"
JOB_FAMILY_OTHER = "other"

JOB_FAMILY_LABELS = {
    JOB_FAMILY_TECH_DEV: "\u6280\u672f\u5f00\u53d1",
    JOB_FAMILY_DATA: "\u6570\u636e",
    JOB_FAMILY_PRODUCT: "\u4ea7\u54c1",
    JOB_FAMILY_OPS: "\u8fd0\u8425",
    JOB_FAMILY_ADMIN: "\u884c\u653f\u52a9\u7406",
    JOB_FAMILY_LEGAL: "\u6cd5\u5f8b",
    JOB_FAMILY_OTHER: "\u5176\u4ed6",
}

COMPUTER_STUDENT_FAMILY_WEIGHTS = {
    JOB_FAMILY_TECH_DEV: 1.0,
    JOB_FAMILY_DATA: 0.9,
    JOB_FAMILY_PRODUCT: 0.7,
    JOB_FAMILY_OPS: 0.2,
    JOB_FAMILY_ADMIN: 0.2,
    JOB_FAMILY_LEGAL: 0.1,
    JOB_FAMILY_OTHER: 0.6,
}

_FAMILY_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (JOB_FAMILY_LEGAL, ("\u6cd5\u52a1", "\u6cd5\u5f8b", "\u5f8b\u5e08", "\u5408\u89c4", "\u6cd5\u5b66")),
    (JOB_FAMILY_DATA, ("\u6570\u636e\u5206\u6790", "\u6570\u636e\u5de5\u7a0b", "\u6570\u636e\u5f00\u53d1", "\u6570\u636e\u6cbb\u7406", "\u6570\u636e\u79d1\u5b66", "\u6570\u4ed3", "etl", "bi")),
    (JOB_FAMILY_PRODUCT, ("\u4ea7\u54c1\u7ecf\u7406", "\u4ea7\u54c1\u4e13\u5458", "\u4ea7\u54c1\u52a9\u7406", "\u4ea7\u54c1\u7b56\u5212", "product manager")),
    (JOB_FAMILY_OPS, (
    "运营", "用户增长", "内容", "活动", "社群", "电商",
    "管培生", "储备干部", "管理培训生",
    "销售", "市场", "商务", "渠道"
    )),
    (JOB_FAMILY_ADMIN, ("\u603b\u52a9", "\u52a9\u7406", "\u884c\u653f", "\u79d8\u4e66", "ceo\u52a9\u7406", "\u8463\u4e8b\u957f\u52a9\u7406", "\u603b\u7ecf\u7406\u52a9\u7406")),
    (
        JOB_FAMILY_TECH_DEV,
        (
            "\u540e\u7aef",
            "\u524d\u7aef",
            "\u5f00\u53d1",
            "\u6d4b\u8bd5",
            "\u8fd0\u7ef4",
            "\u5168\u6808",
            "java",
            "python",
            "react",
            "fastapi",
            "spring",
            "\u7b97\u6cd5",
            "ai",
            "\u673a\u5668\u5b66\u4e60",
            "\u7814\u53d1",
            "\u6280\u672f\u652f\u6301",
            "\u5b9e\u65bd\u5de5\u7a0b\u5e08",
            "\u5de5\u7a0b\u5e08",
            "devops",
            "\u67b6\u6784",
        ),
    ),
)

_COMPUTER_MAJOR_MARKERS = (
    "\u8ba1\u7b97\u673a",
    "\u8f6f\u4ef6\u5de5\u7a0b",
    "\u7f51\u7edc\u5de5\u7a0b",
    "\u4fe1\u606f\u5de5\u7a0b",
    "\u6570\u636e\u79d1\u5b66",
    "\u4eba\u5de5\u667a\u80fd",
    "\u667a\u80fd\u79d1\u5b66",
    "\u7f51\u7edc\u7a7a\u95f4\u5b89\u5168",
)

_COMPUTER_SKILL_MARKERS = {
    "python",
    "java",
    "react",
    "fastapi",
    "mysql",
    "redis",
    "git",
    "sql",
    "javascript",
    "typescript",
    "spring boot",
    "spring",
    "docker",
    "linux",
    "c++",
    "go",
    "php",
}

_TECHNICAL_FAMILIES = {JOB_FAMILY_TECH_DEV, JOB_FAMILY_DATA}
_BLOCKED_FROM_TECH_FAMILIES = {JOB_FAMILY_ADMIN, JOB_FAMILY_LEGAL}


def classify_job_family(
    job_title: str,
    *,
    summary: str = "",
    skills: Iterable[str] | None = None,
    industry_tags: Iterable[str] | None = None,
) -> str:
    title_corpus = normalize_text(job_title, default="").lower()
    for family, markers in _FAMILY_MARKERS:
        if any(marker.lower() in title_corpus for marker in markers):
            return family

    fallback_corpus = " ".join(
        part
        for part in [
            normalize_text(summary, default=""),
            " ".join(normalize_list(list(skills or []))),
            " ".join(normalize_list(list(industry_tags or []))),
        ]
        if part
    ).lower()
    for family, markers in _FAMILY_MARKERS:
        if any(marker.lower() in fallback_corpus for marker in markers):
            return family
    return JOB_FAMILY_OTHER


def is_computer_student(
    *,
    major: str = "",
    skills: Iterable[str] | None = None,
    summary: str = "",
) -> bool:
    normalized_major = normalize_text(major, default="").lower()
    if any(marker.lower() in normalized_major for marker in _COMPUTER_MAJOR_MARKERS):
        return True

    corpus = " ".join(normalize_list(list(skills or [])) + [normalize_text(summary, default="")]).lower()
    return any(marker in corpus for marker in _COMPUTER_SKILL_MARKERS)


def family_weight_for_student(
    *,
    is_computer_related: bool,
    job_family: str,
) -> float:
    if not is_computer_related:
        return 1.0
    return COMPUTER_STUDENT_FAMILY_WEIGHTS.get(job_family, COMPUTER_STUDENT_FAMILY_WEIGHTS[JOB_FAMILY_OTHER])


def is_preferred_path_family(job_family: str) -> bool:
    return job_family in _TECHNICAL_FAMILIES


def is_path_transition_allowed(source_family: str, target_family: str) -> bool:
    return not (source_family in _BLOCKED_FROM_TECH_FAMILIES and target_family in _TECHNICAL_FAMILIES)


def is_blocked_family_pair(left_family: str, right_family: str) -> bool:
    return (
        (left_family in _BLOCKED_FROM_TECH_FAMILIES and right_family in _TECHNICAL_FAMILIES)
        or (right_family in _BLOCKED_FROM_TECH_FAMILIES and left_family in _TECHNICAL_FAMILIES)
    )
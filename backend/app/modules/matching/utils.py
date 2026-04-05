from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Iterable

from app.modules.matching.config import EDUCATION_LEVELS, SKILL_PATTERNS, TEXT_DEFAULT

SKILL_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in SKILL_PATTERNS:
    SKILL_ALIAS_TO_CANONICAL[canonical.lower()] = canonical
    for alias in aliases:
        SKILL_ALIAS_TO_CANONICAL[alias.lower()] = canonical



def normalize_text(value: Any, default: str = TEXT_DEFAULT) -> str:
    if value is None:
        return default
    if isinstance(value, list):
        for item in value:
            text = normalize_text(item, default="")
            if text:
                return text
        return default
    if isinstance(value, dict):
        return default
    text = re.sub(r"\s+", " ", str(value).replace("\u3000", " ")).strip()
    return text or default



def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        return []
    values = value if isinstance(value, list) else re.split(r"[\n,，/、;；|]+", str(value))
    result: list[str] = []
    for item in values:
        text = normalize_text(item, default="")
        if text and text != TEXT_DEFAULT and text not in result:
            result.append(text)
    return result



def unique_keep_order(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = normalize_text(value, default="")
        lowered = text.lower()
        if text and lowered not in seen:
            seen.add(lowered)
            result.append(text)
    return result



def clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(100.0, score)), 2)



def normalize_evidence_map(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    return {str(key): normalize_list(item) for key, item in value.items()}



def canonicalize_skill(value: str) -> str:
    text = normalize_text(value, default="")
    lowered = text.lower()
    return SKILL_ALIAS_TO_CANONICAL.get(lowered, text)



def tokenize_skill(value: str) -> set[str]:
    text = normalize_text(value, default="").lower()
    if not text:
        return set()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff#+.-]+", " ", text)
    return {token for token in text.split() if token}



def skill_similarity(left: str, right: str) -> float:
    left_text = normalize_text(left, default="")
    right_text = normalize_text(right, default="")
    if not left_text or not right_text:
        return 0.0
    left_canonical = canonicalize_skill(left_text)
    right_canonical = canonicalize_skill(right_text)
    if left_canonical.lower() == right_canonical.lower():
        return 1.0
    left_tokens = tokenize_skill(left_canonical)
    right_tokens = tokenize_skill(right_canonical)
    if left_tokens and right_tokens:
        overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
        if overlap > 0:
            return round(max(overlap, SequenceMatcher(None, left_canonical.lower(), right_canonical.lower()).ratio()), 4)
    return round(SequenceMatcher(None, left_canonical.lower(), right_canonical.lower()).ratio(), 4)



def best_skill_match(target_skill: str, candidate_skills: list[str], extra_corpus: Iterable[str] | None = None) -> dict[str, Any]:
    normalized_target = canonicalize_skill(target_skill)
    best = {
        "required_skill": normalized_target,
        "matched": False,
        "matched_skill": "",
        "confidence": 0.0,
        "match_type": "missing",
        "evidence": [],
    }
    corpus = list(extra_corpus or [])
    for candidate in candidate_skills:
        similarity = skill_similarity(normalized_target, candidate)
        if similarity <= best["confidence"]:
            continue
        match_type = "fuzzy"
        if similarity >= 0.99:
            match_type = "exact"
        elif canonicalize_skill(normalized_target).lower() == canonicalize_skill(candidate).lower():
            match_type = "synonym"
        elif similarity >= 0.75:
            match_type = "partial"
        best = {
            "required_skill": normalized_target,
            "matched": similarity >= 0.62,
            "matched_skill": canonicalize_skill(candidate),
            "confidence": round(similarity, 4),
            "match_type": match_type,
            "evidence": [candidate],
        }
    if not best["matched"] and corpus:
        lowered_target = normalized_target.lower()
        for snippet in corpus:
            lowered_snippet = snippet.lower()
            if lowered_target in lowered_snippet:
                return {
                    "required_skill": normalized_target,
                    "matched": True,
                    "matched_skill": normalized_target,
                    "confidence": 0.68,
                    "match_type": "evidence",
                    "evidence": [snippet],
                }
            canonical = canonicalize_skill(normalized_target).lower()
            if canonical and canonical in lowered_snippet:
                return {
                    "required_skill": normalized_target,
                    "matched": True,
                    "matched_skill": normalized_target,
                    "confidence": 0.68,
                    "match_type": "evidence",
                    "evidence": [snippet],
                }
    return best



def parse_education_rank(value: str) -> int:
    text = normalize_text(value, default="")
    for marker, rank in sorted(EDUCATION_LEVELS.items(), key=lambda item: item[1], reverse=True):
        if marker in text:
            return rank
    return -1



def parse_experience_requirement(value: str) -> dict[str, Any]:
    text = normalize_text(value, default="")
    if not text or text == TEXT_DEFAULT or text == "经验不限":
        return {"kind": "none", "min_years": 0.0, "max_years": None, "label": text or TEXT_DEFAULT}
    if any(marker in text for marker in ("应届", "实习", "校招")):
        return {"kind": "entry", "min_years": 0.0, "max_years": 1.0, "label": text}
    match = re.search(r"(\d+(?:\.\d+)?)\s*[-~至到]\s*(\d+(?:\.\d+)?)\s*年", text)
    if match:
        left = float(match.group(1))
        right = float(match.group(2))
        return {"kind": "range", "min_years": left, "max_years": right, "label": text}
    match = re.search(r"(\d+(?:\.\d+)?)\s*年(?:以上|及以上)?", text)
    if match:
        years = float(match.group(1))
        return {"kind": "minimum", "min_years": years, "max_years": None, "label": text}
    return {"kind": "unknown", "min_years": 0.0, "max_years": None, "label": text}



def estimate_student_experience_years(internship_count: int, internship_score: float) -> float:
    estimated = 0.0
    if internship_count > 0:
        estimated += min(1.5, 0.5 + max(internship_count - 1, 0) * 0.35)
    if internship_score >= 80:
        estimated += 0.5
    elif internship_score >= 65:
        estimated += 0.25
    return round(min(2.5, estimated), 2)



def get_student_ability_score(student: Any, ability_key: str) -> float:
    aliases = {
        "communication": ("communication_score", "communication"),
        "learning": ("learning_score", "learning"),
        "innovation": ("innovation_score", "innovation"),
        "stress_score": ("stress_score", "stress_tolerance_score", "stress_tolerance"),
        "internship": ("internship_score", "internship_ability_score", "internship_ability"),
        "professional_skill_score": ("professional_skill_score", "professional_skills_score"),
    }
    for field_name in aliases.get(ability_key, (ability_key,)):
        if hasattr(student, field_name):
            return clamp_score(getattr(student, field_name))
    return 0.0



def summarize_snippets(*groups: Iterable[str], limit: int = 6) -> list[str]:
    collected: list[str] = []
    for group in groups:
        for item in group:
            text = normalize_text(item, default="")
            if text and text not in collected:
                collected.append(text)
            if len(collected) >= limit:
                return collected
    return collected



def text_overlap_score(left: str, right: str) -> float:
    left_tokens = tokenize_skill(left)
    right_tokens = tokenize_skill(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return round(len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1), 4)


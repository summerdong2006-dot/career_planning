from __future__ import annotations

import json
from typing import Any

from app.modules.student_profile.schema import (
    TEXT_DEFAULT,
    StudentCompetition,
    StudentInternship,
    StudentProfilePayload,
    StudentProject,
    StudentWorkExperience,
    normalize_list_field,
    normalize_text_field,
)



def unique_keep_order(items: list[Any], key_func=None) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for item in items:
        key = key_func(item) if key_func is not None else json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result



def _text_key(value: Any) -> str:
    return normalize_text_field(value, default="")



def _dict_key(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, sort_keys=True)



def flatten_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(flatten_string_list(item))
        return result
    if isinstance(value, dict):
        return []
    text = normalize_text_field(value, default="")
    return [text] if text else []



def normalize_string_list(value: Any) -> list[str]:
    flattened = flatten_string_list(value)
    return unique_keep_order([item for item in flattened if item.strip()], key_func=_text_key)



def _build_projects(raw_items: list[Any]) -> list[StudentProject]:
    normalized: list[StudentProject] = []
    for item in raw_items:
        if isinstance(item, dict):
            normalized.append(StudentProject.model_validate(item))
            continue
        text = normalize_text_field(item, default="")
        if text:
            normalized.append(StudentProject(name=text, role=TEXT_DEFAULT, description=text))
    return unique_keep_order(normalized, key_func=_dict_key)



def _build_internships(raw_items: list[Any]) -> list[StudentInternship]:
    normalized: list[StudentInternship] = []
    for item in raw_items:
        if isinstance(item, dict):
            normalized.append(StudentInternship.model_validate(item))
            continue
        text = normalize_text_field(item, default="")
        if text:
            normalized.append(StudentInternship(company=TEXT_DEFAULT, role=TEXT_DEFAULT, description=text))
    return unique_keep_order(normalized, key_func=_dict_key)



def _build_competitions(raw_items: list[Any]) -> list[StudentCompetition]:
    unique_items = unique_keep_order(list(raw_items), key_func=_text_key)
    return [StudentCompetition(name=item, award=TEXT_DEFAULT, description=item) for item in unique_items]



def _build_student_work(raw_items: list[Any]) -> list[StudentWorkExperience]:
    unique_items = unique_keep_order(list(raw_items), key_func=_text_key)
    return [StudentWorkExperience(organization=TEXT_DEFAULT, role=TEXT_DEFAULT, description=item) for item in unique_items]



def _dedupe_model_list(items: list[Any], model_cls):
    normalized_items = [model_cls.model_validate(item) for item in items]
    return unique_keep_order(normalized_items, key_func=_dict_key)



def build_summary(payload: dict[str, Any]) -> str:
    school = normalize_text_field(payload.get("school"))
    major = normalize_text_field(payload.get("major"))
    education = normalize_text_field(payload.get("education"))
    skills = payload.get("skills", [])
    internships = payload.get("internships", [])
    projects = payload.get("projects", [])
    career_intention = normalize_text_field(payload.get("career_intention"))

    summary_parts = [
        f"{school}{major}{education}背景学生" if school != TEXT_DEFAULT or major != TEXT_DEFAULT else "学生背景信息待补充",
        f"具备{'、'.join(skills[:5])}等技能" if skills else "技能信息待补充",
        f"拥有{len(projects)}段项目经历" if projects else "项目经历待补充",
        f"拥有{len(internships)}段实习/实践经历" if internships else "实习经历待补充",
        f"职业意向为{career_intention}" if career_intention != TEXT_DEFAULT else "职业意向待补充",
    ]
    return "，".join(summary_parts)



def stabilize_profile_payload(payload: StudentProfilePayload | dict[str, Any]) -> StudentProfilePayload:
    data = payload.model_dump(mode="json") if isinstance(payload, StudentProfilePayload) else dict(payload)
    data["skills"] = unique_keep_order(normalize_list_field(data.get("skills")), key_func=_text_key)
    data["certificates"] = normalize_string_list(data.get("certificates"))
    data["innovation_experiences"] = unique_keep_order(normalize_list_field(data.get("innovation_experiences")), key_func=_text_key)
    data["projects"] = _dedupe_model_list(data.get("projects", []), StudentProject)
    data["internships"] = _dedupe_model_list(data.get("internships", []), StudentInternship)
    data["competitions"] = _dedupe_model_list(data.get("competitions", []), StudentCompetition)
    data["student_work"] = _dedupe_model_list(data.get("student_work", []), StudentWorkExperience)

    evidence = data.get("evidence") or {}
    if isinstance(evidence, dict):
        data["evidence"] = {
            key: unique_keep_order(normalize_list_field(value), key_func=_text_key)
            for key, value in evidence.items()
        }

    return StudentProfilePayload.model_validate(data)



def normalize_profile_payload(raw_payload: dict[str, Any], extras: dict[str, Any]) -> StudentProfilePayload:
    base_fields = raw_payload.get("base_fields", {})
    payload = {
        "student_name": base_fields.get("student_name", TEXT_DEFAULT),
        "student_no": base_fields.get("student_no", TEXT_DEFAULT),
        "school": base_fields.get("school", TEXT_DEFAULT),
        "major": base_fields.get("major", TEXT_DEFAULT),
        "education": base_fields.get("education", TEXT_DEFAULT),
        "grade": base_fields.get("grade", TEXT_DEFAULT),
        "skills": unique_keep_order(raw_payload.get("skills", []), key_func=_text_key),
        "projects": _build_projects(raw_payload.get("projects", [])),
        "internships": _build_internships(raw_payload.get("internships", [])),
        "competitions": _build_competitions(raw_payload.get("competitions", [])),
        "certificates": normalize_string_list(raw_payload.get("certificates", [])),
        "student_work": _build_student_work(raw_payload.get("student_work", [])),
        "career_intention": raw_payload.get("career_intention", TEXT_DEFAULT),
        "innovation_experiences": unique_keep_order(raw_payload.get("innovation_experiences", []), key_func=_text_key),
        "ability_scores": extras.get("ability_scores"),
        "completeness_score": extras.get("completeness_score", 0.0),
        "competitiveness_score": extras.get("competitiveness_score", 0.0),
        "missing_items": extras.get("missing_items", []),
        "evidence": extras.get("evidence"),
        "summary": extras.get("summary") or build_summary(
            {
                "school": base_fields.get("school"),
                "major": base_fields.get("major"),
                "education": base_fields.get("education"),
                "skills": raw_payload.get("skills", []),
                "projects": raw_payload.get("projects", []),
                "internships": raw_payload.get("internships", []),
                "career_intention": raw_payload.get("career_intention", TEXT_DEFAULT),
            }
        ),
        "resume_source": raw_payload.get("resume_source", TEXT_DEFAULT),
    }
    return stabilize_profile_payload(payload)

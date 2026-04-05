from __future__ import annotations

from typing import Any

from app.modules.student_profile.schema import StudentProfileEvidence


def build_evidence(raw_payload: dict[str, Any], summary: str = "未明确") -> StudentProfileEvidence:
    base_fields = raw_payload.get("base_fields", {})
    field_evidence = base_fields.get("field_evidence", {})
    sections = raw_payload.get("sections", {})

    return StudentProfileEvidence(
        student_name=field_evidence.get("student_name", []),
        student_no=field_evidence.get("student_no", []),
        school=field_evidence.get("school", []),
        major=field_evidence.get("major", []),
        education=field_evidence.get("education", []),
        grade=field_evidence.get("grade", []),
        skills=sections.get("skills", []),
        projects=sections.get("projects", []),
        internships=sections.get("internships", []),
        competitions=sections.get("competitions", []),
        certificates=sections.get("certificates", []),
        student_work=sections.get("student_work", []),
        career_intention=sections.get("career_intention", []),
        professional_skills=sections.get("skills", []),
        innovation=(sections.get("innovation_experiences", []) + sections.get("competitions", []) + sections.get("projects", []))[:6],
        learning=(sections.get("certificates", []) + sections.get("skills", []) + sections.get("projects", []))[:6],
        stress_tolerance=(sections.get("internships", []) + sections.get("student_work", []))[:6],
        communication=(sections.get("student_work", []) + sections.get("projects", []))[:6],
        internship_ability=sections.get("internships", []),
        summary=[summary] if summary else [],
    )

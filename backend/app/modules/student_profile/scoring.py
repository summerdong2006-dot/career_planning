from __future__ import annotations

from app.modules.student_profile.schema import (
    ABILITY_LABELS,
    MissingItem,
    ScoringWeights,
    StudentProfileAbilityScore,
    StudentProfileEvidence,
)

MISSING_FIELD_CONFIG = {
    "school": ("学校", "补充毕业院校名称，例如“XX大学”。", "high"),
    "major": ("专业", "补充主修专业，便于后续岗位匹配。", "high"),
    "education": ("学历", "补充最高学历，例如本科或硕士。", "high"),
    "grade": ("年级", "补充年级或毕业届次。", "medium"),
    "skills": ("技能", "补充至少 3 项专业技能或工具。", "high"),
    "projects": ("项目经历", "补充至少 1 段项目经历，说明角色与产出。", "high"),
    "internships": ("实习经历", "补充实习/实践经历，说明公司、岗位和成果。", "medium"),
    "certificates": ("证书", "补充证书或语言成绩，没有则保持为空。", "low"),
    "career_intention": ("职业意向", "补充目标岗位或行业方向。", "medium"),
    "student_work": ("学生工作", "补充学生工作、社团或组织经历。", "low"),
    "competitions": ("竞赛经历", "补充竞赛、科研或创新经历。", "medium"),
}


def _score_by_count(count: int, max_count: int, base: float = 0.0) -> float:
    if max_count <= 0:
        return 0.0
    return min(100.0, round(base + (count / max_count) * (100.0 - base), 2))


def calculate_ability_scores(raw_payload: dict, evidence: StudentProfileEvidence) -> StudentProfileAbilityScore:
    skills = raw_payload.get("skills", [])
    projects = raw_payload.get("projects", [])
    internships = raw_payload.get("internships", [])
    competitions = raw_payload.get("competitions", [])
    certificates = raw_payload.get("certificates", [])
    student_work = raw_payload.get("student_work", [])
    innovation_experiences = raw_payload.get("innovation_experiences", [])

    professional = _score_by_count(len(skills) * 2 + len(projects) + len(certificates), 12, base=15.0)
    innovation = _score_by_count(len(innovation_experiences) + len(competitions) + len(projects), 8, base=10.0)
    learning = _score_by_count(len(certificates) + len(skills) + len(evidence.learning), 14, base=20.0)
    stress = _score_by_count(len(internships) + len(student_work) + len(evidence.stress_tolerance), 10, base=18.0)
    communication = _score_by_count(len(student_work) + len(projects) + len(evidence.communication), 10, base=20.0)
    internship_ability = _score_by_count(len(internships) * 2 + len(projects), 10, base=12.0)

    return StudentProfileAbilityScore(
        professional_skills=professional,
        innovation=innovation,
        learning=learning,
        stress_tolerance=stress,
        communication=communication,
        internship_ability=internship_ability,
    )


def calculate_completeness_score(profile: dict) -> float:
    total = len(MISSING_FIELD_CONFIG)
    missing = 0
    for field_name in MISSING_FIELD_CONFIG:
        value = profile.get(field_name)
        if value in ("未明确", None, "") or value == []:
            missing += 1
    return round(max(0.0, min(100.0, ((total - missing) / total) * 100.0)), 2)


def calculate_competitiveness_score(ability_scores: StudentProfileAbilityScore, weights: ScoringWeights) -> float:
    normalized = weights.normalized()
    total = 0.0
    for field_name, weight in normalized.items():
        total += getattr(ability_scores, field_name) * weight
    return round(max(0.0, min(100.0, total)), 2)


def identify_missing_items(profile: dict, evidence: StudentProfileEvidence) -> list[MissingItem]:
    missing_items: list[MissingItem] = []
    for field_name, (label, suggestion, severity) in MISSING_FIELD_CONFIG.items():
        value = profile.get(field_name)
        if value in ("未明确", None, "") or value == []:
            missing_items.append(
                MissingItem(field=field_name, label=label, suggestion=suggestion, severity=severity)
            )
    if not any(getattr(evidence, field_name, []) for field_name in ABILITY_LABELS):
        missing_items.append(
            MissingItem(
                field="ability_evidence",
                label="能力佐证",
                suggestion="补充能体现能力的项目、竞赛或实习片段，便于后续证据追溯。",
                severity="high",
            )
        )
    return missing_items


def attach_score_evidence(
    evidence: StudentProfileEvidence,
    ability_scores: StudentProfileAbilityScore,
    completeness_score: float,
    competitiveness_score: float,
    missing_items: list[MissingItem],
) -> StudentProfileEvidence:
    evidence.professional_skills = evidence.professional_skills or evidence.skills
    evidence.innovation = evidence.innovation or evidence.competitions or evidence.projects
    evidence.learning = evidence.learning or evidence.certificates or evidence.skills
    evidence.stress_tolerance = evidence.stress_tolerance or evidence.internships or evidence.student_work
    evidence.communication = evidence.communication or evidence.student_work or evidence.projects
    evidence.internship_ability = evidence.internship_ability or evidence.internships or evidence.projects
    evidence.completeness_score = [f"完整度由已识别字段覆盖情况计算，当前为 {completeness_score} 分。"]
    evidence.competitiveness_score = [
        "；".join(f"{ABILITY_LABELS[key]} {getattr(ability_scores, key)} 分" for key in ABILITY_LABELS),
        f"综合竞争力得分为 {competitiveness_score} 分。",
    ]
    evidence.missing_items = [f"{item.label}: {item.suggestion}" for item in missing_items]
    return evidence

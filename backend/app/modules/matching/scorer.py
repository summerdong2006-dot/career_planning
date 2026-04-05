from __future__ import annotations

from typing import Any

from app.modules.matching.config import ABILITY_LABELS, SOFT_SKILL_TO_ABILITY, TEXT_DEFAULT
from app.modules.matching.schema import JobMatchProfile, MatchDimensionDetail, MatchingWeights, StudentMatchProfile
from app.modules.matching.utils import (
    best_skill_match,
    clamp_score,
    estimate_student_experience_years,
    get_student_ability_score,
    parse_education_rank,
    parse_experience_requirement,
    summarize_snippets,
    text_overlap_score,
    unique_keep_order,
)



def score_base_requirement(student: StudentMatchProfile, job: JobMatchProfile) -> MatchDimensionDetail:
    missing_items: list[str] = []
    gaps: list[str] = []
    evidence: list[str] = []
    component_scores: list[tuple[str, float, float]] = []
    checks: list[bool] = []
    details: dict[str, Any] = {}

    student_rank = parse_education_rank(student.education)
    required_rank = parse_education_rank(job.education_requirement)
    if required_rank <= 0:
        education_score = 85.0
        education_matched = True
        details["education"] = {"required": job.education_requirement, "student": student.education, "matched": True}
    else:
        education_matched = student_rank >= required_rank
        if education_matched:
            education_score = 100.0
            evidence.append(f"学生学历为{student.education}，满足岗位学历要求{job.education_requirement}")
        elif student_rank == required_rank - 1:
            education_score = 45.0
            missing_items.append(f"学历要求为{job.education_requirement}，当前为{student.education}")
        else:
            education_score = 10.0
            missing_items.append(f"学历差距较大：岗位要求{job.education_requirement}，当前为{student.education}")
        details["education"] = {"required": job.education_requirement, "student": student.education, "matched": education_matched}
        checks.append(education_matched)
    component_scores.append(("education", education_score, 0.4))

    experience_requirement = parse_experience_requirement(job.years_experience_requirement)
    estimated_years = estimate_student_experience_years(student.internship_count, student.internship_score)
    if experience_requirement["kind"] == "none":
        experience_score = 85.0
        experience_matched = True
    elif experience_requirement["kind"] == "entry":
        experience_matched = True
        experience_score = 92.0 if student.internship_count > 0 or student.internship_score >= 55 else 78.0
        if student.internship_count > 0:
            evidence.append(f"学生已有{student.internship_count}段实习/实践经历，可投递应届/实习类岗位")
    else:
        experience_matched = estimated_years >= float(experience_requirement["min_years"])
        if experience_matched:
            experience_score = 100.0
            evidence.append(
                f"学生实践经验折算约{estimated_years}年，接近或满足岗位经验要求{job.years_experience_requirement}"
            )
        elif estimated_years >= max(0.5, float(experience_requirement["min_years"]) * 0.5):
            experience_score = 55.0
            missing_items.append(f"岗位要求{job.years_experience_requirement}经验，当前经验储备偏弱")
        else:
            experience_score = 20.0
            missing_items.append(f"岗位要求{job.years_experience_requirement}经验，当前缺少对应实践经历")
        checks.append(experience_matched)
    details["experience"] = {
        "required": job.years_experience_requirement,
        "estimated_years": estimated_years,
        "matched": experience_matched,
    }
    component_scores.append(("experience", experience_score, 0.35))

    required_certs = job.certificates
    matched_certs: list[str] = []
    if not required_certs:
        certificate_score = 85.0
        certificate_matched = True
    else:
        for certificate in required_certs:
            matched = best_skill_match(certificate, student.certificates)
            if matched["matched"]:
                matched_certs.append(certificate)
        coverage = len(matched_certs) / max(len(required_certs), 1)
        certificate_score = 40.0 + coverage * 60.0
        certificate_matched = coverage >= 1.0
        if matched_certs:
            evidence.append(f"学生证书与岗位要求匹配：{'、'.join(matched_certs)}")
        for certificate in required_certs:
            if certificate not in matched_certs:
                missing_items.append(f"缺少岗位要求证书：{certificate}")
        checks.append(certificate_matched)
    details["certificates"] = {
        "required": required_certs,
        "student": student.certificates,
        "matched": matched_certs,
    }
    component_scores.append(("certificates", certificate_score, 0.25))

    weight_total = sum(weight for _, _, weight in component_scores) or 1.0
    score = sum(value * weight for _, value, weight in component_scores) / weight_total
    if student.internship_count == 0 and "实习" in job.internship_requirement:
        gaps.append("岗位对实习到岗或实习经历有要求，当前实践经历偏少")
    gaps.extend(missing_items)
    matched = all(checks) if checks else True
    explanation = "基础门槛整体满足" if matched else "基础门槛存在硬性差距，需要重点关注学历、经验或证书要求"
    evidence = summarize_snippets(evidence, job.extracted_evidence.get("education_requirement", []), job.extracted_evidence.get("years_experience_requirement", []))
    return MatchDimensionDetail(
        score=score,
        matched=matched,
        explanation=explanation,
        evidence=evidence,
        gaps=unique_keep_order(gaps),
        unmet_items=unique_keep_order(missing_items),
        details=details,
    )



def score_skill_match(student: StudentMatchProfile, job: JobMatchProfile) -> MatchDimensionDetail:
    student_skills = unique_keep_order(student.professional_skills)
    student_corpus = summarize_snippets(
        student.professional_skills,
        student.extracted_evidence.get("skills", []),
        student.extracted_evidence.get("projects", []),
        student.extracted_evidence.get("summary", []),
    )
    must_matches = [best_skill_match(skill, student_skills, student_corpus) for skill in job.must_have_skills]
    nice_matches = [best_skill_match(skill, student_skills, student_corpus) for skill in job.nice_to_have_skills]

    if not job.must_have_skills and not job.nice_to_have_skills:
        fallback_score = clamp_score(max(55.0, student.professional_skill_score * 0.75 + 20.0))
        return MatchDimensionDetail(
            score=fallback_score,
            matched=fallback_score >= 60.0,
            explanation="岗位画像未明确列出核心技能，按学生专业技能分和已有技能清单进行估算",
            evidence=summarize_snippets(student_skills, student.extracted_evidence.get("skills", [])),
            gaps=[],
            unmet_items=[],
            details={"must_matches": [], "nice_matches": [], "student_skills": student_skills},
        )

    must_score = (
        sum(item["confidence"] if item["matched"] else 0.0 for item in must_matches)
        / len(job.must_have_skills)
        * 100.0
    ) if job.must_have_skills else 0.0
    nice_bonus = (
        sum(item["confidence"] if item["matched"] else 0.0 for item in nice_matches)
        / len(job.nice_to_have_skills)
        * 15.0
    ) if job.nice_to_have_skills else 0.0

    if job.must_have_skills:
        score = must_score * 0.85 + nice_bonus
    else:
        score = max(55.0, student.professional_skill_score * 0.75 + 20.0) + nice_bonus
    score = clamp_score(score)

    missing_must = [item["required_skill"] for item in must_matches if not item["matched"]]
    missing_nice = [item["required_skill"] for item in nice_matches if not item["matched"]]
    matched_skill_pairs = [
        f"{item['required_skill']} <- {item['matched_skill']}({item['match_type']})"
        for item in must_matches + nice_matches
        if item["matched"]
    ]
    evidence = summarize_snippets(
        matched_skill_pairs,
        student.extracted_evidence.get("skills", []),
        job.extracted_evidence.get("must_have_skills", []),
        job.extracted_evidence.get("nice_to_have_skills", []),
    )
    gaps = [f"缺少核心技能：{skill}" for skill in missing_must]
    gaps.extend(f"缺少加分技能：{skill}" for skill in missing_nice[:3])
    matched = not missing_must if job.must_have_skills else score >= 60.0
    explanation = "核心技能覆盖较好" if matched else "核心技能覆盖不足，必须技能存在缺口"
    return MatchDimensionDetail(
        score=score,
        matched=matched,
        explanation=explanation,
        evidence=evidence,
        gaps=unique_keep_order(gaps),
        unmet_items=unique_keep_order(missing_must),
        details={
            "must_matches": must_matches,
            "nice_matches": nice_matches,
            "missing_must_skills": missing_must,
            "missing_nice_skills": missing_nice,
        },
    )



def _resolve_soft_skill_ability(soft_skill: str) -> str:
    for marker, ability_key in SOFT_SKILL_TO_ABILITY.items():
        if marker in soft_skill:
            return ability_key
    return "communication"



def score_soft_skill_match(student: StudentMatchProfile, job: JobMatchProfile) -> MatchDimensionDetail:
    details: list[dict[str, Any]] = []
    evidence: list[str] = []
    gaps: list[str] = []

    if not job.soft_skills:
        fallback = (
            get_student_ability_score(student, "communication")
            + get_student_ability_score(student, "learning")
            + get_student_ability_score(student, "stress_score")
            + get_student_ability_score(student, "internship")
        ) / 4
        return MatchDimensionDetail(
            score=fallback,
            matched=fallback >= 60.0,
            explanation="岗位画像未明确列出职业素养要求，按学生通用能力分进行估算",
            evidence=summarize_snippets(
                student.extracted_evidence.get("communication", []),
                student.extracted_evidence.get("learning", []),
            ),
            gaps=[],
            unmet_items=[],
            details={"mapped_items": []},
        )

    for soft_skill in job.soft_skills:
        ability_key = _resolve_soft_skill_ability(soft_skill)
        ability_score = get_student_ability_score(student, ability_key)
        matched = ability_score >= 70.0
        if ability_score < 60.0:
            gaps.append(f"{soft_skill}对应的{ABILITY_LABELS.get(ability_key, ability_key)}偏弱")
        if matched:
            evidence.append(f"{soft_skill}映射到{ABILITY_LABELS.get(ability_key, ability_key)}，学生得分{ability_score}")
        details.append(
            {
                "soft_skill": soft_skill,
                "mapped_ability": ability_key,
                "ability_label": ABILITY_LABELS.get(ability_key, ability_key),
                "student_score": ability_score,
                "matched": matched,
            }
        )

    score = sum(item["student_score"] for item in details) / max(len(details), 1)
    explanation = "职业素养较匹配" if score >= 70.0 else "职业素养部分维度偏弱，需要补强软技能表现"
    evidence = summarize_snippets(
        evidence,
        student.extracted_evidence.get("communication", []),
        student.extracted_evidence.get("learning", []),
        student.extracted_evidence.get("internship_ability", []),
        job.extracted_evidence.get("soft_skills", []),
    )
    return MatchDimensionDetail(
        score=score,
        matched=score >= 60.0,
        explanation=explanation,
        evidence=evidence,
        gaps=unique_keep_order(gaps),
        unmet_items=unique_keep_order(gaps),
        details={"mapped_items": details},
    )



def score_growth_potential(
    student: StudentMatchProfile,
    job: JobMatchProfile,
    skill_detail: MatchDimensionDetail,
    soft_skill_detail: MatchDimensionDetail,
) -> MatchDimensionDetail:
    learning = get_student_ability_score(student, "learning")
    innovation = get_student_ability_score(student, "innovation")
    professional = get_student_ability_score(student, "professional_skill_score")
    current_capacity = (learning + innovation + professional) / 3

    career_alignment = max(
        text_overlap_score(student.career_intention, job.job_title),
        text_overlap_score(student.summary, job.job_title),
        text_overlap_score(student.career_intention, job.summary),
    ) * 100
    transferability = clamp_score(skill_detail.score * 0.55 + soft_skill_detail.score * 0.20 + career_alignment * 0.25)

    promotion_path = job.promotion_path or ([job.growth_potential] if job.growth_potential != TEXT_DEFAULT else [])
    growth_space = 60.0 + min(len(promotion_path), 3) * 10.0
    if any(marker in job.job_level for marker in ("实习", "校招", "初级")):
        growth_space += 5.0
    growth_space = clamp_score(growth_space)

    score = clamp_score(
        student.completeness_score * 0.22
        + student.competitiveness_score * 0.23
        + current_capacity * 0.20
        + transferability * 0.20
        + growth_space * 0.15
    )

    gaps: list[str] = []
    if student.completeness_score < 50.0:
        gaps.append("学生画像完整度偏低，潜力判断置信度下降")
    if student.competitiveness_score < 55.0:
        gaps.append("当前竞争力分偏低，成长兑现存在不确定性")
    if transferability < 60.0:
        gaps.append("当前技能与目标岗位晋升路径的可迁移性一般")

    evidence = summarize_snippets(
        [f"岗位晋升路径：{' -> '.join(promotion_path)}"] if promotion_path else [],
        [f"职业意向与岗位方向对齐度：{round(career_alignment, 2)}"] if career_alignment else [],
        student.extracted_evidence.get("learning", []),
        student.extracted_evidence.get("innovation", []),
    )
    explanation = "具备一定成长空间和迁移潜力" if score >= 65.0 else "成长潜力偏弱，需先补齐画像完整度或关键能力"
    return MatchDimensionDetail(
        score=score,
        matched=score >= 60.0,
        explanation=explanation,
        evidence=evidence,
        gaps=unique_keep_order(gaps),
        unmet_items=unique_keep_order(gaps),
        details={
            "current_capacity": round(current_capacity, 2),
            "transferability": round(transferability, 2),
            "growth_space": round(growth_space, 2),
            "career_alignment": round(career_alignment, 2),
            "promotion_path": promotion_path,
        },
    )



def calculate_total_score(weights: MatchingWeights | None, dimension_scores: dict[str, float]) -> float:
    normalized = (weights or MatchingWeights()).normalized()
    total = 0.0
    for key, weight in normalized.items():
        total += clamp_score(dimension_scores.get(key, 0.0)) * weight
    return clamp_score(total)



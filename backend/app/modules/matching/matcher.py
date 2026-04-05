from __future__ import annotations

from app.modules.matching.config import (
    LOW_JOB_CONFIDENCE_THRESHOLD,
    LOW_STUDENT_COMPLETENESS_THRESHOLD,
    MATCH_PASSING_SCORE,
)
from app.modules.matching.scorer import (
    calculate_total_score,
    score_base_requirement,
    score_growth_potential,
    score_skill_match,
    score_soft_skill_match,
)
from app.modules.matching.schema import (
    JobMatchProfile,
    JobMatchResult,
    JobRequirementSnapshot,
    MatchDimensionDetail,
    MatchDimensionScores,
    MatchingWeights,
    StudentCapabilitySnapshot,
    StudentMatchProfile,
)
from app.modules.matching.utils import summarize_snippets, unique_keep_order

CATEGORY_ORDER = ("match", "stretch", "safe")



def _sort_key(result: JobMatchResult) -> tuple[float, float, float, int]:
    return (
        -result.total_score,
        -result.dimension_scores.skill,
        -result.dimension_scores.base_requirement,
        result.job_profile_id,
    )



def _missing_skills(detail: MatchDimensionDetail, field_name: str) -> list[str]:
    if not isinstance(detail.details, dict):
        return []
    return unique_keep_order(detail.details.get(field_name, []))



def classify_match_category(result: JobMatchResult) -> str | None:
    if result.total_score > 90:
        return "safe"
    if result.total_score >= 75:
        return "match"
    if result.total_score >= 60:
        return "stretch"
    return None



def _build_gap_analysis(
    base_detail: MatchDimensionDetail,
    skill_detail: MatchDimensionDetail,
    soft_skill_detail: MatchDimensionDetail,
    growth_detail: MatchDimensionDetail,
) -> list[str]:
    missing_must = _missing_skills(skill_detail, "missing_must_skills")
    missing_nice = _missing_skills(skill_detail, "missing_nice_skills")

    gaps: list[str] = []
    gaps.extend(base_detail.gaps)
    gaps.extend(f"缺少核心技能：{skill}" for skill in missing_must)
    if missing_must:
        gaps.append("建议优先通过课程项目、实习或作品集补齐 must_have 技能证据")
    gaps.extend(f"缺少加分技能：{skill}" for skill in missing_nice[:3])
    if missing_nice:
        gaps.append("建议补充 1-2 项 nice_to_have 技能，进一步提高竞争力")
    gaps.extend(soft_skill_detail.gaps)
    if soft_skill_detail.score < 60:
        gaps.append("建议补充能体现沟通、协作或抗压表现的经历证据")
    gaps.extend(growth_detail.gaps)
    if growth_detail.score < 60:
        gaps.append("建议先提升画像完整度，并补充项目或实习成果")

    return unique_keep_order(gaps)[:8]



def _build_risk_flags(
    student: StudentMatchProfile,
    job: JobMatchProfile,
    base_detail: MatchDimensionDetail,
    skill_detail: MatchDimensionDetail,
) -> list[str]:
    missing_must = _missing_skills(skill_detail, "missing_must_skills")
    risks: list[str] = []

    if not base_detail.matched:
        risks.append("存在基础门槛未满足项，进入筛选环节的风险较高")
    if missing_must:
        risks.append(f"缺失 must_have 技能：{'、'.join(missing_must)}")
    if student.completeness_score < LOW_STUDENT_COMPLETENESS_THRESHOLD:
        risks.append("学生画像完整度较低，当前推荐置信度下降")
    if job.confidence_score < LOW_JOB_CONFIDENCE_THRESHOLD * 100:
        risks.append("岗位画像置信度较低（confidence_score 低），建议结合原始 JD 复核")

    return unique_keep_order(risks)



def _category_explanation(category: str | None, result: JobMatchResult) -> str:
    missing_must = _missing_skills(result.dimension_details["skill"], "missing_must_skills")
    if category == "safe":
        return "归类为保底岗：总分超过 90，基础要求和核心技能基本完全匹配。"
    if category == "match":
        return "归类为匹配岗：总分在 75-90，技能匹配度较高且整体风险较低。"
    if category == "stretch":
        if missing_must:
            return "归类为冲刺岗：总分在 60-75，仍有明显能力差距，但发展潜力可支撑冲刺。"
        return "归类为冲刺岗：总分在 60-75，当前能力尚需补强，但仍具备成长空间。"
    return "当前总分未进入推荐分层，建议作为低优先级备选岗位。"



def _build_reason(
    job: JobMatchProfile,
    dimension_scores: MatchDimensionScores,
    matched: bool,
    skill_detail: MatchDimensionDetail,
    category: str | None,
) -> str:
    label_map = {
        "base_requirement": "基础要求",
        "skill": "职业技能",
        "soft_skill": "职业素养",
        "growth": "发展潜力",
    }
    strongest_dimension = max(dimension_scores.model_dump().items(), key=lambda item: item[1])[0]
    weakest_dimension = min(dimension_scores.model_dump().items(), key=lambda item: item[1])[0]
    missing_must = _missing_skills(skill_detail, "missing_must_skills")

    if matched and not missing_must:
        base_reason = f"{job.job_title}整体匹配度较高，{label_map[strongest_dimension]}表现较强。"
    elif missing_must:
        base_reason = f"{job.job_title}存在投递价值，但核心技能仍缺少{'、'.join(missing_must)}。"
    else:
        base_reason = f"{job.job_title}可作为候选岗位，当前短板主要在{label_map[weakest_dimension]}。"
    return f"{base_reason}{_category_explanation(category, JobMatchResult(job_id=job.job_id, job_profile_id=job.job_profile_id, job_title=job.job_title, total_score=0, dimension_scores=dimension_scores, matched=matched, reason='', gap_analysis=[], evidence=[], risk_flags=[], dimension_details={'skill': skill_detail}, weight_config=MatchingWeights()))}"



def _build_reason_with_result(
    job: JobMatchProfile,
    dimension_scores: MatchDimensionScores,
    matched: bool,
    skill_detail: MatchDimensionDetail,
    category: str | None,
) -> str:
    label_map = {
        "base_requirement": "基础要求",
        "skill": "职业技能",
        "soft_skill": "职业素养",
        "growth": "发展潜力",
    }
    strongest_dimension = max(dimension_scores.model_dump().items(), key=lambda item: item[1])[0]
    weakest_dimension = min(dimension_scores.model_dump().items(), key=lambda item: item[1])[0]
    missing_must = _missing_skills(skill_detail, "missing_must_skills")

    if matched and not missing_must:
        base_reason = f"{job.job_title}整体匹配度较高，{label_map[strongest_dimension]}表现较强。"
    elif missing_must:
        base_reason = f"{job.job_title}存在投递价值，但核心技能仍缺少{'、'.join(missing_must)}。"
    else:
        base_reason = f"{job.job_title}可作为候选岗位，当前短板主要在{label_map[weakest_dimension]}。"
    dummy_result = JobMatchResult(
        job_id=job.job_id,
        job_profile_id=job.job_profile_id,
        job_title=job.job_title,
        total_score=dimension_scores.base_requirement,
        dimension_scores=dimension_scores,
        matched=matched,
        reason="",
        gap_analysis=[],
        evidence=[],
        risk_flags=[],
        dimension_details={"skill": skill_detail},
        weight_config=MatchingWeights(),
    )
    return f"{base_reason}{_category_explanation(category, dummy_result)}"



def _build_evidence(
    student: StudentMatchProfile,
    job: JobMatchProfile,
    base_detail: MatchDimensionDetail,
    skill_detail: MatchDimensionDetail,
    soft_skill_detail: MatchDimensionDetail,
    growth_detail: MatchDimensionDetail,
) -> list[str]:
    matched_must = [
        f"命中核心技能：{item['required_skill']} <- {item['matched_skill']}"
        for item in skill_detail.details.get("must_matches", [])
        if item.get("matched")
    ]
    matched_nice = [
        f"命中加分技能：{item['required_skill']} <- {item['matched_skill']}"
        for item in skill_detail.details.get("nice_matches", [])
        if item.get("matched")
    ]
    return summarize_snippets(
        matched_must,
        matched_nice,
        base_detail.evidence,
        skill_detail.evidence,
        soft_skill_detail.evidence,
        growth_detail.evidence,
        student.extracted_evidence.get("summary", []),
        job.extracted_evidence.get("summary", []),
        limit=8,
    )



def _infer_job_requirement_snapshot(job: JobMatchProfile) -> JobRequirementSnapshot:
    title_corpus = f"{job.job_title} {job.job_level} {job.summary}".lower()
    innovation = 55.0
    learning = 60.0
    stress = 55.0
    communication = 55.0
    internship = 45.0 if job.internship_requirement == "未明确" else 65.0

    for skill in job.soft_skills:
        if any(marker in skill for marker in ("沟通", "表达", "协作", "团队")):
            communication = max(communication, 75.0)
        if any(marker in skill for marker in ("学习", "自驱", "主动")):
            learning = max(learning, 75.0)
        if any(marker in skill for marker in ("抗压", "承压")):
            stress = max(stress, 75.0)
        if any(marker in skill for marker in ("创新", "逻辑")):
            innovation = max(innovation, 72.0)
        if any(marker in skill for marker in ("执行", "责任")):
            internship = max(internship, 72.0)

    if any(marker in title_corpus for marker in ("高级", "资深", "专家", "架构", "负责人", "经理", "总监")):
        communication = max(communication, 78.0)
        stress = max(stress, 72.0)
        learning = max(learning, 70.0)
    if any(marker in title_corpus for marker in ("实习", "校招", "应届")):
        learning = max(learning, 68.0)
        internship = max(internship, 60.0)

    return JobRequirementSnapshot(
        must_have_skills=job.must_have_skills,
        certificates=job.certificates,
        innovation_requirement=innovation,
        learning_requirement=learning,
        stress_tolerance_requirement=stress,
        communication_requirement=communication,
        internship_requirement=internship,
        promotion_path=job.promotion_path,
    )


def _build_student_capability_snapshot(student: StudentMatchProfile) -> StudentCapabilitySnapshot:
    return StudentCapabilitySnapshot(
        professional_skills=student.professional_skills,
        certificates=student.certificates,
        innovation_score=student.innovation_score,
        learning_score=student.learning_score,
        stress_tolerance_score=student.stress_score,
        communication_score=student.communication_score,
        internship_score=student.internship_score,
        completeness_score=student.completeness_score,
        competitiveness_score=student.competitiveness_score,
    )


def _serialize_result(result: JobMatchResult) -> dict[str, object]:
    payload = result.model_dump(mode="json")
    payload["category"] = classify_match_category(result)
    return payload



def match_student_to_job(
    student: StudentMatchProfile,
    job: JobMatchProfile,
    weights: MatchingWeights | None = None,
) -> JobMatchResult:
    effective_weights = weights or MatchingWeights()
    base_detail = score_base_requirement(student, job)
    skill_detail = score_skill_match(student, job)
    soft_skill_detail = score_soft_skill_match(student, job)
    growth_detail = score_growth_potential(student, job, skill_detail, soft_skill_detail)

    dimension_scores = MatchDimensionScores(
        base_requirement=base_detail.score,
        skill=skill_detail.score,
        soft_skill=soft_skill_detail.score,
        growth=growth_detail.score,
    )
    total_score = calculate_total_score(effective_weights, dimension_scores.model_dump())
    matched = base_detail.matched and total_score >= MATCH_PASSING_SCORE

    provisional = JobMatchResult(
        job_id=job.job_id,
        job_profile_id=job.job_profile_id,
        job_title=job.job_title,
        total_score=total_score,
        dimension_scores=dimension_scores,
        matched=matched,
        reason="",
        gap_analysis=_build_gap_analysis(base_detail, skill_detail, soft_skill_detail, growth_detail),
        evidence=_build_evidence(student, job, base_detail, skill_detail, soft_skill_detail, growth_detail),
        risk_flags=_build_risk_flags(student, job, base_detail, skill_detail),
        dimension_details={
            "base_requirement": base_detail,
            "skill": skill_detail,
            "soft_skill": soft_skill_detail,
            "growth": growth_detail,
        },
        job_requirement_snapshot=_infer_job_requirement_snapshot(job),
        student_capability_snapshot=_build_student_capability_snapshot(student),
        weight_config=effective_weights,
    )
    category = classify_match_category(provisional)
    provisional.reason = _build_reason_with_result(job, dimension_scores, matched, skill_detail, category)
    return provisional



def rank_jobs_for_student(
    student: StudentMatchProfile,
    jobs: list[JobMatchProfile],
    top_k: int,
    weights: MatchingWeights | None = None,
) -> list[JobMatchResult]:
    results = [match_student_to_job(student, job, weights=weights) for job in jobs]
    results.sort(key=_sort_key)
    return results[:top_k]



def group_top_k_jobs_for_student(
    student: StudentMatchProfile,
    jobs: list[JobMatchProfile],
    top_k: int,
    weights: MatchingWeights | None = None,
) -> dict[str, list[dict[str, object]]]:
    ranked_results = [match_student_to_job(student, job, weights=weights) for job in jobs]
    ranked_results.sort(key=_sort_key)

    pools: dict[str, list[JobMatchResult]] = {key: [] for key in CATEGORY_ORDER}
    for result in ranked_results:
        category = classify_match_category(result)
        if category is None:
            continue
        pools[category].append(result)

    non_empty_categories = [category for category in CATEGORY_ORDER if pools[category]]
    target_count = max(top_k, len(non_empty_categories))
    selected_ids: set[int] = set()
    selected: list[JobMatchResult] = []

    for category in CATEGORY_ORDER:
        if not pools[category]:
            continue
        first = pools[category][0]
        selected.append(first)
        selected_ids.add(id(first))

    remaining = [
        result
        for result in ranked_results
        if classify_match_category(result) in pools and classify_match_category(result) is not None and id(result) not in selected_ids
    ]
    for result in remaining:
        if len(selected) >= target_count:
            break
        selected.append(result)
        selected_ids.add(id(result))

    grouped: dict[str, list[dict[str, object]]] = {"match": [], "stretch": [], "safe": []}
    for result in selected:
        category = classify_match_category(result)
        if category is None:
            continue
        grouped[category].append(_serialize_result(result))

    for category in grouped:
        grouped[category].sort(
            key=lambda item: (
                -float(item["total_score"]),
                -float(item["dimension_scores"]["skill"]),
                -float(item["dimension_scores"]["base_requirement"]),
                int(item["job_profile_id"]),
            )
        )
    return grouped

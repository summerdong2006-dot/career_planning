from __future__ import annotations

from app.modules.matching.config import LOW_JOB_CONFIDENCE_THRESHOLD, LOW_STUDENT_COMPLETENESS_THRESHOLD, MATCH_PASSING_SCORE
from app.modules.matching.schema import JobMatchProfile, MatchDimensionDetail, MatchDimensionScores, StudentMatchProfile
from app.modules.matching.utils import summarize_snippets, unique_keep_order



def generate_gap_analysis(
    base_detail: MatchDimensionDetail,
    skill_detail: MatchDimensionDetail,
    soft_skill_detail: MatchDimensionDetail,
    growth_detail: MatchDimensionDetail,
) -> list[str]:
    return unique_keep_order(
        base_detail.gaps
        + skill_detail.gaps
        + soft_skill_detail.gaps
        + growth_detail.gaps
    )[:8]



def build_match_reason(job: JobMatchProfile, scores: MatchDimensionScores, matched: bool) -> str:
    strongest_dimension = max(scores.model_dump().items(), key=lambda item: item[1])[0]
    label_map = {
        "base_requirement": "基础要求",
        "skill": "职业技能",
        "soft_skill": "职业素养",
        "growth": "发展潜力",
    }
    if matched:
        return f"{job.job_title}推荐度较高，{label_map[strongest_dimension]}表现最强。"
    return f"{job.job_title}存在投递机会，但{label_map[strongest_dimension]}之外仍有明显短板。"



def build_risk_flags(
    student: StudentMatchProfile,
    job: JobMatchProfile,
    base_detail: MatchDimensionDetail,
    total_score: float,
) -> list[str]:
    risks: list[str] = []
    if not base_detail.matched:
        risks.append("存在基础门槛未满足项，进入面试或简历筛选的概率较低")
    if job.confidence_score < LOW_JOB_CONFIDENCE_THRESHOLD * 100:
        risks.append("岗位画像置信度较低，推荐结果需结合原始 JD 复核")
    if student.completeness_score < LOW_STUDENT_COMPLETENESS_THRESHOLD:
        risks.append("学生画像完整度较低，建议补充项目、实习或证据后再评估")
    if total_score < MATCH_PASSING_SCORE:
        risks.append("总分未达到推荐阈值，建议作为保守备选岗位")
    return unique_keep_order(risks)



def build_match_evidence(
    student: StudentMatchProfile,
    job: JobMatchProfile,
    base_detail: MatchDimensionDetail,
    skill_detail: MatchDimensionDetail,
    soft_skill_detail: MatchDimensionDetail,
    growth_detail: MatchDimensionDetail,
) -> list[str]:
    return summarize_snippets(
        base_detail.evidence,
        skill_detail.evidence,
        soft_skill_detail.evidence,
        growth_detail.evidence,
        student.extracted_evidence.get("summary", []),
        job.extracted_evidence.get("summary", []),
        limit=8,
    )


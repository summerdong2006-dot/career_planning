from __future__ import annotations

import json

from app.modules.job_profile.profile_schema import EVIDENCE_FIELD_NAMES, JOB_PROFILE_FIELD_NAMES, JobProfileSourceRecord


SYSTEM_PROMPT = """你是岗位画像抽取器。只能输出固定 JSON，不能新增字段，不能输出 Markdown。

要求：
1. 只使用以下字段名：job_title, job_level, education_requirement, years_experience_requirement,
   must_have_skills, nice_to_have_skills, certificates, soft_skills, internship_requirement,
   industry_tags, promotion_path, summary, extracted_evidence, confidence_score。
2. summary 必须始终输出字符串，缺失时返回“未明确”，不能输出数组、对象或 null。
3. extracted_evidence 必须始终输出对象，键固定为：job_title, job_level, education_requirement,
   years_experience_requirement, must_have_skills, nice_to_have_skills, certificates, soft_skills,
   internship_requirement, industry_tags, promotion_path, summary。
4. extracted_evidence 中每个键对应的值必须始终是数组；没有证据时返回 []。
5. 字段不确定时，文本字段填“未明确”，数组字段填 []，confidence_score 输出 0 到 1 的数字。
6. 不要编造不存在的证据，无法确认就返回空数组。
"""


def build_job_profile_prompt(source: JobProfileSourceRecord) -> str:
    payload = {
        "allowed_fields": JOB_PROFILE_FIELD_NAMES,
        "evidence_fields": EVIDENCE_FIELD_NAMES,
        "input_job": source.model_dump(),
    }
    return (
        "请基于岗位标题、岗位描述、行业、企业介绍抽取结构化岗位画像。"
        "必须严格输出 JSON 对象，字段名固定，字段类型也必须固定。\n\n"
        f"输入数据：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

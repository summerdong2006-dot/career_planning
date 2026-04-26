from __future__ import annotations

import asyncio
import json
from pathlib import Path
from sqlalchemy import text
from app.db.session import SessionLocal

ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "processed" / "jobs_computer_with_text_v2.json"

def s(v, default="", max_len=None):
    v = default if v is None else str(v)
    return v[:max_len] if max_len else v

def j(v, default=None):
    if v is None:
        v = [] if default is None else default
    return json.dumps(v, ensure_ascii=False)

async def main():
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))
    records = payload.get("records", payload if isinstance(payload, list) else [])
    print(f"Loaded records: {len(records)}")

    async with SessionLocal() as db:
        await db.execute(text("TRUNCATE TABLE job_import_batches RESTART IDENTITY CASCADE;"))

        batch_id = (await db.execute(text("""
            INSERT INTO job_import_batches
            (batch_name, source_file, source_format, total_records, raw_records, unique_records,
             duplicate_records, invalid_records, status)
            VALUES
            (:batch_name, :source_file, 'json', :n, :n, :n, 0, 0, 'completed')
            RETURNING id
        """), {
            "batch_name": "computer_jobs_import",
            "source_file": str(DATA_FILE),
            "n": len(records),
        })).scalar_one()

        for i, r in enumerate(records, start=1):
            position_name = s(r.get("position_name") or r.get("title") or r.get("job_title") or f"岗位{i}", max_len=255)
            company = s(r.get("company_full_name") or r.get("company") or "未知公司", max_len=255)
            city = s(r.get("work_city") or r.get("city") or "未知城市", max_len=128)
            address = s(r.get("work_address") or r.get("location") or city, max_len=255)
            salary = s(r.get("salary_range") or "面议", max_len=255)
            desc = s(r.get("job_description") or r.get("description") or r.get("text") or r.get("embedding_text") or "")
            tags = r.get("job_tags") or r.get("required_skills") or r.get("skills") or []

            raw_id = (await db.execute(text("""
                INSERT INTO job_postings_raw
                (batch_id, source_row_number, position_name, work_address, salary_range,
                 company_full_name, industry, company_size, company_type, job_code,
                 job_description, company_intro, raw_payload, clean_status)
                VALUES
                (:batch_id, :source_row_number, :position_name, :work_address, :salary_range,
                 :company_full_name, :industry, :company_size, :company_type, :job_code,
                 :job_description, :company_intro, CAST(:raw_payload AS JSON), 'cleaned')
                RETURNING id
            """), {
                "batch_id": batch_id,
                "source_row_number": int(r.get("source_row_number") or i),
                "position_name": position_name,
                "work_address": address,
                "salary_range": salary,
                "company_full_name": company,
                "industry": s(r.get("industry") or "互联网", max_len=255),
                "company_size": s(r.get("company_size") or "未知", max_len=255),
                "company_type": s(r.get("company_type") or "未知", max_len=255),
                "job_code": s(r.get("job_code") or f"JOB-{i}", max_len=255),
                "job_description": desc,
                "company_intro": s(r.get("company_intro") or "暂无公司介绍"),
                "raw_payload": json.dumps(r, ensure_ascii=False),
            })).scalar_one()

            clean_id = (await db.execute(text("""
                INSERT INTO job_postings_clean
                (batch_id, source_raw_id, canonical_key, position_name, position_name_normalized,
                 job_category, work_city, work_address, salary_range, salary_min_monthly,
                 salary_max_monthly, salary_pay_months, salary_unit, company_full_name,
                 company_name_normalized, industry, company_size, company_type, job_code,
                 job_code_generated, job_description, company_intro, job_tags)
                VALUES
                (:batch_id, :source_raw_id, :canonical_key, :position_name, :position_name_normalized,
                 :job_category, :work_city, :work_address, :salary_range, :salary_min_monthly,
                 :salary_max_monthly, :salary_pay_months, :salary_unit, :company_full_name,
                 :company_name_normalized, :industry, :company_size, :company_type, :job_code,
                 false, :job_description, :company_intro, CAST(:job_tags AS JSON))
                RETURNING id
            """), {
                "batch_id": batch_id,
                "source_raw_id": raw_id,
                "canonical_key": s(r.get("canonical_key") or f"job-{i}", max_len=64),
                "position_name": position_name,
                "position_name_normalized": s(r.get("position_name_normalized") or position_name, max_len=255),
                "job_category": s(r.get("job_category") or "计算机相关岗位", max_len=64),
                "work_city": city,
                "work_address": address,
                "salary_range": salary,
                "salary_min_monthly": int(r.get("salary_min_monthly") or 0),
                "salary_max_monthly": int(r.get("salary_max_monthly") or 0),
                "salary_pay_months": int(r.get("salary_pay_months") or 12),
                "salary_unit": s(r.get("salary_unit") or "月", max_len=32),
                "company_full_name": company,
                "company_name_normalized": s(r.get("company_name_normalized") or company, max_len=255),
                "industry": s(r.get("industry") or "互联网", max_len=255),
                "company_size": s(r.get("company_size") or "未知", max_len=64),
                "company_type": s(r.get("company_type") or "未知", max_len=64),
                "job_code": s(r.get("job_code") or f"JOB-{i}", max_len=255),
                "job_description": desc,
                "company_intro": s(r.get("company_intro") or "暂无公司介绍"),
                "job_tags": j(tags),
            })).scalar_one()

            await db.execute(text("""
                INSERT INTO job_posting_profiles
                (batch_id, source_clean_id, job_title, job_level, education_requirement,
                 years_experience_requirement, must_have_skills, nice_to_have_skills,
                 certificates, soft_skills, internship_requirement, industry_tags,
                 promotion_path, summary, extracted_evidence, confidence_score,
                 extractor_name, extractor_version, raw_profile_payload)
                VALUES
                (:batch_id, :source_clean_id, :job_title, '初级/通用', '本科及以上',
                 '不限', CAST(:must AS JSON), CAST(:nice AS JSON),
                 CAST(:cert AS JSON), CAST(:soft AS JSON), '不限', CAST(:industry_tags AS JSON),
                 CAST(:promotion_path AS JSON), :summary, CAST(:evidence AS JSON), 0.80,
                 'manual_import', 'v1', CAST(:raw AS JSON))
            """), {
                "batch_id": batch_id,
                "source_clean_id": clean_id,
                "job_title": position_name,
                "must": j(tags or ["Python", "SQL", "沟通能力"]),
                "nice": j(r.get("nice_to_have_skills") or []),
                "cert": j([]),
                "soft": j(["沟通能力", "学习能力", "团队协作"]),
                "industry_tags": j([r.get("industry") or "互联网"]),
                "promotion_path": j(["初级岗位", "中级岗位", "高级岗位"]),
                "summary": desc[:500] if desc else f"{position_name}岗位画像",
                "evidence": j({"source": "jobs_computer_with_text_v2.json"}),
                "raw": json.dumps(r, ensure_ascii=False),
            })

        await db.commit()

    print("Import done.")

if __name__ == "__main__":
    asyncio.run(main())

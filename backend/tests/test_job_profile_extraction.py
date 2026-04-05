from types import SimpleNamespace

from app.modules.job_profile.parser import normalize_profile_payload
from app.modules.job_profile.profile_schema import JobProfileSourceRecord
from app.modules.job_profile.profile_service import extract_job_profile_from_source, extract_job_profiles_batch


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalars(self._rows)


class _FakeBatchSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, _statement):
        return _FakeResult(self._rows)


async def test_extract_job_profile_normal_description():
    source = JobProfileSourceRecord(
        position_name="Python开发工程师",
        job_category="后端开发",
        work_city="上海市",
        salary_range="15K-25K·14薪",
        company_full_name="上海星云数据科技有限公司",
        industry="人工智能/大数据",
        job_description="负责Python服务开发与数据处理，熟悉FastAPI和SQL，本科及以上学历，1-3年开发经验，有云原生经验优先，具备良好的沟通能力和团队协作能力。",
        company_intro="聚焦企业数据智能平台建设。",
        job_tags=["Python", "后端", "SQL"],
    )

    profile, raw_payload, extractor_name = await extract_job_profile_from_source(source)

    assert extractor_name == "heuristic"
    assert profile.job_title == "Python开发工程师"
    assert profile.education_requirement == "本科"
    assert profile.years_experience_requirement == "1-3年"
    assert "Python" in profile.must_have_skills
    assert "FastAPI" in profile.must_have_skills
    assert "SQL" in profile.must_have_skills
    assert "Docker" in profile.nice_to_have_skills
    assert "沟通能力" in profile.soft_skills
    assert isinstance(profile.summary, str)
    assert isinstance(profile.extracted_evidence.model_dump(), dict)
    assert raw_payload["job_title"] == "Python开发工程师"


async def test_extract_job_profile_with_missing_fields_returns_stable_defaults():
    source = JobProfileSourceRecord(
        position_name="实施工程师",
        company_full_name="广东南方数码科技股份有限公司",
        industry="计算机软件",
        job_description="",
        company_intro="",
        job_tags=[],
    )

    profile, _, _ = await extract_job_profile_from_source(source)

    assert profile.job_title == "实施工程师"
    assert profile.job_level == "未明确"
    assert profile.education_requirement == "未明确"
    assert profile.years_experience_requirement == "未明确"
    assert profile.internship_requirement == "未明确"
    assert profile.must_have_skills == []
    assert profile.nice_to_have_skills == []
    assert profile.certificates == []
    assert profile.soft_skills == []
    assert isinstance(profile.summary, str)
    assert profile.extracted_evidence.model_dump()["education_requirement"] == []
    assert 0.15 <= profile.confidence_score <= 0.65


async def test_extract_job_profile_handles_long_description():
    long_description = (
        "负责机器学习平台建设，熟悉Python、SQL、PyTorch、TensorFlow，硕士及以上学历，3年以上算法经验，"
        "具备良好的沟通协调能力和跨团队协作能力，有大模型项目经验优先。" * 8
    )
    source = JobProfileSourceRecord(
        position_name="算法工程师",
        job_category="算法/AI",
        company_full_name="杭州智算科技有限公司",
        industry="人工智能/企业服务",
        job_description=long_description,
        company_intro="为企业提供大模型解决方案。",
        job_tags=["AI"],
    )

    profile, _, _ = await extract_job_profile_from_source(source)

    assert profile.education_requirement == "硕士"
    assert profile.years_experience_requirement == "3年以上"
    assert "Python" in profile.must_have_skills
    assert "PyTorch" in profile.must_have_skills
    assert "TensorFlow" in profile.must_have_skills
    assert "大模型" in profile.nice_to_have_skills
    assert isinstance(profile.summary, str)
    assert profile.extracted_evidence.years_experience_requirement


async def test_extract_job_profile_handles_messy_description_structure():
    source = JobProfileSourceRecord(
        position_name="前端开发工程师",
        job_category="前端开发",
        company_full_name="北京智联云科有限公司",
        industry="互联网",
        job_description="【岗位】前端开发工程师 | 本科；1-3年；React/Vue/JavaScript；有数据可视化经验优先；沟通协调、团队合作；",
        company_intro="提供行业信息化解决方案。",
        job_tags=["前端"],
    )

    profile, _, _ = await extract_job_profile_from_source(source)

    assert profile.education_requirement == "本科"
    assert profile.years_experience_requirement == "1-3年"
    assert "React" in profile.must_have_skills or "Vue" in profile.must_have_skills
    assert "沟通能力" in profile.soft_skills or "团队协作" in profile.soft_skills
    assert profile.promotion_path
    assert profile.extracted_evidence.must_have_skills


def test_normalize_profile_payload_enforces_summary_and_evidence_types():
    source = JobProfileSourceRecord(position_name="数据分析师")
    payload = {
        "summary": ["负责业务指标分析与BI建设"],
        "job_level": [],
        "education_requirement": None,
        "must_have_skills": None,
        "soft_skills": "沟通能力,团队协作",
        "extracted_evidence": {
            "summary": "原始摘要证据",
            "job_level": "",
            "must_have_skills": None,
            "soft_skills": "具备良好的沟通能力和团队协作能力",
        },
        "confidence_score": "0.66",
    }

    normalized = normalize_profile_payload(payload, source)
    evidence = normalized.extracted_evidence.model_dump()

    assert isinstance(normalized.summary, str)
    assert normalized.summary == "负责业务指标分析与BI建设"
    assert normalized.job_level == "未明确"
    assert normalized.education_requirement == "未明确"
    assert normalized.must_have_skills == []
    assert normalized.soft_skills == ["沟通能力", "团队协作"]
    assert isinstance(evidence, dict)
    assert all(isinstance(value, list) for value in evidence.values())
    assert evidence["summary"] == ["原始摘要证据"]
    assert evidence["job_level"] == []
    assert normalized.confidence_score == 0.66


async def test_single_and_batch_outputs_share_the_same_item_schema():
    source = JobProfileSourceRecord(
        source_clean_id=101,
        batch_id=9,
        position_name="数据分析师",
        company_full_name="深圳数图科技股份有限公司",
        industry="企业服务/数据服务",
        job_description="负责业务指标分析和BI报表建设，熟悉SQL，本科及以上学历。",
        job_tags=["SQL"],
    )
    single_profile, raw_payload, extractor_name = await extract_job_profile_from_source(source)

    fake_row = SimpleNamespace(
        id=101,
        batch_id=9,
        canonical_key="demo-key",
        position_name="数据分析师",
        position_name_normalized="数据分析师",
        job_category="数据分析",
        work_city="深圳市",
        salary_range="15K-20K",
        company_full_name="深圳数图科技股份有限公司",
        industry="企业服务/数据服务",
        job_description="负责业务指标分析和BI报表建设，熟悉SQL，本科及以上学历。",
        company_intro="数据驱动型企业服务厂商。",
        job_tags=["SQL"],
    )
    batch_result = await extract_job_profiles_batch(
        session=_FakeBatchSession([fake_row]),
        batch_id=9,
        limit=1,
        persist=False,
    )

    single_item = {
        "source_clean_id": source.source_clean_id,
        "batch_id": source.batch_id,
        "extractor_name": extractor_name,
        "extractor_version": "v1",
        "persisted": False,
        "profile": single_profile.model_dump(mode="json"),
        "raw_profile_payload": raw_payload,
    }
    batch_item = batch_result.items[0].model_dump(mode="json")

    assert set(single_item.keys()) == set(batch_item.keys())
    assert set(single_item["profile"].keys()) == set(batch_item["profile"].keys())
    assert isinstance(batch_item["profile"]["summary"], str)
    assert isinstance(batch_item["profile"]["extracted_evidence"], dict)
    assert all(isinstance(value, list) for value in batch_item["profile"]["extracted_evidence"].values())

from app.modules.reporting.schema import CareerReportContent, CareerReportMeta, CareerReportSection, _normalize_meta


def test_normalize_meta_supports_dict_meta():
    payload = {
        "meta": {
            "student_id": "test_001",
            "target_job": "backend engineer",
            "generated_at": "2026-03-25",
        }
    }

    normalized = _normalize_meta(payload)

    assert normalized == {
        "student_id": "test_001",
        "target_job": "backend engineer",
        "generated_at": "2026-03-25",
    }


def test_normalize_meta_supports_pydantic_meta_model():
    payload = {
        "meta": CareerReportMeta(
            student_id="test_002",
            target_job="data engineer",
            generated_at="2026-03-24",
        )
    }

    normalized = _normalize_meta(payload)

    assert normalized == {
        "student_id": "test_002",
        "target_job": "data engineer",
        "generated_at": "2026-03-24",
    }


def test_career_report_content_supports_pydantic_meta_and_sections():
    content = CareerReportContent(
        meta=CareerReportMeta(
            student_id="test_003",
            target_job="ml engineer",
            generated_at="2026-03-25",
        ),
        sections=[
            CareerReportSection(
                key="summary",
                title="Overall Summary",
                content="Candidate has solid Python fundamentals.",
            )
        ],
    )

    assert content.meta.student_id == "test_003"
    assert content.meta.target_job == "ml engineer"
    assert content.sections == [
        CareerReportSection(
            key="summary",
            title="Overall Summary",
            content="Candidate has solid Python fundamentals.",
        )
    ]

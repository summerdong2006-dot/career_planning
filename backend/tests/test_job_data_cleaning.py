from app.modules.job_profile.cleaning import (
    clean_job_record,
    parse_salary_range,
    project_source_record,
)


def test_project_source_record_maps_aliases():
    raw_record = {
        "职位名称": "Python开发工程师",
        "工作地点": "上海市浦东新区",
        "薪资": "15K-25K·14薪",
        "公司名称": "上海星云数据科技有限公司",
        "行业": "人工智能",
        "企业规模": "200人",
        "公司性质": "民营",
        "岗位描述": "Python API 开发",
    }

    projected = project_source_record(raw_record, source_row_number=1)

    assert projected.position_name == "Python开发工程师"
    assert projected.work_address == "上海市浦东新区"
    assert projected.salary_range == "15K-25K·14薪"
    assert projected.company_full_name == "上海星云数据科技有限公司"
    assert projected.company_size == "200人"
    assert projected.company_type == "民营"



def test_parse_salary_range_supports_annual_salary():
    salary = parse_salary_range("20-30万/年")

    assert salary.salary_min_monthly == 16667
    assert salary.salary_max_monthly == 25000
    assert salary.salary_unit == "yearly"
    assert salary.salary_pay_months == 12



def test_clean_job_record_generates_defaults_and_tags():
    projected = project_source_record(
        {
            "职位名称": "前端开发工程师",
            "工作地址": "北京市海淀区",
            "薪资范围": "18K-30K",
            "公司全称": "北京智联云科有限公司",
            "所属行业": "互联网",
            "人员规模": "500-999人",
            "企业性质": "上市公司",
            "职位描述": "负责 React 前端开发与性能优化",
        },
        source_row_number=2,
    )

    cleaned, issues = clean_job_record(projected)

    assert cleaned.work_city == "北京市"
    assert cleaned.job_category == "前端开发"
    assert "前端" in cleaned.job_tags
    assert "generated_job_code" in {issue.code for issue in issues}
    assert cleaned.salary_min_monthly == 18000
    assert cleaned.salary_max_monthly == 30000



def test_clean_job_record_dedup_key_uses_source_job_code():
    first, _ = clean_job_record(
        project_source_record(
            {
                "职位名称": "Python开发工程师",
                "工作地址": "上海市浦东新区",
                "薪资范围": "15K-25K",
                "公司全称": "上海星云数据科技有限公司",
                "职位编码": "DEV-1001",
            },
            source_row_number=1,
        )
    )
    second, _ = clean_job_record(
        project_source_record(
            {
                "职位名称": "Python开发工程师",
                "工作地址": "上海浦东",
                "薪资范围": "15K-25K",
                "公司全称": "上海星云数据科技有限公司",
                "职位编码": "DEV-1001",
            },
            source_row_number=2,
        )
    )

    assert first.canonical_key == second.canonical_key

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from app.modules.job_profile.data_loader import normalize_field_name

EMPTY_TEXT = ""
UNKNOWN_TEXT = "未知"
UNKNOWN_CITY = "未知城市"
UNKNOWN_JOB = "未知岗位"
UNKNOWN_COMPANY = "未知企业"

FIELD_ALIASES = {
    "position_name": ["职位名称", "岗位名称", "职位", "岗位", "positionname", "jobtitle", "title", "jobname"],
    "work_address": ["工作地址", "工作地点", "地址", "城市", "location", "workaddress", "address"],
    "salary_range": ["薪资范围", "薪资", "工资范围", "salaryrange", "salary", "compensation"],
    "company_full_name": ["公司全称", "公司名称", "企业名称", "companyfullname", "companyname", "company", "employer"],
    "industry": ["所属行业", "行业", "industry"],
    "company_size": ["人员规模", "公司规模", "企业规模", "companysize", "size"],
    "company_type": ["企业性质", "公司性质", "企业类型", "companytype", "ownership"],
    "job_code": ["职位编码", "岗位编码", "职位编号", "岗位编号", "jobcode", "positioncode", "code"],
    "job_description": ["职位描述", "岗位描述", "jobdescription", "description", "jd"],
    "company_intro": ["公司简介", "企业简介", "公司介绍", "companyintro", "introduction"],
}

TAG_PATTERNS = [
    ("Java", ["java", "j2ee", "spring"]),
    ("Python", ["python"]),
    ("Go", ["golang", "go开发", " go "]),
    ("C++", ["c++"]),
    ("前端", ["前端", "react", "vue", "javascript", "typescript"]),
    ("后端", ["后端", "服务端", "spring boot", "django", "fastapi"]),
    ("全栈", ["全栈"]),
    ("测试", ["测试", "qa", "自动化测试"]),
    ("运维", ["运维", "sre", "devops"]),
    ("数据分析", ["数据分析", "bi", "分析师"]),
    ("数据开发", ["数据开发", "数仓", "etl", "hive", "spark"]),
    ("算法", ["算法", "推荐", "搜索", "nlp"]),
    ("AI", ["ai", "人工智能", "大模型", "机器学习", "深度学习"]),
    ("SQL", ["sql", "mysql", "postgresql"]),
    ("Linux", ["linux"]),
    ("云计算", ["云计算", "aws", "阿里云", "腾讯云", "kubernetes", "docker"]),
    ("网络安全", ["安全", "渗透", "攻防", "风控"]),
]

INDUSTRY_PATTERNS = [
    ("人工智能", ["人工智能", "大模型", "机器学习"]),
    ("数据服务", ["大数据", "数据服务", "数据智能"]),
    ("企业服务", ["企业服务", "saas", "b2b"]),
    ("互联网", ["互联网", "web", "在线平台"]),
    ("计算机软件", ["软件", "软件开发", "saas"]),
    ("电子商务", ["电商", "电子商务"]),
    ("通信网络", ["通信", "网络设备", "网络技术"]),
    ("信息安全", ["信息安全", "网络安全", "安全"]),
    ("工业互联网", ["工业互联网", "智能制造"]),
    ("教育科技", ["教育科技", "在线教育"]),
]

COMPANY_SIZE_PATTERNS = [
    ("1-49人", ["少于50人", "20人以下", "1-49人", "15-50人"]),
    ("50-149人", ["50-150人", "50-149人", "50-99人", "100-149人"]),
    ("150-499人", ["150-500人", "150-499人", "200-499人"]),
    ("500-999人", ["500-999人", "500-1000人"]),
    ("1000-4999人", ["1000-9999人", "1000-4999人", "1000人以上"]),
    ("5000人以上", ["5000人以上", "10000人以上"]),
]

COMPANY_TYPE_PATTERNS = [
    ("民营企业", ["民营", "民营公司", "民营企业"]),
    ("上市公司", ["上市公司", "已上市"]),
    ("国有企业", ["国企", "国有企业"]),
    ("外资企业", ["外资", "外商独资", "外资企业"]),
    ("股份制企业", ["股份制", "股份制企业"]),
    ("合资企业", ["合资", "合资企业"]),
    ("事业单位", ["事业单位"]),
]

CITY_PATTERNS = {
    "北京市": ["北京"],
    "上海市": ["上海"],
    "天津市": ["天津"],
    "重庆市": ["重庆"],
    "杭州市": ["杭州"],
    "南京市": ["南京"],
    "苏州市": ["苏州"],
    "成都市": ["成都"],
    "武汉市": ["武汉"],
    "深圳市": ["深圳"],
    "广州市": ["广州"],
    "西安市": ["西安"],
    "长沙市": ["长沙"],
    "合肥市": ["合肥"],
}

CATEGORY_PATTERNS = [
    ("算法/AI", ["算法", "ai", "人工智能", "机器学习", "深度学习", "大模型", "nlp"]),
    ("前端开发", ["前端", "react", "vue", "javascript", "typescript"]),
    ("后端开发", ["后端", "java", "python", "golang", "go", "服务端"]),
    ("测试开发", ["测试", "qa"]),
    ("运维/DevOps", ["运维", "sre", "devops"]),
    ("数据分析", ["数据分析", "bi", "分析师"]),
    ("数据开发", ["数据开发", "数仓", "etl", "spark", "hive"]),
    ("安全", ["安全", "渗透", "风控"]),
    ("产品", ["产品经理", "产品"]),
]


@dataclass(slots=True)
class RawJobRecord:
    source_row_number: int
    position_name: str = EMPTY_TEXT
    work_address: str = EMPTY_TEXT
    salary_range: str = EMPTY_TEXT
    company_full_name: str = EMPTY_TEXT
    industry: str = EMPTY_TEXT
    company_size: str = EMPTY_TEXT
    company_type: str = EMPTY_TEXT
    job_code: str = EMPTY_TEXT
    job_description: str = EMPTY_TEXT
    company_intro: str = EMPTY_TEXT
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CleaningIssue:
    stage: str
    level: str
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SalaryResult:
    salary_range: str
    salary_min_monthly: int | None
    salary_max_monthly: int | None
    salary_pay_months: int
    salary_unit: str


@dataclass(slots=True)
class CleanJobRecord:
    source_row_number: int
    canonical_key: str
    position_name: str
    position_name_normalized: str
    job_category: str
    work_city: str
    work_address: str
    salary_range: str
    salary_min_monthly: int | None
    salary_max_monthly: int | None
    salary_pay_months: int
    salary_unit: str
    company_full_name: str
    company_name_normalized: str
    industry: str
    company_size: str
    company_type: str
    job_code: str
    job_code_generated: bool
    job_description: str
    company_intro: str
    job_tags: list[str]

    def to_export_dict(self) -> dict[str, Any]:
        return asdict(self)



def _normalize_text(value: Any, default: str = EMPTY_TEXT) -> str:
    if value is None:
        return default
    text = str(value).replace("\u3000", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text or default



def _normalize_for_key(value: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value.lower())



def _build_alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, aliases in FIELD_ALIASES.items():
        lookup[normalize_field_name(canonical)] = canonical
        for alias in aliases:
            lookup[normalize_field_name(alias)] = canonical
    return lookup


ALIAS_LOOKUP = _build_alias_lookup()



def project_source_record(record: Mapping[str, Any], source_row_number: int) -> RawJobRecord:
    canonical_record: dict[str, Any] = {field_name: EMPTY_TEXT for field_name in FIELD_ALIASES}
    payload: dict[str, Any] = {}
    for key, value in record.items():
        original_key = str(key).strip()
        payload[original_key] = value
        normalized_key = normalize_field_name(original_key)
        canonical_key = ALIAS_LOOKUP.get(normalized_key)
        if canonical_key:
            canonical_record[canonical_key] = _normalize_text(value)
    return RawJobRecord(
        source_row_number=source_row_number,
        position_name=_normalize_text(canonical_record["position_name"]),
        work_address=_normalize_text(canonical_record["work_address"]),
        salary_range=_normalize_text(canonical_record["salary_range"]),
        company_full_name=_normalize_text(canonical_record["company_full_name"]),
        industry=_normalize_text(canonical_record["industry"]),
        company_size=_normalize_text(canonical_record["company_size"]),
        company_type=_normalize_text(canonical_record["company_type"]),
        job_code=_normalize_text(canonical_record["job_code"]),
        job_description=_normalize_text(canonical_record["job_description"]),
        company_intro=_normalize_text(canonical_record["company_intro"]),
        raw_payload=payload,
    )



def _normalize_by_patterns(value: str, patterns: list[tuple[str, list[str]]], default: str) -> str:
    candidate = _normalize_text(value)
    if not candidate:
        return default
    lowered = candidate.lower()
    for normalized, aliases in patterns:
        if any(alias.lower() in lowered for alias in aliases):
            return normalized
    number_match = re.search(r"(\d+)\s*[-~]\s*(\d+)", lowered)
    if number_match:
        right = int(number_match.group(2))
        if right < 50:
            return "1-49人"
        if right < 150:
            return "50-149人"
        if right < 500:
            return "150-499人"
        if right < 1000:
            return "500-999人"
        if right < 5000:
            return "1000-4999人"
        return "5000人以上"
    single_number = re.search(r"(\d+)", lowered)
    if single_number and default.endswith("人"):
        value_int = int(single_number.group(1))
        if value_int < 50:
            return "1-49人"
        if value_int < 150:
            return "50-149人"
        if value_int < 500:
            return "150-499人"
        if value_int < 1000:
            return "500-999人"
        if value_int < 5000:
            return "1000-4999人"
        return "5000人以上"
    return candidate



def normalize_company_size(value: str) -> str:
    return _normalize_by_patterns(value, COMPANY_SIZE_PATTERNS, UNKNOWN_TEXT)



def normalize_company_type(value: str) -> str:
    return _normalize_by_patterns(value, COMPANY_TYPE_PATTERNS, UNKNOWN_TEXT)



def normalize_industry(value: str) -> str:
    return _normalize_by_patterns(value, INDUSTRY_PATTERNS, "其他信息化行业")



def normalize_position_name(value: str) -> str:
    cleaned = _normalize_text(value, UNKNOWN_JOB)
    cleaned = cleaned.replace("岗位", "").replace("职位", "")
    cleaned = re.sub(r"[【】\[\]()（）]", "", cleaned)
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned or UNKNOWN_JOB



def normalize_company_name(value: str) -> str:
    cleaned = _normalize_text(value, UNKNOWN_COMPANY)
    cleaned = re.sub(r"[（(].*?[)）]", "", cleaned)
    return cleaned or UNKNOWN_COMPANY



def extract_city(work_address: str) -> str:
    address = _normalize_text(work_address)
    if not address:
        return UNKNOWN_CITY
    for city, aliases in CITY_PATTERNS.items():
        if any(alias in address for alias in aliases):
            return city
    direct_match = re.search(r"([^\s,，/]{2,20}(?:市|州|地区|盟))", address)
    if direct_match:
        return direct_match.group(1)
    return UNKNOWN_CITY



def parse_salary_range(value: str) -> SalaryResult:
    salary_text = _normalize_text(value, "面议")
    lowered = salary_text.lower().replace("·", "").replace(" ", "")
    pay_months_match = re.search(r"(\d{1,2})薪", lowered)
    pay_months = int(pay_months_match.group(1)) if pay_months_match else 12

    if not lowered or "面议" in lowered:
        return SalaryResult(
            salary_range="面议",
            salary_min_monthly=None,
            salary_max_monthly=None,
            salary_pay_months=pay_months,
            salary_unit="negotiable",
        )

    salary_without_months = re.sub(r"\d{1,2}薪", "", lowered)
    number_tokens = re.findall(r"\d+(?:\.\d+)?", salary_without_months)
    if not number_tokens:
        return SalaryResult(
            salary_range=salary_text,
            salary_min_monthly=None,
            salary_max_monthly=None,
            salary_pay_months=pay_months,
            salary_unit="unknown",
        )

    if len(number_tokens) >= 2:
        min_value = float(number_tokens[0])
        max_value = float(number_tokens[1])
    else:
        min_value = max_value = float(number_tokens[0])

    if "万/年" in lowered or "万年" in lowered:
        factor = 10000 / 12
        unit = "yearly"
    elif "元/天" in lowered or "元/日" in lowered:
        factor = 21.75
        unit = "daily"
    elif "元/小时" in lowered or "元/时" in lowered:
        factor = 174
        unit = "hourly"
    elif "万/月" in lowered or ("万" in lowered and "/年" not in lowered):
        factor = 10000
        unit = "monthly"
    elif "k" in lowered:
        factor = 1000
        unit = "monthly"
    elif "元/月" in lowered or "月" in lowered:
        factor = 1
        unit = "monthly"
    else:
        factor = 1
        unit = "unknown"

    salary_min = int(round(min_value * factor))
    salary_max = int(round(max_value * factor))
    return SalaryResult(
        salary_range=salary_text,
        salary_min_monthly=salary_min,
        salary_max_monthly=salary_max,
        salary_pay_months=pay_months,
        salary_unit=unit,
    )



def build_job_tags(position_name: str, job_description: str, industry: str) -> list[str]:
    corpus = " ".join([position_name, job_description, industry]).lower()
    tags: list[str] = []
    for tag, keywords in TAG_PATTERNS:
        if any(keyword in corpus for keyword in keywords) and tag not in tags:
            tags.append(tag)
    return tags



def infer_job_category(position_name: str, tags: list[str], job_description: str) -> str:
    corpus = " ".join([position_name, " ".join(tags), job_description]).lower()
    for category, keywords in CATEGORY_PATTERNS:
        if any(keyword in corpus for keyword in keywords):
            return category
    return "通用研发"



def generate_job_code(record: RawJobRecord) -> str:
    source = "|".join(
        [
            normalize_position_name(record.position_name),
            normalize_company_name(record.company_full_name),
            extract_city(record.work_address),
            str(record.source_row_number),
        ]
    )
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:12].upper()
    return f"AUTO-{digest}"



def build_canonical_key(
    position_name_normalized: str,
    company_name_normalized: str,
    work_city: str,
    salary_result: SalaryResult,
    job_code: str,
    job_code_generated: bool,
) -> str:
    if not job_code_generated and job_code:
        dedup_parts = ["code", company_name_normalized, position_name_normalized, job_code]
    else:
        dedup_parts = [
            "fallback",
            company_name_normalized,
            position_name_normalized,
            work_city,
            str(salary_result.salary_min_monthly or 0),
            str(salary_result.salary_max_monthly or 0),
        ]
    return hashlib.sha1("|".join(dedup_parts).encode("utf-8")).hexdigest()



def clean_job_record(record: RawJobRecord) -> tuple[CleanJobRecord, list[CleaningIssue]]:
    issues: list[CleaningIssue] = []

    if not _normalize_text(record.position_name):
        issues.append(
            CleaningIssue(
                stage="standardize",
                level="warning",
                code="missing_position_name",
                message="Position name was missing and has been replaced with a fallback value.",
            )
        )
    if not _normalize_text(record.company_full_name):
        issues.append(
            CleaningIssue(
                stage="standardize",
                level="warning",
                code="missing_company_name",
                message="Company name was missing and has been replaced with a fallback value.",
            )
        )
    if not _normalize_text(record.work_address):
        issues.append(
            CleaningIssue(
                stage="standardize",
                level="warning",
                code="missing_work_address",
                message="Work address was missing and city extraction fell back to an unknown city marker.",
            )
        )
    if not _normalize_text(record.salary_range):
        issues.append(
            CleaningIssue(
                stage="standardize",
                level="warning",
                code="missing_salary_range",
                message="Salary range was missing and has been replaced with negotiable.",
            )
        )

    position_name_normalized = normalize_position_name(record.position_name)
    company_name_normalized = normalize_company_name(record.company_full_name)
    work_address = _normalize_text(record.work_address, UNKNOWN_TEXT)
    work_city = extract_city(record.work_address)
    salary_result = parse_salary_range(record.salary_range)
    industry = normalize_industry(record.industry)
    company_size = normalize_company_size(record.company_size)
    company_type = normalize_company_type(record.company_type)
    job_description = _normalize_text(record.job_description, EMPTY_TEXT)
    company_intro = _normalize_text(record.company_intro, EMPTY_TEXT)

    if salary_result.salary_min_monthly is None and salary_result.salary_unit == "unknown":
        issues.append(
            CleaningIssue(
                stage="standardize",
                level="warning",
                code="salary_parse_fallback",
                message="Salary range could not be parsed into monthly bounds.",
                details={"raw_salary_range": record.salary_range},
            )
        )

    job_code = _normalize_text(record.job_code)
    job_code_generated = not bool(job_code)
    if job_code_generated:
        job_code = generate_job_code(record)
        issues.append(
            CleaningIssue(
                stage="standardize",
                level="info",
                code="generated_job_code",
                message="Job code was missing and has been generated from normalized company, title, city and row number.",
                details={"job_code": job_code},
            )
        )

    job_tags = build_job_tags(position_name_normalized, job_description, industry)
    job_category = infer_job_category(position_name_normalized, job_tags, job_description)
    canonical_key = build_canonical_key(
        position_name_normalized=position_name_normalized,
        company_name_normalized=_normalize_for_key(company_name_normalized),
        work_city=_normalize_for_key(work_city),
        salary_result=salary_result,
        job_code=_normalize_for_key(job_code),
        job_code_generated=job_code_generated,
    )

    cleaned = CleanJobRecord(
        source_row_number=record.source_row_number,
        canonical_key=canonical_key,
        position_name=_normalize_text(record.position_name, UNKNOWN_JOB),
        position_name_normalized=position_name_normalized,
        job_category=job_category,
        work_city=work_city,
        work_address=work_address,
        salary_range=salary_result.salary_range,
        salary_min_monthly=salary_result.salary_min_monthly,
        salary_max_monthly=salary_result.salary_max_monthly,
        salary_pay_months=salary_result.salary_pay_months,
        salary_unit=salary_result.salary_unit,
        company_full_name=_normalize_text(record.company_full_name, UNKNOWN_COMPANY),
        company_name_normalized=company_name_normalized,
        industry=industry,
        company_size=company_size,
        company_type=company_type,
        job_code=job_code,
        job_code_generated=job_code_generated,
        job_description=job_description,
        company_intro=company_intro,
        job_tags=job_tags,
    )
    return cleaned, issues

# AI辅助生成：Qwen3-Max-Thinking, 2026-04-27
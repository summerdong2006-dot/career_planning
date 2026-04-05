from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from app.modules.student_profile.schema import TEXT_DEFAULT

PUNCT_TRANSLATION = str.maketrans(
    {
        "：": ":",
        "；": ";",
        "，": ",",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "“": '"',
        "”": '"',
    }
)

DELIMITER_PATTERN = re.compile(r"[\n,;，；|]+")
PLACEHOLDER_TEXTS = {"", "未明确", "n/a", "na", "none", "null", "暂无", "无", "unknown"}

EXPLICIT_SKILL_FIELDS = ("skills", "skill", "专业技能", "技能", "技术栈")
SKILL_SECTION_MARKERS = ["技能", "专业技能", "掌握", "熟悉", "精通", "技术栈"]

NAME_LABEL_PATTERNS = [
    r"(?:姓名|name)\s*[:：]\s*([^\n,，;；]+)",
]
NAME_STOP_MARKERS = ["学校", "学院", "大学", "专业", "学历", "本科", "硕士", "博士", "项目", "实习", "求职意向"]
NAME_INVALID_TERMS = {
    "软件工程",
    "计算机",
    "计算机科学",
    "计算机科学与技术",
    "信息管理",
    "信息管理与信息系统",
    "人工智能",
    "数据科学",
    "数据科学与大数据技术",
    "网络工程",
    "通信工程",
    "电子商务",
}

MAJOR_LABEL_PATTERNS = [
    r"(?:专业|主修|所学专业)\s*[:：]\s*(.+)",
]
MAJOR_STOP_MARKERS = ["学历", "学位", "技能", "专业技能", "项目经历", "实习经历", "竞赛经历", "学生工作", "求职意向", "职业意向", "证书"]

SKILL_PATTERNS = [
    ("Python", ["python"]),
    ("Java", ["java"]),
    ("C++", ["c++"]),
    ("SQL", ["sql", "mysql", "postgresql", "oracle"]),
    ("Excel", ["excel"]),
    ("Power BI", ["power bi", "powerbi"]),
    ("Tableau", ["tableau"]),
    ("SPSS", ["spss"]),
    ("MATLAB", ["matlab"]),
    ("Linux", ["linux"]),
    ("Git", ["git"]),
    ("Docker", ["docker"]),
    ("FastAPI", ["fastapi"]),
    ("Django", ["django"]),
    ("Spring Boot", ["spring boot", "springboot"]),
    ("React", ["react"]),
    ("Vue", ["vue"]),
    ("JavaScript", ["javascript", "js"]),
    ("TypeScript", ["typescript"]),
    ("机器学习", ["机器学习", "machine learning"]),
    ("深度学习", ["深度学习", "deep learning"]),
    ("PyTorch", ["pytorch"]),
    ("TensorFlow", ["tensorflow"]),
    ("NLP", ["nlp", "自然语言处理"]),
]

CERTIFICATE_PATTERNS = [
    "CET-4",
    "CET-6",
    "教师资格证",
    "计算机二级",
    "普通话等级证书",
    "PMP",
    "证券从业资格",
    "初级会计职称",
]

COMPETITION_MARKERS = ["竞赛", "比赛", "挑战杯", "互联网+", "数学建模", "创新创业", "获奖", "奖学金"]
INTERN_MARKERS = ["实习", "intern", "公司", "客户", "业务支持", "交付"]
PROJECT_MARKERS = ["项目", "课题", "系统设计", "平台开发", "研究", "作品"]
STUDENT_WORK_MARKERS = ["学生会", "社团", "班长", "部长", "志愿者", "组织", "宣传", "辅导员助理"]
CAREER_MARKERS = ["求职意向", "职业意向", "意向岗位", "目标岗位", "希望从事", "应聘"]
CAREER_STOP_MARKERS = ["教育背景", "学校", "专业", "技能", "专业技能", "项目经历", "实习经历", "校园经历", "学生工作", "竞赛经历", "获奖经历", "证书", "自我评价", "个人优势"]
INNOVATION_MARKERS = ["创新", "创业", "发明", "专利", "研究", "竞赛", "作品"]
PROJECT_SECTION_HEADERS = ["项目经历", "项目经验", "项目实践"]
INTERNSHIP_SECTION_HEADERS = ["实习经历", "实习经验", "工作经历", "实践经历"]
COMPETITION_SECTION_HEADERS = ["竞赛经历", "竞赛经验", "获奖经历"]
STUDENT_WORK_SECTION_HEADERS = ["校园经历", "学生工作", "学生组织经历"]
ALL_SECTION_HEADERS = [
    *PROJECT_SECTION_HEADERS,
    *INTERNSHIP_SECTION_HEADERS,
    *COMPETITION_SECTION_HEADERS,
    *STUDENT_WORK_SECTION_HEADERS,
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ").translate(PUNCT_TRANSLATION)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def has_meaningful_text(value: Any) -> bool:
    text = clean_text(value).lower()
    return bool(text) and text not in PLACEHOLDER_TEXTS


def has_meaningful_mapping(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    for item in value.values():
        if isinstance(item, Mapping) and has_meaningful_mapping(item):
            return True
        if isinstance(item, list):
            if any(has_meaningful_text(sub_item) for sub_item in item):
                return True
            continue
        if has_meaningful_text(item):
            return True
    return False


def detect_profile_source(resume_text: str, manual_form: Mapping[str, Any], supplement_text: str) -> str:
    has_resume = has_meaningful_text(resume_text)
    has_manual = has_meaningful_mapping(manual_form)
    has_supplement = has_meaningful_text(supplement_text)
    active_sources = sum((has_resume, has_manual, has_supplement))
    if active_sources >= 2:
        return "hybrid"
    if has_resume:
        return "resume"
    if has_manual or has_supplement:
        return "manual"
    return TEXT_DEFAULT


def flatten_items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        flattened: list[str] = []
        for item in value:
            flattened.extend(flatten_items(item))
        return flattened
    if isinstance(value, Mapping):
        return []
    text = clean_text(value)
    return [text] if text else []


def truncate_at_delimiters(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    return clean_text(DELIMITER_PATTERN.split(text, maxsplit=1)[0])


def truncate_at_field_markers(value: Any, markers: list[str]) -> str:
    text = clean_text(value)
    if not text:
        return ""
    stop_positions = [text.find(marker) for marker in markers if text.find(marker) > 0]
    if stop_positions:
        text = text[: min(stop_positions)]
    return clean_text(text)


def sanitize_major_candidate(value: Any) -> str:
    text = truncate_at_field_markers(value, MAJOR_STOP_MARKERS)
    text = truncate_at_delimiters(text)
    text = re.sub(r"^[A-Za-z\u4e00-\u9fff]{2,}(?:大学|学院)", "", text, count=1).strip()
    text = clean_text(text).strip(": ")
    return text or TEXT_DEFAULT


def dedupe_lines(text: str) -> str:
    seen: set[str] = set()
    output: list[str] = []
    for raw_line in re.split(r"[\r\n]+", text):
        line = clean_text(raw_line)
        if not line or line in seen:
            continue
        seen.add(line)
        output.append(line)
    return "\n".join(output)


def split_search_units(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"[\r\n,，。；;()（）\[\]]+", text)
    return [clean_text(part) for part in parts if clean_text(part)]


def split_segments(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"[\n。！？!?]+", text)
    return [clean_text(part) for part in parts if clean_text(part)]


def split_lines(text: str) -> list[str]:
    if not text:
        return []
    return [clean_text(line) for line in re.split(r"[\r\n]+", text) if clean_text(line)]


def preprocess_texts(resume_text: str, supplement_text: str, manual_form: Mapping[str, Any], basic_info: Mapping[str, Any]) -> dict[str, Any]:
    manual_lines = [f"{key}: {value}" for key, value in manual_form.items() if value not in (None, "", [], {})]
    basic_lines = [f"{key}: {value}" for key, value in basic_info.items() if value not in (None, "", [], {})]
    combined = "\n".join(
        part
        for part in [
            clean_text(resume_text),
            clean_text("\n".join(manual_lines)),
            clean_text(supplement_text),
            clean_text("\n".join(basic_lines)),
        ]
        if part
    )
    deduped = dedupe_lines(combined)
    return {
        "resume_text": clean_text(resume_text),
        "supplement_text": clean_text(supplement_text),
        "manual_text": clean_text("\n".join(manual_lines)),
        "basic_text": clean_text("\n".join(basic_lines)),
        "normalized_text": deduped,
        "lines": split_lines(deduped),
        "segments": split_segments(deduped),
        "search_units": split_search_units(deduped),
    }


def unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = clean_text(value)
        if text and text not in result:
            result.append(text)
    return result


def _extract_single(patterns: list[str], texts: Iterable[str], default: str = TEXT_DEFAULT) -> tuple[str, list[str]]:
    for text in texts:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = truncate_at_delimiters(match.group(1) if match.groups() else match.group(0))
                if value:
                    return value, [clean_text(text)]
    return default, []


def _keyword_matches(segments: Iterable[str], markers: list[str]) -> list[str]:
    matches: list[str] = []
    for segment in segments:
        lowered = segment.lower()
        if any(marker.lower() in lowered for marker in markers):
            matches.append(segment)
    return unique(matches)


def _extract_student_name(
    preprocessed: Mapping[str, Any],
    manual_form: Mapping[str, Any],
    basic_info: Mapping[str, Any],
) -> tuple[str, list[str]]:
    explicit_value = basic_info.get("student_name") or basic_info.get("name") or manual_form.get("student_name") or manual_form.get("name")
    explicit_text = truncate_at_delimiters(explicit_value)
    if explicit_text and explicit_text not in NAME_INVALID_TERMS and re.fullmatch(r"[\u4e00-\u9fff]{2,4}", explicit_text):
        return explicit_text, [clean_text(explicit_value)]

    texts = [preprocessed.get("normalized_text", ""), preprocessed.get("manual_text", ""), preprocessed.get("basic_text", "")]
    for text in texts:
        for pattern in NAME_LABEL_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            candidate = truncate_at_delimiters(truncate_at_field_markers(match.group(1), NAME_STOP_MARKERS))
            if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", candidate) and candidate not in NAME_INVALID_TERMS:
                return candidate, [clean_text(text)]

    normalized_text = clean_text(preprocessed.get("normalized_text", ""))
    natural_match = re.match(r"^\s*([\u4e00-\u9fff]{2,4})[，,\s]", normalized_text)
    if natural_match:
        candidate = natural_match.group(1)
        trailing_text = normalized_text[len(natural_match.group(0)) :]
        if candidate not in NAME_INVALID_TERMS and any(marker in trailing_text[:40] for marker in ("大学", "学院", "专业", "本科", "硕士", "博士")):
            return candidate, [normalized_text]

    return TEXT_DEFAULT, []


def _extract_skills(segments: Iterable[str], manual_form: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    raw: list[str] = []
    evidence: list[str] = []
    for field_name in EXPLICIT_SKILL_FIELDS:
        if field_name not in manual_form:
            continue
        value = manual_form.get(field_name)
        if isinstance(value, list):
            raw.extend(str(item) for item in value)
        elif value not in (None, "", [], {}):
            raw.extend(re.split(r"[\n,，/、;；|]+", str(value)))

    for segment in segments:
        lowered = segment.lower()
        if any(marker.lower() in lowered for marker in SKILL_SECTION_MARKERS):
            evidence.append(segment)
        for canonical, aliases in SKILL_PATTERNS:
            if any(alias.lower() in lowered for alias in aliases):
                raw.append(canonical)

    return unique(raw), unique(evidence)[:6]


def _extract_certificates(segments: Iterable[str], manual_form: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    raw = flatten_items(manual_form.get("certificates"))
    evidence: list[str] = []
    for segment in segments:
        lowered = segment.lower()
        for certificate in CERTIFICATE_PATTERNS:
            if certificate.lower() in lowered:
                raw.append(certificate)
                evidence.append(segment)
    return unique(raw), unique(evidence)[:6]


def _extract_collection_lines(
    segments: Iterable[str],
    manual_form: Mapping[str, Any],
    field_names: list[str],
    markers: list[str],
) -> tuple[list[str], list[str]]:
    raw: list[str] = []
    for field_name in field_names:
        value = manual_form.get(field_name)
        if isinstance(value, list):
            raw.extend(str(item) for item in value)
        elif value:
            raw.extend(re.split(r"[\n]+", str(value)))
    evidence = _keyword_matches(segments, markers)
    raw.extend(evidence)
    return unique(raw), evidence[:6]


def _normalize_section_header(value: str) -> str:
    return re.sub(r"[\s:：]+", "", clean_text(value)).lower()


def _matches_section_header(line: str, headers: list[str]) -> bool:
    normalized_line = _normalize_section_header(line)
    return any(normalized_line.startswith(_normalize_section_header(header)) for header in headers)


def _extract_section_lines(preprocessed: Mapping[str, Any], headers: list[str]) -> list[str]:
    lines = list(preprocessed.get("lines", []))
    start_index: int | None = None
    leading_line: str | None = None
    for index, line in enumerate(lines):
        if _matches_section_header(line, headers):
            start_index = index + 1
            leading_line = re.sub(r"^[^:：]+[:：]\s*", "", line).strip()
            break
    if start_index is None:
        return []

    section_lines: list[str] = []
    if leading_line and leading_line != clean_text(lines[start_index - 1]):
        section_lines.append(clean_text(leading_line))
    for line in lines[start_index:]:
        if _matches_section_header(line, ALL_SECTION_HEADERS):
            break
        section_lines.append(line)
    return section_lines


def _extract_labeled_line_value(
    preprocessed: Mapping[str, Any],
    labels: list[str],
    *,
    stop_markers: list[str] | None = None,
) -> tuple[str, list[str]]:
    lines = list(preprocessed.get("lines", []))
    for index, line in enumerate(lines):
        value = _extract_labeled_value(line, labels)
        if value:
            if stop_markers:
                value = truncate_at_field_markers(value, stop_markers)
            value = truncate_at_delimiters(value)
            if value:
                return value, [line]
        normalized = clean_text(line)
        for label in labels:
            header_only = re.sub(r"[\s:：]+", "", normalized)
            if header_only == re.sub(r"[\s:：]+", "", label) and index + 1 < len(lines):
                next_line = clean_text(lines[index + 1])
                if next_line and not _matches_section_header(next_line, ALL_SECTION_HEADERS):
                    if stop_markers:
                        next_line = truncate_at_field_markers(next_line, stop_markers)
                    next_line = truncate_at_delimiters(next_line)
                    if next_line:
                        return next_line, [line, lines[index + 1]]
    return "", []


def _flatten_collection_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        items: list[Any] = []
        for item in value:
            items.extend(_flatten_collection_items(item))
        return items
    if isinstance(value, Mapping):
        return [dict(value)]
    text = clean_text(value)
    return [text] if text else []


def _extract_labeled_value(line: str, labels: list[str]) -> str:
    text = clean_text(line)
    lowered = text.lower()
    for label in labels:
        label_lower = label.lower()
        if lowered.startswith(label_lower):
            remainder = text[len(label) :]
            remainder = re.sub(r"^[\s:：-]+", "", remainder)
            return clean_text(remainder)
    return ""


def _compact_entry_text(lines: list[str]) -> str:
    return clean_text("；".join(line for line in lines if clean_text(line)))


def _parse_project_entries(preprocessed: Mapping[str, Any]) -> list[dict[str, Any]]:
    section_lines = _extract_section_lines(preprocessed, PROJECT_SECTION_HEADERS)
    if not section_lines:
        return []

    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    detail_lines: list[str] = []

    def flush() -> None:
        nonlocal current, detail_lines
        if current is None:
            return
        if detail_lines:
            current["description"] = _compact_entry_text(detail_lines)
        if not clean_text(current.get("name")) and detail_lines:
            current["name"] = clean_text(detail_lines[0])
        if clean_text(current.get("name")) or clean_text(current.get("description")):
            current["name"] = clean_text(current.get("name")) or clean_text(current.get("description")) or TEXT_DEFAULT
            current["role"] = clean_text(current.get("role")) or TEXT_DEFAULT
            current["description"] = clean_text(current.get("description")) or current["name"]
            entries.append(current)
        current = None
        detail_lines = []

    for line in section_lines:
        project_name = _extract_labeled_value(
            line,
            ["项目一", "项目二", "项目三", "项目四", "项目五", "项目六", "项目七", "项目八", "项目九", "项目十", "项目名称"],
        )
        if project_name:
            flush()
            current = {"name": project_name, "role": TEXT_DEFAULT, "description": ""}
            continue

        if re.match(r"^项目[0-9A-Za-z一二三四五六七八九十]+", line):
            flush()
            current = {
                "name": clean_text(re.sub(r"^项目[0-9A-Za-z一二三四五六七八九十]+\s*[:：]?\s*", "", line)),
                "role": TEXT_DEFAULT,
                "description": "",
            }
            continue

        generic_project_name = _extract_labeled_value(line, ["项目"])
        if generic_project_name and not any(line.startswith(prefix) for prefix in ["项目描述", "项目内容", "项目简介"]):
            flush()
            current = {"name": generic_project_name, "role": TEXT_DEFAULT, "description": ""}
            continue

        if current is None:
            current = {"name": line, "role": TEXT_DEFAULT, "description": ""}
            continue

        role_value = _extract_labeled_value(line, ["角色", "担任角色"])
        if role_value:
            current["role"] = role_value
            continue

        detail_value = _extract_labeled_value(line, ["项目描述", "项目内容", "项目简介", "个人职责", "负责内容"])
        if detail_value:
            detail_lines.append(detail_value)
            continue

        if not re.match(r"^(时间|起止时间)\s*[:：]", line):
            detail_lines.append(line)

    flush()
    return entries


def _parse_internship_entries(preprocessed: Mapping[str, Any]) -> list[dict[str, Any]]:
    section_lines = _extract_section_lines(preprocessed, INTERNSHIP_SECTION_HEADERS)
    if not section_lines:
        return []

    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    detail_lines: list[str] = []

    def flush() -> None:
        nonlocal current, detail_lines
        if current is None:
            return
        if detail_lines:
            current["description"] = _compact_entry_text(detail_lines)
        if clean_text(current.get("company")) or clean_text(current.get("role")) or clean_text(current.get("description")):
            current["company"] = clean_text(current.get("company")) or TEXT_DEFAULT
            current["role"] = clean_text(current.get("role")) or TEXT_DEFAULT
            current["description"] = clean_text(current.get("description")) or current["role"] or current["company"]
            entries.append(current)
        current = None
        detail_lines = []

    for line in section_lines:
        company_value = _extract_labeled_value(line, ["公司", "实习公司", "实习单位", "单位", "企业"])
        if company_value:
            flush()
            current = {"company": company_value, "role": TEXT_DEFAULT, "description": ""}
            continue

        if current is None and ("实习" in line or "兼职" in line):
            current = {"company": TEXT_DEFAULT, "role": line, "description": ""}
            continue

        if current is None:
            continue

        role_value = _extract_labeled_value(line, ["岗位", "职位", "职务"])
        if role_value:
            current["role"] = role_value
            continue

        detail_value = _extract_labeled_value(line, ["工作内容", "工作描述", "实习内容", "实习描述", "岗位职责", "职责"])
        if detail_value:
            detail_lines.append(detail_value)
            continue

        if not re.match(r"^(时间|起止时间)\s*[:：]", line):
            detail_lines.append(line)

    flush()
    return entries


def _extract_school(preprocessed: Mapping[str, Any], manual_form: Mapping[str, Any], basic_info: Mapping[str, Any]) -> tuple[str, list[str]]:
    explicit_value = basic_info.get("school") or manual_form.get("school")
    explicit_text = truncate_at_delimiters(explicit_value)
    if explicit_text:
        return explicit_text, [clean_text(explicit_value)]

    line_value, line_evidence = _extract_labeled_line_value(preprocessed, ["学校", "毕业院校"])
    if line_value:
        return line_value, line_evidence

    normalized_text = clean_text(preprocessed.get("normalized_text", ""))
    match = re.search(r"(?:学校|毕业院校)\s*[:：]\s*([^\n]+)", normalized_text)
    if match:
        return truncate_at_delimiters(match.group(1)), [normalized_text]

    school_match = re.search(r"([A-Za-z\u4e00-\u9fff]{2,}(?:大学|学院))", normalized_text)
    if school_match:
        return school_match.group(1), [normalized_text]

    return TEXT_DEFAULT, []


def _extract_major(preprocessed: Mapping[str, Any], manual_form: Mapping[str, Any], basic_info: Mapping[str, Any]) -> tuple[str, list[str]]:
    explicit_value = basic_info.get("major") or manual_form.get("major")
    explicit_text = sanitize_major_candidate(explicit_value)
    if explicit_text != TEXT_DEFAULT:
        return explicit_text, [clean_text(explicit_value)]

    line_value, line_evidence = _extract_labeled_line_value(preprocessed, ["专业", "主修专业"], stop_markers=MAJOR_STOP_MARKERS)
    if line_value:
        candidate = sanitize_major_candidate(line_value)
        if candidate != TEXT_DEFAULT:
            return candidate, line_evidence

    normalized_text = clean_text(preprocessed.get("normalized_text", ""))
    match = re.search(r"(?:专业|主修|所学专业)\s*[:：]\s*([^\n]+)", normalized_text)
    if match:
        candidate = sanitize_major_candidate(match.group(1))
        if candidate != TEXT_DEFAULT:
            return candidate, [normalized_text]

    major_match = re.search(
        r"(计算机科学与技术|软件工程|信息管理与信息系统|人工智能|数据科学与大数据技术|网络工程|通信工程|电子商务|自动化|统计学|新闻学|土木工程)",
        normalized_text,
    )
    if major_match:
        return major_match.group(1), [normalized_text]

    return TEXT_DEFAULT, []


def extract_base_fields(preprocessed: Mapping[str, Any], manual_form: Mapping[str, Any], basic_info: Mapping[str, Any]) -> dict[str, Any]:
    texts = [preprocessed.get("normalized_text", ""), preprocessed.get("manual_text", ""), preprocessed.get("basic_text", "")]
    student_name, student_name_evidence = _extract_student_name(preprocessed, manual_form, basic_info)
    student_no = truncate_at_delimiters(basic_info.get("student_no") or basic_info.get("student_id") or manual_form.get("student_no") or manual_form.get("学号"))
    student_no = student_no or _extract_single([r"(?:学号|student[_ ]?no)\s*[:：]\s*([A-Za-z0-9_-]+)"], texts)[0]
    school, school_evidence = _extract_school(preprocessed, manual_form, basic_info)
    major, major_evidence = _extract_major(preprocessed, manual_form, basic_info)
    education, education_evidence = _extract_single([r"(博士)", r"(硕士)", r"(本科)", r"(大专)", r"(中专)"], texts)
    line_education, line_education_evidence = _extract_labeled_line_value(preprocessed, ["学历", "学位"])
    if line_education:
        education, education_evidence = line_education, line_education_evidence
    education = truncate_at_delimiters(basic_info.get("education") or manual_form.get("education") or education)
    grade, grade_evidence = _extract_single([r"(20\d{2}级)", r"(大[一二三四五])", r"(研[一二三])", r"((?:20\d{2})届)"], texts)
    line_grade, line_grade_evidence = _extract_labeled_line_value(preprocessed, ["年级", "毕业时间", "毕业届次"])
    if line_grade:
        grade, grade_evidence = line_grade, line_grade_evidence
    grade = truncate_at_delimiters(basic_info.get("grade") or manual_form.get("grade") or grade)
    return {
        "student_name": student_name or TEXT_DEFAULT,
        "student_no": student_no or TEXT_DEFAULT,
        "school": school or TEXT_DEFAULT,
        "major": major or TEXT_DEFAULT,
        "education": education or TEXT_DEFAULT,
        "grade": grade or TEXT_DEFAULT,
        "field_evidence": {
            "student_name": student_name_evidence[:3],
            "student_no": [student_no] if student_no else [],
            "school": school_evidence[:3],
            "major": major_evidence[:3],
            "education": education_evidence[:3],
            "grade": grade_evidence[:3],
        },
    }


def infer_resume_source(resume_text: str, manual_form: Mapping[str, Any], supplement_text: str) -> str:
    return detect_profile_source(resume_text, manual_form, supplement_text)


def _extract_career_intention(
    preprocessed: Mapping[str, Any],
    manual_form: Mapping[str, Any],
    basic_info: Mapping[str, Any],
) -> tuple[str, list[str]]:
    explicit_value = manual_form.get("career_intention") or basic_info.get("career_intention")
    explicit_text = truncate_at_delimiters(truncate_at_field_markers(explicit_value, CAREER_STOP_MARKERS))
    if explicit_text:
        return explicit_text, [clean_text(explicit_value)]

    line_value, line_evidence = _extract_labeled_line_value(
        preprocessed,
        ["求职意向", "职业意向", "意向岗位", "目标岗位"],
        stop_markers=CAREER_STOP_MARKERS,
    )
    if line_value:
        return line_value, line_evidence

    lines = [clean_text(line) for line in re.split(r"[\r\n]+", preprocessed.get("normalized_text", "")) if clean_text(line)]
    for line in lines:
        for marker in CAREER_MARKERS:
            if marker not in line:
                continue
            candidate = line[line.find(marker) + len(marker) :]
            candidate = re.sub(r"^[\s:：\-]+", "", candidate)
            candidate = truncate_at_delimiters(truncate_at_field_markers(candidate, CAREER_STOP_MARKERS))
            candidate = re.sub(r"^(希望从事|应聘)\s*", "", candidate)
            if candidate:
                return candidate, [line]
    return TEXT_DEFAULT, []


def build_raw_profile_payload(preprocessed: Mapping[str, Any], manual_form: Mapping[str, Any], basic_info: Mapping[str, Any]) -> dict[str, Any]:
    segments = preprocessed.get("segments", [])
    base = extract_base_fields(preprocessed, manual_form, basic_info)
    skills, skills_evidence = _extract_skills(segments, manual_form)
    certificates, certificate_evidence = _extract_certificates(segments, manual_form)

    project_items: list[Any] = []
    for field_name in ["projects", "project_experiences"]:
        project_items.extend(_flatten_collection_items(manual_form.get(field_name)))
    projects = [*project_items, *_parse_project_entries(preprocessed)]
    project_evidence = _keyword_matches(segments, PROJECT_MARKERS)

    internship_items: list[Any] = []
    for field_name in ["internships", "internship_experiences"]:
        internship_items.extend(_flatten_collection_items(manual_form.get(field_name)))
    internships = [*internship_items, *_parse_internship_entries(preprocessed)]
    internship_evidence = _keyword_matches(segments, INTERN_MARKERS)

    competitions, competition_evidence = _extract_collection_lines(segments, manual_form, ["competitions", "competition_experiences"], COMPETITION_MARKERS)
    student_work, student_work_evidence = _extract_collection_lines(segments, manual_form, ["student_work"], STUDENT_WORK_MARKERS)
    innovation_experiences, innovation_evidence = _extract_collection_lines(segments, manual_form, ["innovation_experiences"], INNOVATION_MARKERS)
    career_text, career_evidence = _extract_career_intention(preprocessed, manual_form, basic_info)

    return {
        "base_fields": base,
        "skills": skills,
        "projects": projects,
        "internships": internships,
        "competitions": competitions,
        "certificates": certificates,
        "student_work": student_work,
        "career_intention": career_text or TEXT_DEFAULT,
        "innovation_experiences": innovation_experiences,
        "resume_source": infer_resume_source(preprocessed.get("resume_text", ""), manual_form, preprocessed.get("supplement_text", "")),
        "sections": {
            "skills": skills_evidence,
            "projects": project_evidence,
            "internships": internship_evidence,
            "competitions": competition_evidence,
            "certificates": certificate_evidence,
            "student_work": student_work_evidence,
            "career_intention": career_evidence,
            "innovation_experiences": innovation_evidence,
        },
        "preprocessed": {
            "normalized_text": preprocessed.get("normalized_text", ""),
            "segments": segments,
        },
    }

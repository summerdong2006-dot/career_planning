from __future__ import annotations

DEFAULT_MATCHING_WEIGHTS = {
    "base_requirement": 0.25,
    "skill": 0.40,
    "soft_skill": 0.20,
    "growth": 0.15,
}

DEFAULT_TOP_K = 5
LOW_JOB_CONFIDENCE_THRESHOLD = 0.45
LOW_STUDENT_COMPLETENESS_THRESHOLD = 45.0
MATCH_PASSING_SCORE = 60.0
TEXT_DEFAULT = "未明确"

EDUCATION_LEVELS = {
    "学历不限": 0,
    "不限学历": 0,
    "中专": 1,
    "大专": 2,
    "本科": 3,
    "学士": 3,
    "硕士": 4,
    "研究生": 4,
    "博士": 5,
}

SKILL_PATTERNS: list[tuple[str, list[str]]] = [
    ("Python", ["python", "py"]),
    ("Java", ["java"]),
    ("Go", ["golang", "go语言", "go开发"]),
    ("C++", ["c++", "cpp"]),
    ("SQL", ["sql", "mysql", "postgresql", "oracle", "sqlite"]),
    ("MySQL", ["mysql"]),
    ("PostgreSQL", ["postgresql", "postgres"]),
    ("Redis", ["redis"]),
    ("FastAPI", ["fastapi"]),
    ("Django", ["django"]),
    ("Flask", ["flask"]),
    ("Spring Boot", ["spring boot", "springboot", "spring"]),
    ("React", ["react"]),
    ("Vue", ["vue"]),
    ("JavaScript", ["javascript", "js"]),
    ("TypeScript", ["typescript", "ts"]),
    ("Docker", ["docker", "容器化", "云原生"]),
    ("Kubernetes", ["kubernetes", "k8s"]),
    ("Linux", ["linux"]),
    ("Git", ["git"]),
    ("Spark", ["spark"]),
    ("Hive", ["hive"]),
    ("ETL", ["etl"]),
    ("Excel", ["excel"]),
    ("Tableau", ["tableau"]),
    ("Power BI", ["power bi", "powerbi", "bi报表"]),
    ("机器学习", ["机器学习", "machine learning", "ml"]),
    ("深度学习", ["深度学习", "deep learning"]),
    ("PyTorch", ["pytorch"]),
    ("TensorFlow", ["tensorflow"]),
    ("NLP", ["nlp", "自然语言处理"]),
    ("数据分析", ["数据分析", "数据洞察", "数据建模"]),
]

SOFT_SKILL_TO_ABILITY = {
    "沟通能力": "communication",
    "表达能力": "communication",
    "沟通协调": "communication",
    "团队协作": "communication",
    "团队合作": "communication",
    "跨团队": "communication",
    "学习能力": "learning",
    "快速学习": "learning",
    "学习意愿": "learning",
    "自驱力": "learning",
    "主动性": "learning",
    "抗压能力": "stress_score",
    "承压能力": "stress_score",
    "执行力": "internship",
    "责任心": "internship",
    "逻辑思维": "innovation",
    "逻辑能力": "innovation",
    "创新能力": "innovation",
}

ABILITY_LABELS = {
    "professional_skill_score": "专业技能",
    "innovation": "创新能力",
    "learning": "学习能力",
    "stress_score": "抗压能力",
    "communication": "沟通能力",
    "internship": "实习能力",
}


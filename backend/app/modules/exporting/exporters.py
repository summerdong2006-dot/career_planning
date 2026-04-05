import os
import uuid
from datetime import datetime
from typing import Dict

from jinja2 import Template

# 可选：如果你装了 weasyprint
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except Exception:
    WEASYPRINT_AVAILABLE = False


OUTPUT_DIR = "backend/output"


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_html(report: Dict) -> str:
    """将标准 section-based JSON 转换为 HTML"""

    template_str = """
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, "Microsoft YaHei"; padding: 40px; }
            h1 { text-align: center; }
            h2 { margin-top: 30px; border-bottom: 2px solid #ccc; padding-bottom: 5px; }
            p { line-height: 1.8; }
        </style>
    </head>
    <body>
        <h1>职业生涯发展报告</h1>

        <p><strong>学生ID：</strong>{{ meta.student_id }}</p>
        <p><strong>目标岗位：</strong>{{ meta.target_job }}</p>
        <p><strong>生成时间：</strong>{{ meta.generated_at }}</p>

        {% for sec in sections %}
            <h2>{{ loop.index }}. {{ sec.title }}</h2>
            <p>{{ sec.content }}</p>
        {% endfor %}

    </body>
    </html>
    """

    template = Template(template_str)
    return template.render(
        meta=report["meta"],
        sections=report["sections"]
    )


def export_html(report: Dict) -> str:
    """导出 HTML 文件"""

    ensure_output_dir()

    file_id = str(uuid.uuid4())[:8]
    filename = f"report_{file_id}.html"
    file_path = os.path.join(OUTPUT_DIR, filename)

    html_content = build_html(report)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return file_path


def export_pdf(report: Dict) -> str:
    """导出 PDF"""

    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint 未安装，请先 pip install weasyprint")

    ensure_output_dir()

    file_id = str(uuid.uuid4())[:8]
    filename = f"report_{file_id}.pdf"
    file_path = os.path.join(OUTPUT_DIR, filename)

    html_content = build_html(report)

    HTML(string=html_content).write_pdf(file_path)

    return file_path


def export_report(report: Dict, format: str = "pdf") -> str:
    """统一导出入口"""

    if format == "html":
        return export_html(report)

    if format == "pdf":
        return export_pdf(report)

    raise ValueError(f"Unsupported format: {format}")
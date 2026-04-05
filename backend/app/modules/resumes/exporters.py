from __future__ import annotations

from html import escape
from typing import Any

from app.core.exceptions import AppException
from app.modules.reporting.exporters import _safe_slug
from app.modules.resumes.schema import ResumeDetail, ResumeExportPayload


CJK_FONT_STACK = '"Noto Sans CJK SC", "Noto Sans SC", "Microsoft YaHei", "PingFang SC", "SimSun", sans-serif'


def _template_css() -> str:
    return f"""
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: #f4f7fb;
      color: #15202b;
      font-family: {CJK_FONT_STACK};
      line-height: 1.6;
      font-size: 14px;
    }}
    .resume-document {{
      max-width: 900px;
      margin: 0 auto;
      padding: 28px 24px 40px;
    }}
    .hero {{
      padding: 24px 28px;
      border-radius: 20px;
      background: linear-gradient(135deg, #0f172a 0%, #155e75 60%, #38bdf8 100%);
      color: #eff6ff;
    }}
    .hero h1 {{ margin: 0 0 8px; font-size: 30px; }}
    .hero p {{ margin: 0; color: rgba(239, 246, 255, 0.9); }}
    .meta-grid {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }}
    .meta-card, .section-card {{
      background: #ffffff;
      border: 1px solid #dbe5f0;
      border-radius: 16px;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
    }}
    .meta-card {{ padding: 14px 16px; }}
    .meta-label {{ display:block; margin-bottom: 6px; color:#4b5563; font-size:11px; text-transform:uppercase; letter-spacing:0.1em; }}
    .meta-value {{ font-size: 17px; font-weight: 700; color:#0f172a; }}
    .section-card {{ margin-top: 18px; padding: 20px 22px; }}
    .section-card h2 {{ margin: 0 0 12px; font-size: 20px; color:#0f172a; }}
    .section-card h3 {{ margin: 12px 0 8px; font-size: 15px; color:#1d4ed8; }}
    p, ul {{ margin: 0 0 10px; }}
    ul {{ padding-left: 20px; }}
    li + li {{ margin-top: 6px; }}
    .footer-note {{ margin-top: 18px; color:#64748b; font-size: 12px; text-align: right; }}
    @media (max-width: 720px) {{ .meta-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    """


def build_resume_html(resume: ResumeDetail) -> str:
    content = resume.content

    def render_list(items: list[str]) -> str:
        if not items:
            return "<p>暂无补充内容</p>"
        return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"

    def render_projects() -> str:
        if not content.projects:
            return "<p>暂无项目经历</p>"
        blocks: list[str] = []
        for item in content.projects:
            stack = "、".join(item.tech_stack)
            stack_html = f"<p><strong>技术栈：</strong>{escape(stack)}</p>" if stack else ""
            blocks.append(
                "<article>"
                f"<h3>{escape(item.name)}</h3>"
                f"<p><strong>角色：</strong>{escape(item.role or '项目成员')}</p>"
                f"{stack_html}"
                f"{render_list(item.highlights)}"
                "</article>"
            )
        return "".join(blocks)

    def render_internships() -> str:
        if not content.internships:
            return "<p>暂无实习经历</p>"
        blocks: list[str] = []
        for item in content.internships:
            duration_html = f"<p><strong>时长：</strong>{escape(item.duration)}</p>" if item.duration else ""
            blocks.append(
                "<article>"
                f"<h3>{escape(item.company or '实习单位')}</h3>"
                f"<p><strong>岗位：</strong>{escape(item.role or '实习生')}</p>"
                f"{duration_html}"
                f"{render_list(item.highlights)}"
                "</article>"
            )
        return "".join(blocks)

    education_html = "".join(
        (
            "<article>"
            f"<h3>{escape(item.school or '教育经历')}</h3>"
            f"<p>{escape(' / '.join(part for part in [item.major, item.education, item.grade] if part))}</p>"
            f"{render_list(item.highlights)}"
            "</article>"
        )
        for item in content.education
    ) or "<p>暂无教育经历</p>"

    return (
        "<!doctype html>"
        '<html lang="zh-CN">'
        "<head>"
        '<meta charset="utf-8"/>'
        f"<title>{escape(content.basic_info.student_name or resume.student_id)} - {escape(resume.target_job)}</title>"
        f"<style>{_template_css()}</style>"
        "</head>"
        "<body>"
        '<div class="resume-document">'
        '<header class="hero">'
        f"<h1>{escape(content.basic_info.student_name or resume.student_id)}</h1>"
        f"<p>{escape(resume.target_job)} · {escape(content.job_intention.target_city or '校园招聘定制简历')}</p>"
        "</header>"
        '<section class="meta-grid">'
        f'<article class="meta-card"><span class="meta-label">学生 ID</span><div class="meta-value">{escape(resume.student_id)}</div></article>'
        f'<article class="meta-card"><span class="meta-label">学校</span><div class="meta-value">{escape(content.basic_info.school or "未填写")}</div></article>'
        f'<article class="meta-card"><span class="meta-label">专业</span><div class="meta-value">{escape(content.basic_info.major or "未填写")}</div></article>'
        f'<article class="meta-card"><span class="meta-label">学历 / 年级</span><div class="meta-value">{escape(" / ".join(part for part in [content.basic_info.education, content.basic_info.grade] if part) or "未填写")}</div></article>'
        '</section>'
        f'<section class="section-card"><h2>求职意向</h2><p>{escape(content.job_intention.target_job)}</p><p>{escape(content.job_intention.target_city or "")}</p></section>'
        f'<section class="section-card"><h2>个人概述</h2><p>{escape(content.summary)}</p></section>'
        f'<section class="section-card"><h2>教育经历</h2>{education_html}</section>'
        f'<section class="section-card"><h2>专业技能</h2>{render_list(content.skills)}</section>'
        f'<section class="section-card"><h2>项目经历</h2>{render_projects()}</section>'
        f'<section class="section-card"><h2>实习经历</h2>{render_internships()}</section>'
        f'<section class="section-card"><h2>补充信息</h2>{render_list(content.extras)}</section>'
        f'<p class="footer-note">Resume ID: {resume.resume_id}</p>'
        '</div>'
        '</body>'
        '</html>'
    )


def build_export_payload(resume: ResumeDetail | dict[str, Any], export_format: str) -> ResumeExportPayload:
    resume = resume if isinstance(resume, ResumeDetail) else ResumeDetail.model_validate(resume)
    normalized_format = export_format.lower().strip()
    filename_base = _safe_slug(f"{resume.student_id}-{resume.target_job}-{resume.resume_id}")
    if normalized_format == "markdown":
        return ResumeExportPayload(
            format="markdown",
            filename=f"{filename_base}.md",
            media_type="text/markdown; charset=utf-8",
            content=resume.markdown_content,
        )
    if normalized_format == "html":
        return ResumeExportPayload(
            format="html",
            filename=f"{filename_base}.html",
            media_type="text/html; charset=utf-8",
            content=build_resume_html(resume),
        )
    if normalized_format == "json":
        return ResumeExportPayload(
            format="json",
            filename=f"{filename_base}.json",
            media_type="application/json",
            content=resume.content.model_dump(mode="json"),
        )
    raise AppException(
        message=f"Unsupported resume export format: {export_format}",
        error_code="resume_export_format_not_supported",
        status_code=400,
    )

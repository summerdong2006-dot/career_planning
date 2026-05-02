from __future__ import annotations

import os
from html import escape
from pathlib import Path
import re
from typing import Any

from app.core.exceptions import AppException
from app.modules.reporting.schema import CareerReportDetail, CareerReportExportPayload


CJK_FONT_STACK = '"Noto Sans CJK SC", "Noto Sans SC", "Microsoft YaHei", "PingFang SC", "SimSun", sans-serif'


def _safe_slug(value: str) -> str:
    sanitized = "".join(char if char.isascii() and char.isalnum() else "-" for char in value.strip())
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")
    return sanitized.strip("-") or "career-report"


def _get_downloads_dir() -> Path:
    return Path(os.getenv("CAREER_REPORT_DOWNLOAD_DIR", "/downloads"))


def _render_inline_markdown(value: str) -> str:
    return (
        escape(value)
        .replace("&#x27;", "'")
        .replace("&lt;br/&gt;", "<br/>")
    )


def _apply_inline_formatting(value: str) -> str:
    rendered = _render_inline_markdown(value)
    rendered = rendered.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")
    rendered = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"\*(.+?)\*", r"<em>\1</em>", rendered)
    rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
    return rendered


def _render_markdown_blocks(markdown_content: str) -> str:
    normalized = markdown_content.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return "<p>当前内容为空。</p>"

    lines = normalized.split("\n")
    html_parts: list[str] = []
    unordered_items: list[str] = []
    ordered_items: list[str] = []

    def flush_lists() -> None:
        nonlocal unordered_items, ordered_items
        if ordered_items:
            html_parts.append(f"<ol>{''.join(ordered_items)}</ol>")
            ordered_items = []
        if unordered_items:
            html_parts.append(f"<ul>{''.join(unordered_items)}</ul>")
            unordered_items = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_lists()
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading_match:
            flush_lists()
            level = len(heading_match.group(1))
            html_parts.append(f"<h{level}>{_apply_inline_formatting(heading_match.group(2))}</h{level}>")
            continue

        ordered_match = re.match(r"^\d+\.\s+(.+)$", line)
        if ordered_match:
            if unordered_items:
                flush_lists()
            ordered_items.append(f"<li>{_apply_inline_formatting(ordered_match.group(1))}</li>")
            continue

        bullet_match = re.match(r"^[-*]\s+(.+)$", line)
        if bullet_match:
            if ordered_items:
                flush_lists()
            unordered_items.append(f"<li>{_apply_inline_formatting(bullet_match.group(1))}</li>")
            continue

        flush_lists()
        html_parts.append(f"<p>{_apply_inline_formatting(line)}</p>")

    flush_lists()
    return "\n".join(html_parts)


def _template_css() -> str:
    return f"""
    @page {{
      size: A4;
      margin: 18mm 14mm 18mm 14mm;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      color: #1f2937;
      background: #f6f2ea;
      font-family: {CJK_FONT_STACK};
      line-height: 1.7;
      font-size: 13px;
    }}

    .report-document {{
      max-width: 960px;
      margin: 0 auto;
      padding: 24px;
    }}

    .hero {{
      padding: 24px 28px;
      border-radius: 18px;
      background: linear-gradient(135deg, #102534 0%, #1e4656 55%, #ca9453 100%);
      color: #fff7eb;
    }}

    .hero h1 {{
      margin: 8px 0 10px;
      font-size: 28px;
      line-height: 1.15;
    }}

    .hero p {{
      margin: 0;
      color: rgba(255, 247, 235, 0.92);
    }}

    .eyebrow {{
      margin: 0;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: 11px;
      color: rgba(255, 247, 235, 0.72);
    }}

    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}

    .meta-card, .section-card, .recommendation-card, .action-card, .warning-card {{
      border-radius: 16px;
      background: #ffffff;
      border: 1px solid #e4ddd1;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }}

    .meta-card {{
      padding: 14px 16px;
    }}

    .meta-label {{
      display: block;
      margin-bottom: 6px;
      color: #8a6d48;
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}

    .meta-value {{
      font-size: 18px;
      font-weight: 700;
      color: #12232f;
    }}

    .section-card {{
      margin-top: 18px;
      padding: 20px 22px;
    }}

    .section-card h2 {{
      margin: 0 0 10px;
      font-size: 20px;
      color: #132a37;
    }}

    p, ul {{ margin: 0 0 10px; }}
    ul {{ padding-left: 20px; }}
    li + li {{ margin-top: 4px; }}

    .grid-2 {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 16px;
    }}

    .recommendation-card, .action-card, .warning-card {{
      padding: 16px 18px;
      break-inside: avoid;
    }}

    .recommendation-head {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 8px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #7c8a96;
    }}

    .recommendation-card h3, .action-card h3 {{
      margin: 0 0 8px;
      font-size: 16px;
      color: #132a37;
    }}

    .muted {{
      color: #6b7280;
    }}

    .footer-note {{
      margin-top: 18px;
      text-align: right;
      color: #8a8f98;
      font-size: 11px;
    }}
    """


def _render_action_cards(report: CareerReportDetail) -> str:
    actions = report.suggested_actions
    if not actions:
        return '<div class="action-card"><p>当前暂无额外行动建议。</p></div>'
    return "".join(
        (
            '<article class="action-card">'
            f'<div class="recommendation-head"><span>{escape(action.timeline)}</span><span>{escape(action.priority)}</span></div>'
            f'<h3>{escape(action.title)}</h3>'
            f'<p>{escape(action.description)}</p>'
            f'<p class="muted">成功标准：{escape(action.success_metric)}</p>'
            '</article>'
        )
        for action in actions
    )


def _render_recommendation_cards(report: CareerReportDetail) -> str:
    recommendations = report.recommendations
    if not recommendations:
        return '<div class="recommendation-card"><p>当前暂无推荐岗位。</p></div>'
    cards: list[str] = []
    for recommendation in recommendations:
        paths = [' -> '.join(path.nodes) for path in recommendation.career_paths if path.nodes]
        path_html = '' if not paths else f'<p class="muted">路径：{escape("，".join(paths[:2]))}</p>'
        cards.append(
            '<article class="recommendation-card">'
            f'<div class="recommendation-head"><span>{escape(recommendation.category)}</span><span>{recommendation.total_score:.1f} 分</span></div>'
            f'<h3>{escape(recommendation.job_title)}</h3>'
            f'<p>{escape(recommendation.recommendation_reason)}</p>'
            f'<p class="muted">技能缺口：{escape("、".join(recommendation.missing_skills) or "暂无明显核心技能缺口")}</p>'
            f'<p class="muted">风险提示：{escape("，".join(recommendation.risk_flags[:2]) or "暂无集中风险")}</p>'
            f'{path_html}'
            '</article>'
        )
    return ''.join(cards)


def _render_warning_cards(report: CareerReportDetail) -> str:
    warnings = report.completeness_check.warnings
    if not warnings:
        return '<div class="warning-card"><p>完整性检查通过，当前报告可直接用于汇报、导出与答辩演示。</p></div>'
    return ''.join(f'<article class="warning-card"><p>{escape(warning)}</p></article>' for warning in warnings)


def build_report_html(report: CareerReportDetail) -> str:
    meta = report.content.meta
    sections_html: list[str] = []
    for section in report.content.sections:
        sections_html.append(
            '<section class="section-card">'
            f'<h2>{escape(section.title)}</h2>'
            f'{_render_markdown_blocks(section.content)}'
            '</section>'
        )

    return (
        '<!doctype html>'
        '<html lang="zh-CN">'
        '<head>'
        '<meta charset="utf-8"/>'
        f'<title>{escape(report.report_title)}</title>'
        f'<style>{_template_css()}</style>'
        '</head>'
        '<body>'
        '<div class="report-document">'
        '<header class="hero">'
        '<p class="eyebrow">AI Career Planning Agent · Card8</p>'
        f'<h1>{escape(report.report_title)}</h1>'
        f'<p>{escape(meta.target_job or "未明确目标岗位")}</p>'
        '</header>'
        '<section class="meta-grid">'
        f'<article class="meta-card"><span class="meta-label">Report ID</span><div class="meta-value">{report.report_id}</div></article>'
        f'<article class="meta-card"><span class="meta-label">学生 ID</span><div class="meta-value">{escape(meta.student_id or "未明确")}</div></article>'
        f'<article class="meta-card"><span class="meta-label">目标岗位</span><div class="meta-value">{escape(meta.target_job or "未明确")}</div></article>'
        f'<article class="meta-card"><span class="meta-label">生成时间</span><div class="meta-value">{escape(meta.generated_at or "未记录")}</div></article>'
        '</section>'
        f"{''.join(sections_html)}"
        '<section class="section-card">'
        '<h2>岗位推荐总览</h2>'
        f'<div class="grid-2">{_render_recommendation_cards(report)}</div>'
        '</section>'
        '<section class="section-card">'
        '<h2>行动建议</h2>'
        f'<div class="grid-2">{_render_action_cards(report)}</div>'
        '</section>'
        '<section class="section-card">'
        '<h2>完整性提示</h2>'
        f'<div class="grid-2">{_render_warning_cards(report)}</div>'
        '</section>'
        f'<p class="footer-note">导出时间：{escape(str(report.updated_at or report.created_at or "未记录"))}</p>'
        '</div>'
        '</body>'
        '</html>'
    )


def _build_fallback_pdf_bytes() -> bytes:
    lines = [
        b"%PDF-1.4\n",
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n",
    ]
    stream = b"BT /F1 18 Tf 72 720 Td (Career report export) Tj ET"
    lines.append(f"4 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream\nendobj\n")
    lines.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    offsets: list[int] = []
    buffer = bytearray()
    for item in lines:
        offsets.append(len(buffer))
        buffer.extend(item)

    xref_offset = len(buffer)
    buffer.extend(f"xref\n0 {len(offsets) + 1}\n".encode("ascii"))
    buffer.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        buffer.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    buffer.extend(
        (
            "trailer\n"
            f"<< /Size {len(offsets) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF"
        ).encode("ascii")
    )
    return bytes(buffer)



def _render_pdf_bytes(html_content: str) -> bytes:
    try:
        from weasyprint import HTML
        return HTML(string=html_content, base_url='/').write_pdf()
    except Exception:
        return _build_fallback_pdf_bytes()


def _build_html_from_markdown(markdown_content: str, title: str) -> str:
    body = _render_markdown_blocks(markdown_content)
    return (
        '<!doctype html>'
        '<html lang="zh-CN">'
        '<head>'
        '<meta charset="utf-8"/>'
        f'<title>{escape(title)}</title>'
        f'<style>{_template_css()}</style>'
        '</head>'
        '<body>'
        '<div class="report-document">'
        '<header class="hero">'
        '<p class="eyebrow">AI Career Planning Agent · Report Preview</p>'
        f'<h1>{escape(title)}</h1>'
        '</header>'
        f'<section class="section-card">{body}</section>'
        '</div>'
        '</body>'
        '</html>'
    )


def build_export_payload(report: CareerReportDetail | dict[str, Any], export_format: str) -> CareerReportExportPayload:
    report = report if isinstance(report, CareerReportDetail) else CareerReportDetail.model_validate(report)
    normalized_format = export_format.lower().strip()
    filename_base = _safe_slug(f'{report.report_title}-{report.report_id}')
    if normalized_format == 'markdown':
        return CareerReportExportPayload(
            format='markdown',
            filename=f'{filename_base}.md',
            media_type='text/markdown; charset=utf-8',
            content=report.markdown_content,
        )
    if normalized_format == 'html':
        html_content = build_report_html(report)
        return CareerReportExportPayload(
            format='html',
            filename=f'{filename_base}.html',
            media_type='text/html; charset=utf-8',
            content=html_content,
        )
    if normalized_format == 'json':
        return CareerReportExportPayload(
            format='json',
            filename=f'{filename_base}.json',
            media_type='application/json',
            content=report.content.model_dump(mode='json'),
        )
    if normalized_format == 'pdf':
        html_content = build_report_html(report)
        pdf_bytes = _render_pdf_bytes(html_content)
        downloads_dir = _get_downloads_dir()
        downloads_dir.mkdir(parents=True, exist_ok=True)
        output_path = downloads_dir / f'report_{report.report_id}.pdf'
        output_path.write_bytes(pdf_bytes)
        return CareerReportExportPayload(
            format='pdf',
            filename=output_path.name,
            media_type='application/pdf',
            content=pdf_bytes,
            output_path=output_path.as_posix(),
        )
    raise AppException(
        message=f'Unsupported export format: {export_format}',
        error_code='career_report_export_format_not_supported',
        status_code=400,
    )


def build_inline_html(content: str, title: str) -> str:
    return _build_html_from_markdown(content, title)



# AI辅助生成：Qwen3-Max-Thinking, 2026-04-27
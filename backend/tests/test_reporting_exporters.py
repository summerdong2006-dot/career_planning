from app.modules.reporting.exporters import build_inline_html


def test_build_inline_html_renders_markdown_blocks_and_inline_formatting():
    markdown = "\n".join(
        [
            "# 职业报告",
            "",
            "## 一、总体评估",
            "",
            "这是一段 **加粗**、*强调* 和 `代码` 内容。",
            "",
            "1. 第一条行动建议",
            "2. 第二条行动建议",
            "",
            "- 技能补齐",
            "* 项目优化",
        ]
    )

    html = build_inline_html(markdown, "职业报告")

    assert "<h1>职业报告</h1>" in html
    assert "<h2>一、总体评估</h2>" in html
    assert "<strong>加粗</strong>" in html
    assert "<em>强调</em>" in html
    assert "<code>代码</code>" in html
    assert "<ol><li>第一条行动建议</li><li>第二条行动建议</li></ol>" in html
    assert "<ul><li>技能补齐</li><li>项目优化</li></ul>" in html


def test_build_inline_html_preserves_paragraph_breaks_without_pre_wrapper():
    markdown = "第一段\n\n第二段"

    html = build_inline_html(markdown, "段落测试")

    assert "<pre>" not in html
    assert "<p>第一段</p>" in html
    assert "<p>第二段</p>" in html

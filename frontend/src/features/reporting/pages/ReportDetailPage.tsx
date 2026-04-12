import { useEffect, useMemo, useState } from "react";

import { toSafeDisplayList, toSafeDisplayText } from "../../../shared/encoding";
import { renderMarkdownToHtml } from "../../../shared/markdown";
import { downloadReport, getReportDetail, updateReportSection } from "../api";
import type {
  CareerReportDetail,
  DemoExportFormat,
  ReportEditorSection,
  ReportSectionPutRequest
} from "../types";

type RequestState = "idle" | "loading" | "saving" | "success" | "error";

type ReportDetailPageProps = {
  reportId: number;
  onNavigateHome: () => void;
  onOpenReport: (reportId: number) => void;
};

const demoExportFormats: DemoExportFormat[] = ["html", "json", "pdf"];

const sectionTitleMap: Record<string, string> = {
  summary: "总体评估",
  match: "岗位匹配分析",
  gap: "能力差距分析",
  plan_short: "短期提升建议",
  plan_mid: "中期发展路径"
};

function buildEditableSections(report: CareerReportDetail): ReportEditorSection[] {
  if (report.editor_state.sections.length > 0) {
    return report.editor_state.sections;
  }

  return report.content.sections.map((section) => ({
    content: section.content,
    section_key: section.key,
    title: section.title
  }));
}

function indexSections(sections: ReportEditorSection[]): Record<string, ReportEditorSection> {
  return Object.fromEntries(sections.map((section) => [section.section_key, section]));
}

function formatDate(value: string | null): string {
  if (!value) {
    return "未记录";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString("zh-CN", {
    hour12: false
  });
}

function downloadBlob(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

function isPositiveInteger(value: string): boolean {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0;
}

function safeSectionTitle(section: ReportEditorSection): string {
  return toSafeDisplayText(section.title, sectionTitleMap[section.section_key] ?? "未命名章节");
}

function safeSectionContent(section: ReportEditorSection): string {
  return toSafeDisplayText(section.content, "该部分内容当前不可直接展示，你可以手动编辑成更适合 Demo 的版本。", {
    allowAscii: true
  });
}

export function ReportDetailPage({ reportId, onNavigateHome, onOpenReport }: ReportDetailPageProps) {
  const [report, setReport] = useState<CareerReportDetail | null>(null);
  const [draftsByKey, setDraftsByKey] = useState<Record<string, ReportEditorSection>>({});
  const [currentSectionKey, setCurrentSectionKey] = useState("");
  const [requestState, setRequestState] = useState<RequestState>("loading");
  const [message, setMessage] = useState(`正在加载报告 ${reportId}。`);
  const [quickReportId, setQuickReportId] = useState(String(reportId));

  const originalSections = report ? buildEditableSections(report) : [];
  const originalByKey = indexSections(originalSections);
  const sections = originalSections.map((section) => draftsByKey[section.section_key] ?? section);
  const currentSection =
    sections.find((section) => section.section_key === currentSectionKey) ?? sections[0] ?? null;
  const currentOriginal = currentSection ? originalByKey[currentSection.section_key] : undefined;
  const dirtyCount = sections.filter((section) => {
    const original = originalByKey[section.section_key];
    return original && original.content !== section.content;
  }).length;
  const supportedExportFormats = report
    ? report.editor_state.supported_export_formats.filter(
        (format): format is DemoExportFormat => demoExportFormats.includes(format as DemoExportFormat)
      )
    : demoExportFormats;

  const hydrateReport = (nextReport: CareerReportDetail, nextMessage: string) => {
    const nextSections = buildEditableSections(nextReport).map((section) => ({
      ...section,
      title: safeSectionTitle(section),
      content: safeSectionContent(section)
    }));

    setReport(nextReport);
    setDraftsByKey(indexSections(nextSections));
    setCurrentSectionKey((previousKey) => {
      if (nextSections.some((section) => section.section_key === previousKey)) {
        return previousKey;
      }

      return nextSections[0]?.section_key ?? "";
    });
    setRequestState("success");
    setMessage(nextMessage);
  };

  const loadReport = async (targetReportId: number) => {
    setRequestState("loading");
    setMessage(`正在加载报告 ${targetReportId}。`);

    try {
      const nextReport = await getReportDetail(targetReportId);
      hydrateReport(nextReport, `报告 ${nextReport.report_id} 已加载，可以直接用于 Demo 展示。`);
    } catch (error) {
      setReport(null);
      setDraftsByKey({});
      setCurrentSectionKey("");
      setRequestState("error");
      setMessage(error instanceof Error ? error.message : "加载报告失败。");
    }
  };

  useEffect(() => {
    setQuickReportId(String(reportId));
    void loadReport(reportId);
  }, [reportId]);

  const handleDraftChange = (value: string) => {
    if (!currentSection) {
      return;
    }

    setDraftsByKey((currentDrafts) => ({
      ...currentDrafts,
      [currentSection.section_key]: {
        ...currentSection,
        content: value
      }
    }));
  };

  const handleRefresh = async () => {
    await loadReport(reportId);
  };

  const handleSaveCurrentSection = async () => {
    if (!report || !currentSection || !currentOriginal) {
      return;
    }

    if (currentSection.content === currentOriginal.content) {
      setRequestState("success");
      setMessage(`章节「${currentSection.title}」暂无变更。`);
      return;
    }

    const payload: ReportSectionPutRequest = {
      content: currentSection.content
    };

    setRequestState("saving");
    setMessage(`正在保存章节「${currentSection.title}」。`);

    try {
      const nextReport = await updateReportSection(report.report_id, currentSection.section_key, payload);
      hydrateReport(nextReport, `章节「${currentSection.title}」保存成功。`);
    } catch (error) {
      setRequestState("error");
      setMessage(error instanceof Error ? error.message : "保存章节失败。");
    }
  };

  const handleExport = async (format: DemoExportFormat) => {
    if (!report) {
      return;
    }

    setRequestState("loading");
    setMessage(`正在导出 ${format.toUpperCase()}。`);

    try {
      const result = await downloadReport(report.report_id, format);
      downloadBlob(result.blob, result.filename);
      setRequestState("success");
      setMessage(`${format.toUpperCase()} 导出已开始。`);
    } catch (error) {
      setRequestState("error");
      setMessage(error instanceof Error ? error.message : "导出失败。");
    }
  };

  const handleOpenAnotherReport = () => {
    if (!isPositiveInteger(quickReportId)) {
      setRequestState("error");
      setMessage("report_id 必须是正整数。");
      return;
    }

    onOpenReport(Number(quickReportId));
  };

  const safeWarnings = useMemo(
    () => toSafeDisplayList(report?.completeness_check.warnings, "当前没有额外提示，适合继续演示。"),
    [report]
  );

  const safeRecommendations = useMemo(() => {
    return (report?.recommendations ?? []).slice(0, 3).map((recommendation) => ({
      ...recommendation,
      category: toSafeDisplayText(recommendation.category, "推荐"),
      job_title: toSafeDisplayText(recommendation.job_title, "目标岗位"),
      recommendation_reason: toSafeDisplayText(recommendation.recommendation_reason, "该岗位与当前学生画像存在一定匹配度，适合继续作为推荐方向展示。")
    }));
  }, [report]);

  const safeActions = useMemo(() => {
    return (report?.suggested_actions ?? []).slice(0, 4).map((action) => ({
      ...action,
      title: toSafeDisplayText(action.title, "补充关键能力证据"),
      description: toSafeDisplayText(action.description, "围绕目标岗位补充项目、技能和实践材料，以提升投递转化率。"),
      timeline: toSafeDisplayText(action.timeline, "近期"),
      priority: toSafeDisplayText(action.priority, "medium", { allowAscii: true })
    }));
  }, [report]);

  const previewHtml = useMemo(
    () => renderMarkdownToHtml(currentSection?.content ?? "", '<p class="preview-empty">当前章节内容为空。</p>'),
    [currentSection]
  );

  return (
    <main className="app-shell report-reader">
      <section className="hero-card glass-card report-hero report-reader-hero">
        <div className="report-hero__copy">
          <p className="eyebrow">Report Detail</p>
          <h1>{toSafeDisplayText(report?.report_title, `职业报告 #${reportId}`)}</h1>
          <p className="hero-copy">在这里查看完整职业发展建议，梳理优势、差距与下一步行动，并按需要微调报告内容。</p>
        </div>
        <div className="report-hero__side">
          <aside className={`status-panel status-panel--${requestState}`}>
            <span>当前状态</span>
            <strong>{message}</strong>
          </aside>
          <div className="report-cover-stack" aria-hidden="true">
            <span className="report-cover-stack__sheet report-cover-stack__sheet--back" />
            <span className="report-cover-stack__sheet report-cover-stack__sheet--front">
              <i />
              <i />
              <i />
            </span>
          </div>
        </div>
      </section>

      <section className="editor-panel glass-card report-reader-panel">
        <div className="toolbar-row report-toolbar">
          <div className="toolbar-inline">
            <button className="ghost-button" onClick={onNavigateHome} type="button">
              返回报告工作台
            </button>
            <button className="secondary-button" onClick={handleRefresh} type="button">
              重新加载
            </button>
          </div>

          <div className="toolbar-inline">
            <input
              className="text-input"
              onChange={(event) => setQuickReportId(event.target.value)}
              style={{ width: 150 }}
              type="number"
              value={quickReportId}
            />
            <button className="secondary-button" onClick={handleOpenAnotherReport} type="button">
              切换报告
            </button>
          </div>

          <div className="toolbar-inline">
            {supportedExportFormats.map((format) => (
              <button
                className="secondary-button"
                disabled={!report}
                key={format}
                onClick={() => void handleExport(format)}
                type="button"
              >
                导出 {format.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {report ? (
          <>
            <div className="meta-grid report-meta-grid">
              <article className="meta-card report-meta-card">
                <span className="eyebrow">Student</span>
                <strong>{toSafeDisplayText(report.content.meta.student_id, "未填写", { allowAscii: true })}</strong>
              </article>
              <article className="meta-card report-meta-card">
                <span className="eyebrow">Target Job</span>
                <strong>{toSafeDisplayText(report.content.meta.target_job, "待补充")}</strong>
              </article>
              <article className="meta-card report-meta-card">
                <span className="eyebrow">Generated</span>
                <strong>{toSafeDisplayText(report.content.meta.generated_at, formatDate(report.created_at), { allowAscii: true })}</strong>
              </article>
              <article className="meta-card report-meta-card">
                <span className="eyebrow">Version</span>
                <strong>v{report.report_version} / {toSafeDisplayText(report.status, "draft", { allowAscii: true })}</strong>
              </article>
            </div>

            <div className="detail-layout report-detail-layout">
              <aside className="nav-section glass-card report-section-nav">
                <div className="panel-title">
                  <p className="eyebrow">Sections</p>
                  <h3>章节导航</h3>
                  <p className="muted-text">每个章节都可以单独查看和编辑，适合快速润色内容。</p>
                </div>

                <div className="section-list">
                  {sections.map((section) => {
                    const original = originalByKey[section.section_key];
                    const isDirty = Boolean(original && original.content !== section.content);

                    return (
                      <button
                        className={`nav-button ${section.section_key === currentSection?.section_key ? "nav-button--active" : ""}`}
                        key={section.section_key}
                        onClick={() => setCurrentSectionKey(section.section_key)}
                        type="button"
                      >
                        <div className="section-title-row">
                          <div>
                            <div className="section-meta">{section.section_key}</div>
                            <strong>{section.title}</strong>
                          </div>
                          {isDirty ? <span className="pill">未保存</span> : null}
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div className="stat-grid">
                  <article className="stat-card">
                    <span className="eyebrow">Dirty</span>
                    <strong>{dirtyCount}</strong>
                  </article>
                  <article className="stat-card">
                    <span className="eyebrow">Complete</span>
                    <strong>{Math.round(report.completeness_check.score)}</strong>
                  </article>
                </div>

                <article className="list-card report-warning-card">
                  <p className="eyebrow">Warnings</p>
                  <h4>展示提示</h4>
                  <ul className="warning-list">
                    {safeWarnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                </article>
              </aside>

              <section className="editor-panel glass-card report-paper">
                {currentSection ? (
                  <>
                    <header className="editor-header">
                      <div className="editor-actions">
                        <div className="panel-title">
                          <p className="eyebrow">Current Section</p>
                          <h3>{currentSection.title}</h3>
                          <p className="muted-text">
                            section_key={currentSection.section_key}，更新时间 {formatDate(report.updated_at)}
                          </p>
                        </div>

                        <div className="badge-row">
                          {currentOriginal && currentOriginal.content !== currentSection.content ? (
                            <span className="pill">当前章节有未保存修改</span>
                          ) : (
                            <span className="tag">当前章节已同步</span>
                          )}
                          <button className="primary-button" onClick={() => void handleSaveCurrentSection()} type="button">
                            保存当前章节
                          </button>
                        </div>
                      </div>
                    </header>

                    <div className="editor-split">
                      <label className="field-group">
                        <span className="field-label">章节内容</span>
                        <textarea
                          className="text-area"
                          onChange={(event) => handleDraftChange(event.target.value)}
                          value={currentSection.content}
                        />
                      </label>

                      <article className="preview-card report-preview-card">
                        <div className="panel-title">
                          <p className="eyebrow">Preview</p>
                          <h4>Markdown 预览</h4>
                        </div>
                        <div
                          className="markdown-preview report-markdown"
                          dangerouslySetInnerHTML={{ __html: previewHtml }}
                        />
                      </article>
                    </div>

                    <div className="two-column-grid">
                      <article className="list-card report-related-card">
                        <p className="eyebrow">Recommendations</p>
                        <h4>推荐岗位</h4>
                        <div className="list-stack">
                          {safeRecommendations.length > 0 ? (
                            safeRecommendations.map((recommendation) => (
                              <article className="list-card report-related-item" key={`${recommendation.job_id}-${recommendation.job_title}`}>
                                <div className="badge-row">
                                  <span className="tag">{recommendation.category}</span>
                                  <span className="tag">{recommendation.total_score.toFixed(1)} 分</span>
                                </div>
                                <h4>{recommendation.job_title}</h4>
                                <p className="muted-text">{recommendation.recommendation_reason}</p>
                              </article>
                            ))
                          ) : (
                            <p className="panel-empty">当前没有可展示的岗位推荐数据。</p>
                          )}
                        </div>
                      </article>

                      <article className="list-card report-related-card">
                        <p className="eyebrow">Actions</p>
                        <h4>行动建议</h4>
                        <div className="list-stack">
                          {safeActions.length > 0 ? (
                            safeActions.map((action) => (
                              <article className="list-card report-related-item" key={action.action_id}>
                                <div className="badge-row">
                                  <span className="tag">{action.timeline}</span>
                                  <span className="tag">{action.priority}</span>
                                </div>
                                <h4>{action.title}</h4>
                                <p className="muted-text">{action.description}</p>
                              </article>
                            ))
                          ) : (
                            <p className="panel-empty">当前没有可展示的行动建议。</p>
                          )}
                        </div>
                      </article>
                    </div>
                  </>
                ) : (
                  <article className="empty-card">
                    <h3>报告中没有章节</h3>
                    <p className="panel-empty">当前报告没有可编辑内容，可以返回上一页重新生成报告。</p>
                  </article>
                )}
              </section>
            </div>
          </>
        ) : (
          <article className="empty-card">
            <h3>报告不可用</h3>
            <p className="panel-empty">请返回报告工作台重新生成，或切换到一个存在的 report_id。</p>
          </article>
        )}
      </section>
    </main>
  );
}

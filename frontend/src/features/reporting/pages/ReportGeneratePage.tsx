import { useEffect, useState } from "react";

import { generateReport, getLatestReport, getReportDetail } from "../api";

type RequestState = "idle" | "loading" | "success" | "error";

type ReportGeneratePageProps = {
  initialStudentProfileId?: number;
  onNavigateHome: () => void;
  onOpenReport: (reportId: number) => void;
};

function isPositiveInteger(value: string): boolean {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0;
}

export function ReportGeneratePage({ initialStudentProfileId, onNavigateHome, onOpenReport }: ReportGeneratePageProps) {
  const [studentProfileId, setStudentProfileId] = useState(initialStudentProfileId ? String(initialStudentProfileId) : "");
  const [topK, setTopK] = useState("3");
  const [reportTitle, setReportTitle] = useState("");
  const [reportId, setReportId] = useState("");
  const [requestState, setRequestState] = useState<RequestState>("idle");
  const [message, setMessage] = useState(
    initialStudentProfileId
      ? `已自动带入 student_profile_id=${initialStudentProfileId}，可以直接生成职业报告。`
      : "先输入 student_profile_id，再生成职业报告。"
  );

  useEffect(() => {
    if (!initialStudentProfileId) {
      return;
    }

    setStudentProfileId(String(initialStudentProfileId));
    setMessage(`已自动带入 student_profile_id=${initialStudentProfileId}，可以直接生成职业报告。`);
  }, [initialStudentProfileId]);

  const handleGenerate = async () => {
    if (!isPositiveInteger(studentProfileId)) {
      setRequestState("error");
      setMessage("请先输入有效的 student_profile_id。");
      return;
    }

    if (!isPositiveInteger(topK)) {
      setRequestState("error");
      setMessage("top_k 必须是正整数。");
      return;
    }

    setRequestState("loading");
    setMessage("正在生成职业报告，完成后会自动进入报告详情页。");

    try {
      const report = await generateReport({
        reportTitle: reportTitle.trim() || undefined,
        studentProfileId: Number(studentProfileId),
        topK: Number(topK)
      });

      setRequestState("success");
      setMessage(`职业报告已生成，report_id=${report.report_id}。`);
      onOpenReport(report.report_id);
    } catch (error) {
      setRequestState("error");
      setMessage(error instanceof Error ? error.message : "生成职业报告失败。");
    }
  };

  const handleOpenReport = async () => {
    if (!isPositiveInteger(reportId)) {
      setRequestState("error");
      setMessage("请输入有效的 report_id。");
      return;
    }

    setRequestState("loading");
    setMessage(`正在检查报告 ${reportId}。`);

    try {
      const report = await getReportDetail(Number(reportId));
      setRequestState("success");
      setMessage(`报告 ${report.report_id} 可用，正在进入详情页。`);
      onOpenReport(report.report_id);
    } catch (error) {
      setRequestState("error");
      setMessage(error instanceof Error ? error.message : "加载报告失败。");
    }
  };

  const handleOpenLatest = async () => {
    if (!isPositiveInteger(studentProfileId)) {
      setRequestState("error");
      setMessage("请先输入有效的 student_profile_id。");
      return;
    }

    setRequestState("loading");
    setMessage(`正在查找 student_profile_id=${studentProfileId} 的最新报告。`);

    try {
      const report = await getLatestReport(Number(studentProfileId));
      setRequestState("success");
      setMessage(`已定位到最新报告 ${report.report_id}。`);
      onOpenReport(report.report_id);
    } catch (error) {
      setRequestState("error");
      setMessage(error instanceof Error ? error.message : "查询最新报告失败。");
    }
  };

  return (
    <main className="app-shell report-workbench">
      <section className="hero-card glass-card report-hero">
        <div className="report-hero__copy">
          <p className="eyebrow">Career Report</p>
          <h1>职业报告工作台</h1>
          <p className="hero-copy">在这里生成专属职业发展报告，回顾个人画像与目标岗位，并继续查看已有报告。</p>
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

      <section className="report-console-grid">
        <article className="form-card glass-card report-console-card">
          <div className="panel-title">
            <p className="eyebrow">Step 1</p>
            <h2>生成新报告</h2>
            <p className="muted-text">使用学生画像生成一份职业报告，成功后自动跳转到详情页。</p>
          </div>

          <div className="form-grid">
            <label className="field-group">
              <span className="field-label">student_profile_id</span>
              <input
                className="text-input"
                onChange={(event) => setStudentProfileId(event.target.value)}
                type="number"
                value={studentProfileId}
              />
            </label>

            <label className="field-group">
              <span className="field-label">top_k</span>
              <input
                className="text-input"
                max="10"
                min="1"
                onChange={(event) => setTopK(event.target.value)}
                type="number"
                value={topK}
              />
            </label>

            <label className="field-group field-group--full">
              <span className="field-label">report_title（可选）</span>
              <input
                className="text-input"
                onChange={(event) => setReportTitle(event.target.value)}
                placeholder="例如：张三职业发展报告"
                value={reportTitle}
              />
            </label>
          </div>

          <div className="button-row">
            <button className="primary-button" onClick={handleGenerate} type="button">
              生成职业报告
            </button>
            <button className="secondary-button" onClick={handleOpenLatest} type="button">
              打开该学生最新报告
            </button>
            <button className="ghost-button" onClick={onNavigateHome} type="button">
              返回工作台
            </button>
          </div>
        </article>

        <article className="info-card glass-card report-open-card">
          <div className="panel-title">
            <p className="eyebrow">Step 2</p>
            <h2>打开已有报告</h2>
            <p className="muted-text">如果你已经生成过报告，也可以直接输入 `report_id` 进入详情页。</p>
          </div>

          <div className="form-grid form-grid--single">
            <label className="field-group">
              <span className="field-label">report_id</span>
              <input
                className="text-input"
                onChange={(event) => setReportId(event.target.value)}
                type="number"
                value={reportId}
              />
            </label>
          </div>

          <div className="button-row">
            <button className="primary-button" onClick={handleOpenReport} type="button">
              查看报告详情
            </button>
          </div>

          <div className="report-includes">
            <span>职业定位</span>
            <span>能力差距</span>
            <span>行动计划</span>
            <span>风险提醒</span>
          </div>

          <div className="list-stack">
            <article className="list-card report-tip-card">
              <h4>演示建议</h4>
              <p className="muted-text">先在学生画像页生成一个 `student_profile_id`，再回到这里生成职业报告，路径最稳定。</p>
            </article>
          </div>
        </article>
      </section>
    </main>
  );
}

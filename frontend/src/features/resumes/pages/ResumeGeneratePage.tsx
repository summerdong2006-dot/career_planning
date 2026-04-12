import { useEffect, useState } from "react";

import { downloadResume, generateResume, updateResume } from "../api";
import type { ResumeDetail, ResumeExportFormat } from "../types";

type RequestState = "idle" | "loading" | "saving" | "success" | "error";

type ResumeGeneratePageProps = {
  initialStudentProfileId?: number;
  onNavigateHome: () => void;
};

function isPositiveInteger(value: string): boolean {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0;
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

export function ResumeGeneratePage({ initialStudentProfileId, onNavigateHome }: ResumeGeneratePageProps) {
  const [studentProfileId, setStudentProfileId] = useState(initialStudentProfileId ? String(initialStudentProfileId) : "");
  const [targetJob, setTargetJob] = useState("Python 后端开发工程师");
  const [resume, setResume] = useState<ResumeDetail | null>(null);
  const [summaryDraft, setSummaryDraft] = useState("");
  const [skillsDraft, setSkillsDraft] = useState("");
  const [requestState, setRequestState] = useState<RequestState>("idle");
  const [message, setMessage] = useState("输入 student_profile_id 和目标岗位后即可生成定制简历。");

  useEffect(() => {
    if (initialStudentProfileId) {
      setStudentProfileId(String(initialStudentProfileId));
    }
  }, [initialStudentProfileId]);

  const handleGenerate = async () => {
    if (!isPositiveInteger(studentProfileId) || !targetJob.trim()) {
      setRequestState("error");
      setMessage("student_profile_id 必须有效，目标岗位不能为空。");
      return;
    }

    setRequestState("loading");
    setMessage("正在生成定制简历。");

    try {
      const nextResume = await generateResume({
        studentProfileId: Number(studentProfileId),
        targetJob: targetJob.trim()
      });
      setResume(nextResume);
      setSummaryDraft(nextResume.content.summary);
      setSkillsDraft(nextResume.content.skills.join("、"));
      setRequestState("success");
      setMessage(`简历已生成，resume_id=${nextResume.resume_id}。`);
    } catch (error) {
      setRequestState("error");
      setMessage(error instanceof Error ? error.message : "生成简历失败。");
    }
  };

  const handleSave = async () => {
    if (!resume) {
      return;
    }

    setRequestState("saving");
    setMessage("正在保存简历修改。");

    try {
      const nextResume = await updateResume(resume.resume_id, {
        summary: summaryDraft,
        skills: skillsDraft
          .split(/[、,，\n]/)
          .map((item) => item.trim())
          .filter(Boolean)
      });
      setResume(nextResume);
      setSummaryDraft(nextResume.content.summary);
      setSkillsDraft(nextResume.content.skills.join("、"));
      setRequestState("success");
      setMessage("简历内容已更新。");
    } catch (error) {
      setRequestState("error");
      setMessage(error instanceof Error ? error.message : "保存简历失败。");
    }
  };

  const handleExport = async (format: ResumeExportFormat) => {
    if (!resume) {
      return;
    }

    setRequestState("loading");
    setMessage(`正在导出 ${format.toUpperCase()}。`);

    try {
      const result = await downloadResume(resume.resume_id, format);
      downloadBlob(result.blob, result.filename);
      setRequestState("success");
      setMessage(`${format.toUpperCase()} 导出已开始。`);
    } catch (error) {
      setRequestState("error");
      setMessage(error instanceof Error ? error.message : "导出简历失败。");
    }
  };

  return (
    <main className="app-shell resume-workshop">
      <section className="hero-card glass-card resume-hero">
        <div className="resume-hero__copy">
          <p className="eyebrow">Resumes</p>
          <h1>简历工坊</h1>
          <p className="hero-copy">围绕学生画像和目标岗位生成一份技术简历，并允许直接做轻量编辑和导出。</p>
        </div>
        <div className="resume-hero__side">
          <aside className={`status-panel status-panel--${requestState}`}>
            <span>当前状态</span>
            <strong>{message}</strong>
          </aside>
          <div className="resume-paper-stack" aria-hidden="true">
            <span className="resume-paper-stack__sheet resume-paper-stack__sheet--back" />
            <span className="resume-paper-stack__sheet resume-paper-stack__sheet--front">
              <i />
              <i />
              <i />
              <b />
            </span>
          </div>
        </div>
      </section>

      <section className="resume-console-grid">
        <article className="form-card glass-card resume-console-card">
          <div className="panel-title">
            <p className="eyebrow">Input</p>
            <h2>生成参数</h2>
          </div>

          <div className="form-grid">
            <label className="field-group">
              <span className="field-label">student_profile_id</span>
              <input className="text-input" onChange={(event) => setStudentProfileId(event.target.value)} type="number" value={studentProfileId} />
            </label>
            <label className="field-group">
              <span className="field-label">目标岗位</span>
              <input className="text-input" onChange={(event) => setTargetJob(event.target.value)} value={targetJob} />
            </label>
          </div>

          <div className="button-row">
            <button className="primary-button" onClick={() => void handleGenerate()} type="button">
              生成定制简历
            </button>
            <button className="ghost-button" onClick={onNavigateHome} type="button">
              返回工作台
            </button>
          </div>
        </article>

        <article className="info-card glass-card resume-summary-card">
          <div className="panel-title">
            <p className="eyebrow">Preview</p>
            <h2>简历摘要</h2>
          </div>

          {resume ? (
            <div className="list-stack">
              <article className="list-card resume-mini-card resume-mini-card--mint">
                <p className="eyebrow">Identity</p>
                <h4>{resume.content.basic_info.student_name || resume.student_id}</h4>
                <p className="muted-text">{resume.target_job}</p>
              </article>
              <article className="list-card resume-mini-card resume-mini-card--gold">
                <p className="eyebrow">Skills</p>
                <div className="badge-row">
                  {resume.content.skills.map((skill) => (
                    <span className="tag" key={skill}>
                      {skill}
                    </span>
                  ))}
                </div>
              </article>
            </div>
          ) : (
            <div className="empty-card">
              <h3>还没有简历结果</h3>
              <p className="panel-empty">生成后，这里会展示个人摘要、技能和项目经历概览。</p>
            </div>
          )}
        </article>
      </section>

      <section className="detail-layout detail-layout--single resume-detail-shell">
        <section className="editor-panel glass-card resume-editor-panel">
          {resume ? (
            <>
              <header className="editor-header">
                <div className="editor-actions resume-editor-actions">
                  <div className="panel-title">
                    <p className="eyebrow">Editor</p>
                    <h3>简历内容编辑</h3>
                    <p className="muted-text">当前只开放摘要和技能的轻量编辑，先保证网站版本可用。</p>
                  </div>
                  <div className="badge-row">
                    <span className="tag">resume_id={resume.resume_id}</span>
                    <button className="primary-button" onClick={() => void handleSave()} type="button">
                      保存修改
                    </button>
                    {(["markdown", "html", "json"] as ResumeExportFormat[]).map((format) => (
                      <button className="secondary-button" key={format} onClick={() => void handleExport(format)} type="button">
                        导出 {format.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>
              </header>

              <div className="editor-split resume-editor-split">
                <div className="list-stack">
                  <label className="field-group">
                    <span className="field-label">简历摘要</span>
                    <textarea className="text-area resume-textarea" onChange={(event) => setSummaryDraft(event.target.value)} value={summaryDraft} />
                  </label>
                  <label className="field-group">
                    <span className="field-label">技能清单</span>
                    <textarea className="text-area text-area--compact resume-textarea" onChange={(event) => setSkillsDraft(event.target.value)} value={skillsDraft} />
                  </label>
                </div>

                <article className="preview-card resume-preview-paper">
                  <div className="panel-title">
                    <p className="eyebrow">Preview</p>
                    <h4>阅读预览</h4>
                  </div>
                  <p className="preview-body">{summaryDraft || "摘要为空。"}</p>
                  <div className="badge-row">
                    {skillsDraft
                      .split(/[、,，\n]/)
                      .map((item) => item.trim())
                      .filter(Boolean)
                      .map((skill) => (
                        <span className="tag" key={skill}>
                          {skill}
                        </span>
                      ))}
                  </div>
                </article>
              </div>

              <div className="result-grid result-grid--bottom">
                <article className="list-card resume-section-card">
                  <p className="eyebrow">Projects</p>
                  <div className="list-stack">
                    {resume.content.projects.map((project, index) => (
                      <article className="list-card resume-entry-card" key={`${project.name}-${index}`}>
                        <h4>{project.name || `项目经历 ${index + 1}`}</h4>
                        <p className="muted-text">{project.role}</p>
                        <ul className="bullet-list">
                          {project.highlights.map((highlight) => (
                            <li key={highlight}>{highlight}</li>
                          ))}
                        </ul>
                      </article>
                    ))}
                    {!resume.content.projects.length ? <p className="panel-empty">暂无项目经历。</p> : null}
                  </div>
                </article>

                <article className="list-card resume-section-card">
                  <p className="eyebrow">Internships & Extras</p>
                  <div className="list-stack">
                    {resume.content.internships.map((internship, index) => (
                      <article className="list-card resume-entry-card" key={`${internship.company}-${index}`}>
                        <h4>{internship.company || `实习经历 ${index + 1}`}</h4>
                        <p className="muted-text">{internship.role}</p>
                        <ul className="bullet-list">
                          {internship.highlights.map((highlight) => (
                            <li key={highlight}>{highlight}</li>
                          ))}
                        </ul>
                      </article>
                    ))}
                    <article className="list-card resume-entry-card">
                      <h4>补充信息</h4>
                      <ul className="bullet-list">
                        {resume.content.extras.map((extra) => (
                          <li key={extra}>{extra}</li>
                        ))}
                      </ul>
                    </article>
                  </div>
                </article>
              </div>
            </>
          ) : (
            <article className="empty-card">
              <h3>等待生成定制简历</h3>
              <p className="panel-empty">先输入画像 ID 和目标岗位，生成后会在这里展示完整预览。</p>
            </article>
          )}
        </section>
      </section>
    </main>
  );
}

import { useEffect, useState } from "react";

import { getWorkspaceOverview } from "../api";
import type { WorkspaceOverview } from "../types";

type RequestState = "idle" | "loading" | "success" | "error";

type WorkspaceDashboardPageProps = {
  onCreateProfile: () => void;
  onOpenReport: (reportId: number) => void;
  onOpenRecommendations: (studentProfileId?: number) => void;
  onOpenResume: (studentProfileId?: number) => void;
};

function formatDate(value: string | null): string {
  if (!value) {
    return "刚刚";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString("zh-CN", { hour12: false });
}

export function WorkspaceDashboardPage({
  onCreateProfile,
  onOpenReport,
  onOpenRecommendations,
  onOpenResume
}: WorkspaceDashboardPageProps) {
  const [workspace, setWorkspace] = useState<WorkspaceOverview | null>(null);
  const [requestState, setRequestState] = useState<RequestState>("loading");
  const [message, setMessage] = useState("正在加载你的工作台。");

  useEffect(() => {
    const loadWorkspace = async () => {
      setRequestState("loading");
      setMessage("正在同步学生画像、报告和简历记录。");

      try {
        const result = await getWorkspaceOverview();
        setWorkspace(result);
        setRequestState("success");
        setMessage(`已加载 ${result.student_profiles.length} 个学生画像、${result.reports.length} 份报告和 ${result.resumes.length} 份简历。`);
      } catch (error) {
        setRequestState("error");
        setMessage(error instanceof Error ? error.message : "加载工作台失败。");
      }
    };

    void loadWorkspace();
  }, []);

  const latestProfile = workspace?.student_profiles[0];

  return (
    <main className="app-shell">
      <section className="hero-card glass-card">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>职业规划网站工作台</h1>
          <p className="hero-copy">这里集中展示当前账号的学生画像、职业报告和定制简历，并提供一键进入各功能页面的入口。</p>
        </div>
        <aside className={`status-panel status-panel--${requestState}`}>
          <span>当前状态</span>
          <strong>{message}</strong>
        </aside>
      </section>

      <section className="workspace-actions glass-card">
        <button className="primary-button" onClick={onCreateProfile} type="button">
          新建学生画像
        </button>
        <button className="secondary-button" onClick={() => onOpenRecommendations(latestProfile?.profile_id)} type="button">
          查看岗位推荐
        </button>
        <button className="secondary-button" onClick={() => onOpenResume(latestProfile?.profile_id)} type="button">
          生成定制简历
        </button>
        <button
          className="secondary-button"
          onClick={() => (workspace?.reports[0] ? onOpenReport(workspace.reports[0].report_id) : onCreateProfile())}
          type="button"
        >
          打开最近报告
        </button>
      </section>

      <section className="result-grid">
        <article className="info-card glass-card">
          <div className="panel-title">
            <p className="eyebrow">Profiles</p>
            <h2>学生画像</h2>
          </div>
          {workspace?.student_profiles.length ? (
            <div className="list-stack">
              {workspace.student_profiles.map((profile) => (
                <article className="list-card" key={profile.profile_id}>
                  <div className="section-title-row">
                    <h4>画像 #{profile.profile_id}</h4>
                    <span className="tag">v{profile.profile_version}</span>
                  </div>
                  <p className="muted-text">{profile.career_intention || "未填写意向方向"}</p>
                  <p className="muted-text">{profile.summary || "暂无摘要"}</p>
                  <div className="button-row">
                    <button className="secondary-button" onClick={() => onOpenRecommendations(profile.profile_id)} type="button">
                      看推荐
                    </button>
                    <button className="secondary-button" onClick={() => onOpenResume(profile.profile_id)} type="button">
                      做简历
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-card">
              <h3>还没有学生画像</h3>
              <p className="panel-empty">先创建一个学生画像，后面的推荐、报告和简历都会以它为入口。</p>
            </div>
          )}
        </article>

        <article className="info-card glass-card">
          <div className="panel-title">
            <p className="eyebrow">Reports</p>
            <h2>职业报告</h2>
          </div>
          {workspace?.reports.length ? (
            <div className="list-stack">
              {workspace.reports.map((report) => (
                <article className="list-card" key={report.report_id}>
                  <div className="section-title-row">
                    <h4>{report.report_title}</h4>
                    <span className="tag">{report.status}</span>
                  </div>
                  <p className="muted-text">student_profile_id={report.student_profile_id}</p>
                  <p className="muted-text">最近更新：{formatDate(report.updated_at)}</p>
                  <div className="button-row">
                    <button className="primary-button" onClick={() => onOpenReport(report.report_id)} type="button">
                      打开报告
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-card">
              <h3>还没有职业报告</h3>
              <p className="panel-empty">在学生画像和岗位推荐完成后，就可以生成第一份职业发展报告。</p>
            </div>
          )}
        </article>
      </section>

      <section className="result-grid result-grid--bottom">
        <article className="info-card glass-card">
          <div className="panel-title">
            <p className="eyebrow">Resumes</p>
            <h2>定制简历</h2>
          </div>
          {workspace?.resumes.length ? (
            <div className="list-stack">
              {workspace.resumes.map((resume) => (
                <article className="list-card" key={resume.resume_id}>
                  <div className="section-title-row">
                    <h4>简历 #{resume.resume_id}</h4>
                    <span className="tag">{resume.style || "campus"}</span>
                  </div>
                  <p className="muted-text">{resume.target_job || "未填写目标岗位"}</p>
                  <p className="muted-text">创建时间：{formatDate(resume.created_at)}</p>
                  <div className="button-row">
                    <button className="secondary-button" onClick={() => onOpenResume(resume.student_profile_id)} type="button">
                      继续优化
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-card">
              <h3>还没有定制简历</h3>
              <p className="panel-empty">岗位推荐出来后，可以基于目标岗位快速生成一份技术简历。</p>
            </div>
          )}
        </article>

        <article className="info-card glass-card">
          <div className="panel-title">
            <p className="eyebrow">Use Flow</p>
            <h2>推荐使用路径</h2>
          </div>
          <div className="list-stack">
            <article className="list-card">
              <h4>1. 生成学生画像</h4>
              <p className="muted-text">把原始简历文本转成结构化画像，拿到 `student_profile_id`。</p>
            </article>
            <article className="list-card">
              <h4>2. 查看岗位推荐</h4>
              <p className="muted-text">对当前画像做 Top-K 匹配，生成可解释的岗位建议。</p>
            </article>
            <article className="list-card">
              <h4>3. 生成报告与简历</h4>
              <p className="muted-text">根据推荐结果继续产出职业报告和岗位定制简历。</p>
            </article>
          </div>
        </article>
      </section>
    </main>
  );
}

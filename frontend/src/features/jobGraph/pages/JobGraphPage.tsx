import { useEffect, useState } from "react";

import { getJobGraphOverview } from "../api";
import type { JobGraphOverviewResponse } from "../types";

type JobGraphPageProps = {
  onNavigateHome: () => void;
};

export function JobGraphPage({ onNavigateHome }: JobGraphPageProps) {
  const [overview, setOverview] = useState<JobGraphOverviewResponse | null>(null);
  const [message, setMessage] = useState("正在加载岗位图谱数据。");
  const [state, setState] = useState<"loading" | "success" | "error">("loading");

  useEffect(() => {
    const load = async () => {
      try {
        const nextOverview = await getJobGraphOverview(10);
        setOverview(nextOverview);
        setState("success");
        setMessage(`已加载 ${nextOverview.representative_jobs.length} 个代表岗位与 ${nextOverview.graph.edges.length} 条关系边。`);
      } catch (error) {
        setState("error");
        setMessage(error instanceof Error ? error.message : "岗位图谱加载失败。");
      }
    };

    void load();
  }, []);

  return (
    <main className="app-shell">
      <section className="hero-card glass-card">
        <div>
          <p className="eyebrow">Job Graph</p>
          <h1>岗位发展图谱</h1>
          <p className="hero-copy">集中展示代表岗位的核心要求、纵向晋升路径和横向换岗路径，便于演示岗位画像与职业路径规划能力。</p>
        </div>
        <aside className={`status-panel status-panel--${state}`}>
          <span>当前状态</span>
          <strong>{message}</strong>
        </aside>
      </section>

      <section className="two-column-grid">
        <article className="form-card glass-card action-card">
          <div className="panel-title">
            <p className="eyebrow">Overview</p>
            <h2>图谱指标</h2>
          </div>
          <div className="meta-grid meta-grid--compact">
            <article className="meta-card">
              <span>岗位数量</span>
              <strong>{overview?.representative_jobs.length ?? 0}</strong>
            </article>
            <article className="meta-card">
              <span>节点数量</span>
              <strong>{overview?.graph.nodes.length ?? 0}</strong>
            </article>
            <article className="meta-card">
              <span>关系边</span>
              <strong>{overview?.graph.edges.length ?? 0}</strong>
            </article>
          </div>
          <div className="button-row">
            <button className="ghost-button" onClick={onNavigateHome} type="button">
              返回工作台
            </button>
          </div>
        </article>

        <article className="form-card glass-card">
          <div className="panel-title">
            <p className="eyebrow">Edges</p>
            <h2>关系概览</h2>
          </div>
          {overview?.graph.edges.length ? (
            <ul className="bullet-list">
              {overview.graph.edges.slice(0, 12).map((edge) => (
                <li key={`${edge.source_job_id}-${edge.target_job_id}-${edge.type}`}>
                  {String(edge.source_job_id)} → {String(edge.target_job_id)}｜{edge.type}｜{edge.weight.toFixed(1)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="panel-empty">暂无图谱关系数据。</p>
          )}
        </article>
      </section>

      <section className="result-grid">
        <article className="info-card glass-card result-grid-span">
          <div className="panel-title">
            <p className="eyebrow">Representative Jobs</p>
            <h2>代表岗位与路径</h2>
          </div>
          {overview?.representative_jobs.length ? (
            <div className="list-stack">
              {overview.representative_jobs.map((job) => (
                <article className="list-card" key={job.job_profile_id}>
                  <div className="section-title-row">
                    <div>
                      <h4>{job.job_title}</h4>
                      <p className="muted-text">{job.job_level || "未明确"}</p>
                    </div>
                    <div className="badge-row">
                      <span className="tag">job_id={job.job_id}</span>
                    </div>
                  </div>
                  <p className="muted-text">{job.summary || "暂无岗位摘要。"}</p>
                  <div className="result-grid result-grid--inner">
                    <article className="list-card">
                      <p className="eyebrow">Requirement</p>
                      <ul className="bullet-list">
                        <li>核心技能：{job.must_have_skills.slice(0, 5).join("、") || "未明确"}</li>
                        <li>证书要求：{job.certificates.join("、") || "未明确"}</li>
                        <li>晋升链路：{job.promotion_path.join(" -> ") || "未明确"}</li>
                      </ul>
                    </article>
                    <article className="list-card">
                      <p className="eyebrow">Career Paths</p>
                      {job.career_paths.length ? (
                        <ul className="bullet-list">
                          {job.career_paths.map((path, index) => (
                            <li key={`${job.job_id}-${index}`}>{path.join(" -> ")}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="panel-empty">暂无可展示路径。</p>
                      )}
                    </article>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-card">
              <h3>暂无代表岗位</h3>
              <p className="panel-empty">请先确保数据库中已有岗位画像数据。</p>
            </div>
          )}
        </article>
      </section>
    </main>
  );
}

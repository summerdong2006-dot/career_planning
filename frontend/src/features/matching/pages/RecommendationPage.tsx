import { useEffect, useState } from "react";

import { recommendJobs } from "../api";
import type { MatchingRecommendResponse } from "../types";

type RequestState = "idle" | "loading" | "success" | "error";

type RecommendationPageProps = {
  initialStudentProfileId?: number;
  onBackHome: () => void;
  onOpenReportWorkspace: (studentProfileId?: number) => void;
  onOpenResumeWorkspace: (studentProfileId?: number) => void;
};

function isPositiveInteger(value: string): boolean {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0;
}

export function RecommendationPage({
  initialStudentProfileId,
  onBackHome,
  onOpenReportWorkspace,
  onOpenResumeWorkspace
}: RecommendationPageProps) {
  const [studentProfileId, setStudentProfileId] = useState(initialStudentProfileId ? String(initialStudentProfileId) : "");
  const [topK, setTopK] = useState("5");
  const [result, setResult] = useState<MatchingRecommendResponse | null>(null);
  const [requestState, setRequestState] = useState<RequestState>("idle");
  const [message, setMessage] = useState("选择学生画像后即可生成岗位推荐结果。");

  useEffect(() => {
    if (initialStudentProfileId) {
      setStudentProfileId(String(initialStudentProfileId));
    }
  }, [initialStudentProfileId]);

  const handleRecommend = async () => {
    if (!isPositiveInteger(studentProfileId) || !isPositiveInteger(topK)) {
      setRequestState("error");
      setMessage("student_profile_id 和 top_k 都必须是正整数。");
      return;
    }

    setRequestState("loading");
    setMessage("正在计算岗位推荐结果。");

    try {
      const nextResult = await recommendJobs({
        studentProfileId: Number(studentProfileId),
        topK: Number(topK)
      });
      setResult(nextResult);
      setRequestState("success");
      setMessage(`已生成 ${nextResult.matches.length} 条岗位推荐。`);
    } catch (error) {
      setRequestState("error");
      setMessage(error instanceof Error ? error.message : "生成岗位推荐失败。");
    }
  };

  const currentStudentProfileId = result?.student_profile_id ?? (isPositiveInteger(studentProfileId) ? Number(studentProfileId) : undefined);

  return (
    <main className="app-shell">
      <section className="hero-card glass-card">
        <div>
          <p className="eyebrow">Recommendations</p>
          <h1>岗位推荐工作台</h1>
          <p className="hero-copy">这里直接调用后端匹配引擎，输出 Top-K 岗位、匹配得分、风险提示和关键证据。</p>
        </div>
        <aside className={`status-panel status-panel--${requestState}`}>
          <span>当前状态</span>
          <strong>{message}</strong>
        </aside>
      </section>

      <section className="two-column-grid">
        <article className="form-card glass-card">
          <div className="panel-title">
            <p className="eyebrow">Input</p>
            <h2>推荐参数</h2>
          </div>

          <div className="form-grid">
            <label className="field-group">
              <span className="field-label">student_profile_id</span>
              <input className="text-input" onChange={(event) => setStudentProfileId(event.target.value)} type="number" value={studentProfileId} />
            </label>
            <label className="field-group">
              <span className="field-label">top_k</span>
              <input className="text-input" max="10" min="1" onChange={(event) => setTopK(event.target.value)} type="number" value={topK} />
            </label>
          </div>

          <div className="button-row">
            <button className="primary-button" onClick={() => void handleRecommend()} type="button">
              生成推荐结果
            </button>
            <button className="ghost-button" onClick={onBackHome} type="button">
              返回工作台
            </button>
          </div>
        </article>

        <article className="form-card glass-card action-card">
          <div className="panel-title">
            <p className="eyebrow">Next Step</p>
            <h2>推荐完成后</h2>
            <p className="muted-text">推荐页生成成功后，可以继续进入职业报告或定制简历流程。</p>
          </div>
          <div className="button-row button-row--stacked">
            <button className="primary-button" onClick={() => onOpenReportWorkspace(currentStudentProfileId)} type="button">
              去生成职业报告
            </button>
            <button className="secondary-button" onClick={() => onOpenResumeWorkspace(currentStudentProfileId)} type="button">
              去生成定制简历
            </button>
          </div>
        </article>
      </section>

      <section className="result-grid">
        <article className="info-card glass-card result-grid-span">
          <div className="panel-title">
            <p className="eyebrow">Matches</p>
            <h2>推荐结果</h2>
          </div>

          {result?.matches.length ? (
            <div className="list-stack">
              {result.matches.map((match, index) => (
                <article className="list-card" key={`${match.job_profile_id}-${index}`}>
                  <div className="section-title-row">
                    <div>
                      <p className="eyebrow">Top {index + 1}</p>
                      <h4>{match.job_title}</h4>
                    </div>
                    <div className="badge-row">
                      <span className="pill">{match.total_score.toFixed(1)} 分</span>
                      {match.match_id ? <span className="tag">match_id={match.match_id}</span> : null}
                    </div>
                  </div>
                  <p className="muted-text">{match.reason}</p>
                  <div className="meta-grid meta-grid--compact">
                    <article className="meta-card">
                      <span>基础要求</span>
                      <strong>{match.dimension_scores.base_requirement.toFixed(1)}</strong>
                    </article>
                    <article className="meta-card">
                      <span>技能</span>
                      <strong>{match.dimension_scores.skill.toFixed(1)}</strong>
                    </article>
                    <article className="meta-card">
                      <span>软技能</span>
                      <strong>{match.dimension_scores.soft_skill.toFixed(1)}</strong>
                    </article>
                    <article className="meta-card">
                      <span>成长性</span>
                      <strong>{match.dimension_scores.growth.toFixed(1)}</strong>
                    </article>
                  </div>
                  <div className="result-grid result-grid--inner">
                    <article className="list-card">
                      <p className="eyebrow">Job Requirement Snapshot</p>
                      <ul className="bullet-list">
                        <li>核心技能：{match.job_requirement_snapshot.must_have_skills.slice(0, 5).join("、") || "未明确"}</li>
                        <li>证书要求：{match.job_requirement_snapshot.certificates.join("、") || "未明确"}</li>
                        <li>创新能力要求：{match.job_requirement_snapshot.innovation_requirement.toFixed(1)}</li>
                        <li>学习能力要求：{match.job_requirement_snapshot.learning_requirement.toFixed(1)}</li>
                        <li>抗压能力要求：{match.job_requirement_snapshot.stress_tolerance_requirement.toFixed(1)}</li>
                        <li>沟通能力要求：{match.job_requirement_snapshot.communication_requirement.toFixed(1)}</li>
                        <li>实习能力要求：{match.job_requirement_snapshot.internship_requirement.toFixed(1)}</li>
                      </ul>
                    </article>
                    <article className="list-card">
                      <p className="eyebrow">Student Capability Snapshot</p>
                      <ul className="bullet-list">
                        <li>学生技能：{match.student_capability_snapshot.professional_skills.slice(0, 5).join("、") || "未明确"}</li>
                        <li>学生证书：{match.student_capability_snapshot.certificates.join("、") || "未明确"}</li>
                        <li>创新能力：{match.student_capability_snapshot.innovation_score.toFixed(1)}</li>
                        <li>学习能力：{match.student_capability_snapshot.learning_score.toFixed(1)}</li>
                        <li>抗压能力：{match.student_capability_snapshot.stress_tolerance_score.toFixed(1)}</li>
                        <li>沟通能力：{match.student_capability_snapshot.communication_score.toFixed(1)}</li>
                        <li>实习能力：{match.student_capability_snapshot.internship_score.toFixed(1)}</li>
                      </ul>
                    </article>
                  </div>
                  <div className="result-grid result-grid--inner">
                    <article className="list-card">
                      <p className="eyebrow">Gap Analysis</p>
                      {match.gap_analysis.length ? (
                        <ul className="bullet-list">
                          {match.gap_analysis.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="panel-empty">暂无明显能力差距。</p>
                      )}
                    </article>
                    <article className="list-card">
                      <p className="eyebrow">Evidence & Risk</p>
                      <div className="badge-row">
                        {match.risk_flags.map((risk) => (
                          <span className="tag" key={risk}>
                            {risk}
                          </span>
                        ))}
                      </div>
                      <ul className="bullet-list">
                        {match.evidence.slice(0, 4).map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </article>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-card">
              <h3>还没有推荐结果</h3>
              <p className="panel-empty">输入 student_profile_id 后点击生成，即可看到推荐岗位和匹配分析。</p>
            </div>
          )}
        </article>
      </section>
    </main>
  );
}

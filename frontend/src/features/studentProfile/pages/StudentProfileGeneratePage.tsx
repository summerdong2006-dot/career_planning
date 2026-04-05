import { useMemo, useState } from "react";

import { toSafeDisplayList, toSafeDisplayText } from "../../../shared/encoding";
import { buildStudentProfile } from "../api";
import type { StudentInternship, StudentProfileBuildResult, StudentProject } from "../types";

type RequestState = "idle" | "loading" | "success" | "error";

type StudentProfileGeneratePageProps = {
  onOpenJobRecommendations: (studentProfileId?: number) => void;
  onOpenReportWorkspace: (studentProfileId?: number) => void;
  onOpenResumeWorkspace: (studentProfileId?: number) => void;
};

const initialMessage = "粘贴一段简历文本后，系统会生成可继续用于推荐、报告和简历的学生画像。";

function createStudentId(): string {
  const suffix = Math.random().toString(36).slice(2, 8).toUpperCase();
  return `demo-${suffix}`;
}

function getProfileId(result: StudentProfileBuildResult | null): number | undefined {
  return result?.record_refs.profile_id ?? undefined;
}

function getExperienceTitle(item: StudentProject | StudentInternship, fallback: string): string {
  if ("name" in item) {
    return toSafeDisplayText(item.name, fallback);
  }

  return toSafeDisplayText(item.company, fallback);
}

function getExperienceRole(item: StudentProject | StudentInternship): string {
  return toSafeDisplayText(item.role, "待补充");
}

function getExperienceDescription(item: StudentProject | StudentInternship): string {
  return toSafeDisplayText(item.description, "暂无详细说明");
}

function countReadableEntries(items: string[]): number {
  return items.filter((item) => item !== "待补充").length;
}

export function StudentProfileGeneratePage({
  onOpenJobRecommendations,
  onOpenReportWorkspace,
  onOpenResumeWorkspace
}: StudentProfileGeneratePageProps) {
  const [resumeText, setResumeText] = useState("");
  const [result, setResult] = useState<StudentProfileBuildResult | null>(null);
  const [requestState, setRequestState] = useState<RequestState>("idle");
  const [message, setMessage] = useState(initialMessage);

  const handleGenerate = async () => {
    const normalizedResumeText = resumeText.trim();

    if (!normalizedResumeText) {
      setRequestState("error");
      setMessage("请先粘贴简历文本，再生成学生画像。");
      return;
    }

    setRequestState("loading");
    setMessage("正在生成学生画像，请稍候。");

    try {
      const nextResult = await buildStudentProfile({
        studentId: createStudentId(),
        resumeText: normalizedResumeText,
        persist: true
      });

      setResult(nextResult);
      setRequestState("success");
      setMessage(
        nextResult.record_refs.profile_id
          ? `画像生成完成，student_profile_id=${nextResult.record_refs.profile_id}，可以继续进入推荐、报告和简历流程。`
          : "画像生成完成，可以先查看结构化结果。"
      );
    } catch (error) {
      setRequestState("error");
      setMessage(error instanceof Error ? error.message : "生成学生画像失败。");
    }
  };

  const profile = result?.profile;
  const studentProfileId = getProfileId(result);

  const safeProfile = useMemo(() => {
    if (!profile) {
      return null;
    }

    const skills = toSafeDisplayList(profile.skills, "待补充");
    const summary = toSafeDisplayText(profile.summary, "系统已生成画像，但摘要内容暂不可用，建议继续查看评分和后续流程。");

    return {
      name: toSafeDisplayText(profile.student_name, "待补充"),
      intention: toSafeDisplayText(profile.career_intention, "待补充"),
      summary,
      skills,
      readableSkillCount: countReadableEntries(skills)
    };
  }, [profile]);

  return (
    <main className="app-shell">
      <section className="hero-card glass-card">
        <div>
          <p className="eyebrow">Student Profile</p>
          <h1>学生画像工作台</h1>
          <p className="hero-copy">流程参考：输入简历文本，生成结构化画像，再把 `student_profile_id` 继续传给推荐、报告和简历模块。</p>
        </div>
        <aside className={`status-panel status-panel--${requestState}`}>
          <span>当前状态</span>
          <strong>{message}</strong>
        </aside>
      </section>

      <section className="two-column-grid">
        <article className="form-card glass-card">
          <div className="panel-title">
            <p className="eyebrow">Step 1</p>
            <h2>粘贴简历文本</h2>
            <p className="muted-text">请写入您的简历内容。</p>
          </div>

          <div className="form-grid form-grid--single">
            <label className="field-group field-group--full">
              <span className="field-label">简历内容</span>
              <textarea
                className="text-area text-area--tall"
                onChange={(event) => setResumeText(event.target.value)}
                placeholder="示例：张三，上海交通大学计算机科学与技术专业，本科。掌握 Python、SQL、React。项目经历包括校园二手平台、数据分析看板。曾在某互联网公司产品运营实习。求职意向：数据分析师。"
                value={resumeText}
              />
            </label>
          </div>

          <div className="button-row">
            <button className="primary-button" onClick={handleGenerate} type="button">
              生成学生画像
            </button>
          </div>
        </article>

        <article className="info-card glass-card">
          <div className="panel-title">
            <p className="eyebrow">Step 2</p>
            <h2>本次生成结果</h2>
            <p className="muted-text">这里优先展示对 Demo 最重要的字段。</p>
          </div>

          {safeProfile ? (
            <div className="list-stack">
              <article className="list-card">
                <p className="eyebrow">画像编号</p>
                <h4>{studentProfileId ? `student_profile_id=${studentProfileId}` : "已生成但未持久化"}</h4>
                <p className="muted-text">student_id={result?.student_id ?? "未生成"}</p>
              </article>
              <article className="list-card">
                <p className="eyebrow">候选人概览</p>
                <h4>{safeProfile.name}</h4>
                <p className="muted-text">意向方向：{safeProfile.intention}</p>
                <p className="muted-text">{safeProfile.summary}</p>
              </article>
              <article className="list-card">
                <p className="eyebrow">结果概况</p>
                <p className="muted-text">技能数：{safeProfile.readableSkillCount}</p>
                <p className="muted-text">项目数：{profile?.projects.length ?? 0}</p>
                <p className="muted-text">实习数：{profile?.internships.length ?? 0}</p>
              </article>
            </div>
          ) : (
            <div className="empty-card">
              <h3>等待生成结果</h3>
              <p className="panel-empty">生成成功后，这里会显示可直接用于后续流程的画像信息和画像编号。</p>
            </div>
          )}
        </article>
      </section>

      <section className="result-grid">
        <article className="info-card glass-card">
          <div className="panel-title">
            <p className="eyebrow">Structured View</p>
            <h2>结构化画像</h2>
          </div>

          {safeProfile && profile ? (
            <div className="result-stack">
              <div className="meta-grid meta-grid--compact">
                <article className="meta-card">
                  <span>姓名</span>
                  <strong>{safeProfile.name}</strong>
                </article>
                <article className="meta-card">
                  <span>意向方向</span>
                  <strong>{safeProfile.intention}</strong>
                </article>
                <article className="meta-card">
                  <span>完整度评分</span>
                  <strong>{profile.completeness_score.toFixed(1)}</strong>
                </article>
                <article className="meta-card">
                  <span>竞争力评分</span>
                  <strong>{profile.competitiveness_score.toFixed(1)}</strong>
                </article>
              </div>

              <div className="result-section-block">
                <div className="section-title-row">
                  <h3>技能标签</h3>
                </div>
                <div className="badge-row">
                  {safeProfile.skills.map((skill) => (
                    <span className="tag" key={skill}>
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-card">
              <h3>尚未生成学生画像</h3>
              <p className="panel-empty">生成成功后，这里会展示学生画像的基础信息、评分和技能标签。</p>
            </div>
          )}
        </article>

        <article className="info-card glass-card">
          <div className="panel-title">
            <p className="eyebrow">Experience</p>
            <h2>项目与实习</h2>
          </div>

          {profile && (profile.projects.length > 0 || profile.internships.length > 0) ? (
            <div className="list-stack">
              {profile.projects.slice(0, 3).map((project, index) => (
                <article className="list-card" key={`${project.name}-${index}`}>
                  <h4>{getExperienceTitle(project, `项目经历 ${index + 1}`)}</h4>
                  <p className="muted-text">角色：{getExperienceRole(project)}</p>
                  <p className="muted-text">{getExperienceDescription(project)}</p>
                </article>
              ))}
              {profile.internships.slice(0, 2).map((internship, index) => (
                <article className="list-card" key={`${internship.company}-${index}`}>
                  <h4>{getExperienceTitle(internship, `实习经历 ${index + 1}`)}</h4>
                  <p className="muted-text">岗位：{getExperienceRole(internship)}</p>
                  <p className="muted-text">{getExperienceDescription(internship)}</p>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-card">
              <h3>暂无可展示经历</h3>
              <p className="panel-empty">如果接口暂时没有稳定提取出项目或实习，这里会保持简洁空态。</p>
            </div>
          )}
        </article>
      </section>

      <section className="result-grid result-grid--bottom">
        <article className="form-card glass-card action-card">
          <div className="panel-title">
            <p className="eyebrow">Step 3</p>
            <h2>继续下一步</h2>
            <p className="muted-text">生成学生画像后，可以直接带着本次 `student_profile_id` 进入后续模块。</p>
          </div>

          <div className="button-row button-row--stacked">
            <button className="secondary-button" onClick={() => onOpenJobRecommendations(studentProfileId)} type="button">
              去岗位推荐
            </button>
            <button className="primary-button" onClick={() => onOpenReportWorkspace(studentProfileId)} type="button">
              去生成职业报告
            </button>
            <button className="secondary-button" onClick={() => onOpenResumeWorkspace(studentProfileId)} type="button">
              去生成定制简历
            </button>
          </div>
        </article>

        <article className="info-card glass-card">
          <div className="panel-title">
            <p className="eyebrow">Tips</p>
            <h2>演示建议</h2>
          </div>
          <div className="list-stack">
            <article className="list-card">
              <h4>先求流程通</h4>
              <p className="muted-text">当前 Demo 的重点是让画像、推荐、报告和简历四步能顺畅串起来。</p>
            </article>
            <article className="list-card">
              <h4>优先看 ID</h4>
              <p className="muted-text">只要拿到了 `student_profile_id`，后面几个模块就都能继续联调和演示。</p>
            </article>
          </div>
        </article>
      </section>
    </main>
  );
}

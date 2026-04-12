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

const initialMessage = "粘贴一段简历文本后，系统会整理出你的能力画像、经历亮点和职业方向参考。";

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
          ? "画像生成完成，可以继续查看岗位推荐、职业报告或定制简历。"
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
    const summary = toSafeDisplayText(profile.summary, "系统已生成画像，但摘要内容暂不可用，建议继续查看评分和技能标签。");

    return {
      name: toSafeDisplayText(profile.student_name, "待补充"),
      intention: toSafeDisplayText(profile.career_intention, "待补充"),
      summary,
      skills,
      readableSkillCount: countReadableEntries(skills)
    };
  }, [profile]);

  return (
    <main className="app-shell student-profile-workbench">
      <section className="hero-card glass-card student-profile-hero">
        <div className="student-profile-hero__copy">
          <p className="eyebrow">Student Profile</p>
          <h1>学生画像工作台</h1>
          <p className="hero-copy">在这里整理简历信息，生成个人能力画像，快速了解优势、经历亮点与适合探索的职业方向。</p>
        </div>
        <div className="student-profile-hero__side">
          <aside className={`status-panel status-panel--${requestState}`}>
            <span>当前状态</span>
            <strong>{message}</strong>
          </aside>
          <div className="student-profile-orbit" aria-hidden="true">
            <span className="student-profile-orbit__core" />
            <span className="student-profile-orbit__ring student-profile-orbit__ring--one" />
            <span className="student-profile-orbit__ring student-profile-orbit__ring--two" />
            <i>Skill</i>
            <i>Project</i>
            <i>Intent</i>
          </div>
        </div>
      </section>

      <section className="student-profile-lab-grid">
        <article className="form-card glass-card student-profile-input-card">
          <div className="panel-title">
            <p className="eyebrow">Step 1</p>
            <h2>粘贴简历文本</h2>
            <p className="muted-text">把教育背景、项目经历、技能和求职意向放进来，小涯会把它整理成可分析的学生画像。</p>
          </div>

          <div className="form-grid form-grid--single">
            <label className="field-group field-group--full">
              <span className="field-label">简历内容</span>
              <textarea
                className="text-area text-area--tall student-profile-resume-paper"
                onChange={(event) => setResumeText(event.target.value)}
                placeholder="示例：张三，上海交通大学计算机科学与技术专业，本科。掌握 Python、SQL、React。项目经历包括校园二手平台、数据分析看板。曾在某互联网公司产品运营实习。求职意向：数据分析师。"
                value={resumeText}
              />
            </label>
          </div>

          <div className="student-profile-capture-hints">
            <span>教育背景</span>
            <span>项目经历</span>
            <span>技能清单</span>
            <span>实习经历</span>
            <span>求职意向</span>
          </div>

          <div className="button-row student-profile-generate-row">
            <button className="primary-button" onClick={handleGenerate} type="button">
              生成学生画像
            </button>
          </div>
        </article>

        <article className="info-card glass-card student-profile-result-card">
          <div className="panel-title">
            <p className="eyebrow">Step 2</p>
            <h2>本次生成结果</h2>
            <p className="muted-text">这里会概览本次画像的核心信息，方便继续查看推荐、报告或简历。</p>
          </div>

          {safeProfile ? (
            <div className="list-stack student-profile-snapshot">
              <article className="list-card student-profile-mini-card student-profile-mini-card--gold">
                <p className="eyebrow">画像档案</p>
                <h4>{studentProfileId ? `档案 #${studentProfileId}` : "已生成临时画像"}</h4>
                <p className="muted-text">本次画像已可用于后续分析。</p>
              </article>
              <article className="list-card student-profile-mini-card student-profile-mini-card--mint">
                <p className="eyebrow">候选人概览</p>
                <h4>{safeProfile.name}</h4>
                <p className="muted-text">意向方向：{safeProfile.intention}</p>
                <p className="muted-text">{safeProfile.summary}</p>
              </article>
              <article className="list-card student-profile-mini-card student-profile-mini-card--blue">
                <p className="eyebrow">结果概况</p>
                <p className="muted-text">技能数：{safeProfile.readableSkillCount}</p>
                <p className="muted-text">项目数：{profile?.projects.length ?? 0}</p>
                <p className="muted-text">实习数：{profile?.internships.length ?? 0}</p>
              </article>
            </div>
          ) : (
            <div className="empty-card">
              <h3>等待生成结果</h3>
              <p className="panel-empty">生成成功后，这里会显示个人画像概览、意向方向和能力摘要。</p>
            </div>
          )}
        </article>
      </section>

      <section className="result-grid student-profile-output-grid">
        <article className="info-card glass-card student-profile-structured-card">
          <div className="panel-title">
            <p className="eyebrow">Structured View</p>
            <h2>结构化画像</h2>
          </div>

          {safeProfile && profile ? (
            <div className="result-stack">
              <div className="meta-grid meta-grid--compact">
                <article className="meta-card student-profile-score-card">
                  <span>姓名</span>
                  <strong>{safeProfile.name}</strong>
                </article>
                <article className="meta-card student-profile-score-card">
                  <span>意向方向</span>
                  <strong>{safeProfile.intention}</strong>
                </article>
                <article className="meta-card student-profile-score-card">
                  <span>完整度评分</span>
                  <strong>{profile.completeness_score.toFixed(1)}</strong>
                </article>
                <article className="meta-card student-profile-score-card">
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

        <article className="info-card glass-card student-profile-experience-card">
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
              <p className="panel-empty">如果简历里暂时没有项目或实习信息，这里会保持简洁空态。</p>
            </div>
          )}
        </article>
      </section>

      <section className="result-grid result-grid--bottom student-profile-next-grid">
        <article className="form-card glass-card action-card student-profile-next-card">
          <div className="panel-title">
            <p className="eyebrow">Step 3</p>
            <h2>继续下一步</h2>
            <p className="muted-text">画像生成后，可以继续查看岗位推荐、生成职业报告，或制作更贴合目标岗位的简历。</p>
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

        <article className="info-card glass-card student-profile-tips-card">
          <div className="panel-title">
            <p className="eyebrow">Tips</p>
            <h2>使用建议</h2>
          </div>
          <div className="list-stack">
            <article className="list-card">
              <h4>简历越完整，画像越准确</h4>
              <p className="muted-text">建议补充教育背景、技能、项目经历和实习经历，让系统更好识别你的优势。</p>
            </article>
            <article className="list-card">
              <h4>先看画像，再做选择</h4>
              <p className="muted-text">可以先确认画像是否符合真实情况，再继续查看岗位推荐、职业报告和定制简历。</p>
            </article>
          </div>
        </article>
      </section>
    </main>
  );
}

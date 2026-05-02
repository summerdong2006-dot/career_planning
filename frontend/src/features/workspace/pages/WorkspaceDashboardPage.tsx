import { useEffect, useMemo, useState } from "react";

import { toSafeDisplayText } from "../../../shared/encoding";
import { getWorkspaceOverview } from "../api";
import type { StudentWorkspaceSummary, WorkspaceOverview } from "../types";

type RequestState = "idle" | "loading" | "success" | "error";

type WorkspaceDashboardPageProps = {
  onCreateProfile: () => void;
  onOpenReport: (reportId: number) => void;
  onOpenRecommendations: (studentProfileId?: number) => void;
  onOpenResume: (studentProfileId?: number) => void;
};

type RadarMetric = {
  color: string;
  label: string;
  target: number;
  value: number;
  score: number;
};

const RADAR_CENTER = 110;
const RADAR_RADIUS = 78;
const RADAR_SCORE_TARGET = 0.8;
const RADAR_METRIC_DEFINITIONS = [
  { key: "professional_skills", label: "专业技能", color: "#4f8790" },
  { key: "internship_ability", label: "实践能力", color: "#d8c38a" },
  { key: "learning", label: "学习能力", color: "#8ab3a1" },
  { key: "innovation", label: "创新能力", color: "#eed99d" },
  { key: "communication", label: "沟通协作", color: "#c7dde0" }
] as const;

function getRadarPoint(index: number, total: number, value: number, radius = RADAR_RADIUS): string {
  const angle = -Math.PI / 2 + (Math.PI * 2 * index) / total;
  const distance = radius * value;
  const x = RADAR_CENTER + Math.cos(angle) * distance;
  const y = RADAR_CENTER + Math.sin(angle) * distance;

  return `${x.toFixed(1)},${y.toFixed(1)}`;
}

function getRadarPolygon(values: number[]): string {
  return values.map((value, index) => getRadarPoint(index, values.length, value)).join(" ");
}

function buildRadarMetrics(profile?: StudentWorkspaceSummary): RadarMetric[] {
  const abilityScores = profile?.ability_scores ?? {};

  return RADAR_METRIC_DEFINITIONS.map((metric) => {
    const score = Math.max(0, Math.min(100, Number(abilityScores[metric.key]) || 0));
    return {
      ...metric,
      score,
      target: RADAR_SCORE_TARGET,
      value: score / 100
    };
  });
}

function getPilotStatus(state: RequestState, hasProfile: boolean, hasReport: boolean, hasResume: boolean): string {
  if (state === "loading") {
    return "Syncing";
  }
  if (state === "error") {
    return "Needs Attention";
  }
  if (hasProfile && hasReport && hasResume) {
    return "Ready to Launch";
  }
  if (hasProfile) {
    return "In Progress";
  }
  return "Start Here";
}

export function WorkspaceDashboardPage({
  onCreateProfile,
  onOpenRecommendations
}: WorkspaceDashboardPageProps) {
  const [workspace, setWorkspace] = useState<WorkspaceOverview | null>(null);
  const [requestState, setRequestState] = useState<RequestState>("loading");
  const [message, setMessage] = useState("正在加载你的工作台。");
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(null);

  useEffect(() => {
    const loadWorkspace = async () => {
      setRequestState("loading");
      setMessage("正在同步学生画像、职业报告和定制简历。");

      try {
        const result = await getWorkspaceOverview();
        setWorkspace(result);
        setSelectedProfileId((currentProfileId) => currentProfileId ?? result.student_profiles[0]?.profile_id ?? null);
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
  const selectedProfile =
    workspace?.student_profiles.find((profile) => profile.profile_id === selectedProfileId) ?? latestProfile;
  const hasProfile = Boolean(latestProfile);
  const hasReport = Boolean(workspace?.reports[0]);
  const hasResume = Boolean(workspace?.resumes[0]);
  const pilotStatus = getPilotStatus(requestState, hasProfile, hasReport, hasResume);
  const radarVariant = selectedProfile ? selectedProfile.profile_id % 3 : 0;
  const radarMetrics = useMemo(() => buildRadarMetrics(selectedProfile), [selectedProfile]);
  const radarActualPoints = getRadarPolygon(radarMetrics.map((metric) => metric.value));
  const radarTargetPoints = getRadarPolygon(radarMetrics.map((metric) => metric.target));
  const radarRings = [0.25, 0.5, 0.75, 1].map((scale) =>
    getRadarPolygon(radarMetrics.map(() => scale))
  );

  const pathItems = useMemo(
    () => [
      {
        active: hasProfile,
        label: "画像建立",
        text: hasProfile ? "能力轮廓已形成" : "从简历文本开始"
      },
      {
        active: hasProfile,
        label: "岗位探索",
        text: hasProfile ? "可查看推荐岗位" : "画像完成后开启"
      },
      {
        active: hasReport,
        label: "报告沉淀",
        text: hasReport ? "职业建议已生成" : "生成发展报告"
      },
      {
        active: hasResume,
        label: "简历投递",
        text: hasResume ? "定制简历已准备" : "制作岗位简历"
      }
    ],
    [hasProfile, hasReport, hasResume]
  );

  return (
    <main className="app-shell dashboard-studio">
      <div className="dashboard-flow-lines" aria-hidden="true">
        <svg viewBox="0 0 1500 980" preserveAspectRatio="none">
          <defs>
            <marker id="dashboard-flow-arrow-gold" markerHeight="12" markerWidth="12" orient="auto" refX="9" refY="5">
              <path d="M1 1L10 5L1 9" />
            </marker>
            <marker id="dashboard-flow-arrow-teal" markerHeight="12" markerWidth="12" orient="auto" refX="9" refY="5">
              <path d="M1 1L10 5L1 9" />
            </marker>
          </defs>
          <path
            className="dashboard-flow-line dashboard-flow-line--gold"
            d="M-40 214 C 170 24, 496 34, 710 198 S 1056 354, 1240 168 S 1446 22, 1570 104"
            markerEnd="url(#dashboard-flow-arrow-gold)"
          />
          <path
            className="dashboard-flow-line dashboard-flow-line--teal"
            d="M132 714 C 336 468, 532 488, 760 646 S 1124 804, 1488 468"
            markerEnd="url(#dashboard-flow-arrow-teal)"
          />
          <path
            className="dashboard-flow-line dashboard-flow-line--blue"
            d="M-72 508 C 198 340, 430 374, 654 516 S 1046 630, 1570 306"
          />
          <circle className="dashboard-flow-dot dashboard-flow-dot--gold" cx="710" cy="198" r="6" />
          <circle className="dashboard-flow-dot dashboard-flow-dot--teal" cx="760" cy="646" r="6" />
          <circle className="dashboard-flow-dot dashboard-flow-dot--blue" cx="654" cy="516" r="4" />
        </svg>
      </div>
      <section className="dashboard-studio-grid" aria-label="职业规划工作台">
        <article className="studio-card studio-card--pilot">
          <div className="studio-card__topline">
            <span>Career Pilot</span>
            <strong>{pilotStatus}</strong>
          </div>
          <h1>职业规划工作台</h1>
          <p>
            让你的职业计划保持清晰、可信、可行动。
          </p>
          <div className="studio-actions">
            <button className="studio-button studio-button--primary" onClick={onCreateProfile} type="button">
              新建学生画像
            </button>
            <button className="studio-button" onClick={() => onOpenRecommendations(selectedProfile?.profile_id ?? latestProfile?.profile_id)} type="button">
              查看岗位推荐
            </button>
          </div>
        </article>

        <aside className="studio-card studio-card--status">
          <span className="studio-eyebrow">Workspace Signal</span>
          <strong>{message}</strong>
          <div className="studio-stat-row">
            <span>{workspace?.student_profiles.length ?? 0}<small>画像</small></span>
            <span>{workspace?.reports.length ?? 0}<small>报告</small></span>
            <span>{workspace?.resumes.length ?? 0}<small>简历</small></span>
          </div>
        </aside>

        <article className={`studio-card studio-card--radar studio-card--radar-variant-${radarVariant}`}>
          <div className="studio-radar-pilot">
            <small>{selectedProfile ? `Profile #${selectedProfile.profile_id}` : "Select a profile"}</small>
            <strong>能力雷达图</strong>
            <p>
              {selectedProfile
                ? `竞争力 ${selectedProfile.competitiveness_score.toFixed(1)} 分 · 完整度 ${selectedProfile.completeness_score.toFixed(1)} 分`
                : "选择右侧学生画像后，这里会切换对应的能力雷达。"}
            </p>
          </div>

          <div className="studio-radar-panel">
            <h3>PROFILE SCORES FROM STUDENT MODEL</h3>
            <div className="studio-radar-board">
              <svg className="studio-radar-svg" viewBox="0 0 220 220" role="img" aria-label="能力雷达图">
                {radarRings.map((points, index) => (
                  <polygon className="studio-radar-svg__ring" key={points} points={points} opacity={0.34 + index * 0.12} />
                ))}
                {radarMetrics.map((metric, index) => (
                  <line
                    className="studio-radar-svg__axis"
                    key={metric.label}
                    x1={RADAR_CENTER}
                    x2={getRadarPoint(index, radarMetrics.length, 1).split(",")[0]}
                    y1={RADAR_CENTER}
                    y2={getRadarPoint(index, radarMetrics.length, 1).split(",")[1]}
                  />
                ))}
                <polygon className="studio-radar-svg__target" points={radarTargetPoints} />
                <polygon className="studio-radar-svg__actual" points={radarActualPoints} />
                {radarMetrics.map((metric, index) => {
                  const [x, y] = getRadarPoint(index, radarMetrics.length, 1.12, 82).split(",");
                  return (
                    <text className="studio-radar-svg__label" key={`${metric.label}-label`} x={x} y={y}>
                      {metric.label}
                    </text>
                  );
                })}
              </svg>

              <div className="studio-radar-legend">
                {radarMetrics.map((metric) => (
                  <span key={metric.label}>
                    <i style={{ background: metric.color }} />
                    {metric.label} {metric.score.toFixed(1)}
                  </span>
                ))}
              </div>
            </div>
            <div className="studio-radar-note">
              <span>✦</span>
              <p>雷达图使用后端学生画像评分：专业技能、实践能力、学习能力、创新能力和沟通协作。</p>
            </div>
          </div>
        </article>

        <article className="studio-card studio-card--profiles">
          <div className="studio-section-head">
            <div>
              <span className="studio-eyebrow">Student Profile</span>
              <h2>学生画像</h2>
            </div>
            <button className="studio-link" onClick={onCreateProfile} type="button">
              新建
            </button>
          </div>
          {workspace?.student_profiles.length ? (
            <div className="studio-list">
              {workspace.student_profiles.slice(0, 3).map((profile) => (
                <button
                  className={profile.profile_id === selectedProfile?.profile_id ? "studio-list-item studio-list-item--active" : "studio-list-item"}
                  key={profile.profile_id}
                  onClick={() => setSelectedProfileId(profile.profile_id)}
                  type="button"
                >
                  <strong>画像档案 #{profile.profile_id}</strong>
                  <span>{toSafeDisplayText(profile.career_intention, "暂未填写意向方向")}</span>
                  <small>{toSafeDisplayText(profile.summary, "暂无画像摘要")}</small>
                </button>
              ))}
            </div>
          ) : (
            <div className="studio-empty">
              <strong>还没有学生画像</strong>
              <span>先从一段简历文本开始，生成第一份能力档案。</span>
            </div>
          )}
        </article>

        <article className="studio-card studio-card--path">
          <div>
            <span className="studio-eyebrow">Career Path</span>
            <h2>职业路径进度</h2>
          </div>
          <div className="studio-path">
            {pathItems.map((item) => (
              <div className={item.active ? "studio-path-node studio-path-node--active" : "studio-path-node"} key={item.label}>
                <span />
                <strong>{item.label}</strong>
                <small>{item.text}</small>
              </div>
            ))}
          </div>
        </article>
      </section>
    </main>
  );
}
//AI辅助生成：Qwen3-Max-Thinking, 2026-04-26
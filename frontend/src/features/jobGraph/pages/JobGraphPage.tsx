import { type FormEvent, useEffect, useMemo, useState } from "react";

import { getWorkspaceOverview } from "../../workspace/api";
import type { StudentWorkspaceSummary } from "../../workspace/types";
import { getJobGallery, getJobPathByJobId, getJobPathByJobTitle, getJobPathByStudentProfileId } from "../api";
import type { JobPathExplorerResponse, RepresentativeJobCard } from "../types";

type JobGraphPageProps = {
  onNavigateHome: () => void;
};

type RequestState = "loading" | "success" | "error";

const IMAGE_NAMES = ["1.jpg", "2.jpg", "3.jpg"];
const IMAGE_POOL = IMAGE_NAMES.map((name) => `/job_gallery/${encodeURIComponent(name)}`);
const QUICK_SEARCHES = ["后端开发", "前端开发", "数据分析", "人工智能", "测试工程师", "产品运营"];

function getJobImage(index: number): string | null {
  if (IMAGE_POOL.length === 0) {
    return null;
  }
  return IMAGE_POOL[index % IMAGE_POOL.length];
}

function getWalkerPosition(total: number, activeIndex: number): string {
  if (total <= 0) {
    return "50%";
  }
  return `${((activeIndex + 0.5) / total) * 100}%`;
}

function isDisplayValue(value: string | null | undefined): value is string {
  const normalized = value?.trim();
  return Boolean(normalized && normalized !== "未明确" && normalized !== "未知" && normalized !== "无");
}

function displayList(values: string[]): string[] {
  return values.filter(isDisplayValue);
}

function compactLocation(job: RepresentativeJobCard): string | null {
  const parts = [job.work_city, job.work_address].filter(isDisplayValue);
  return parts.length > 0 ? parts.join(" · ") : null;
}

function displaySummary(summary: string): string {
  return isDisplayValue(summary) ? summary : "这个岗位适合继续展开探索。";
}

function isComputerRelatedJob(job: RepresentativeJobCard): boolean {
  const searchableText = [
    job.job_title,
    job.industry,
    job.summary,
    ...job.must_have_skills,
    ...job.certificates,
  ]
    .join(" ")
    .toLowerCase();
  const keywords = [
    "计算机",
    "软件",
    "互联网",
    "开发",
    "前端",
    "后端",
    "全栈",
    "测试",
    "运维",
    "数据",
    "算法",
    "人工智能",
    "机器学习",
    "大模型",
    "云计算",
    "网络",
    "安全",
    "java",
    "python",
    "react",
    "vue",
    "sql",
  ];

  return keywords.some((keyword) => searchableText.includes(keyword));
}

function pickDefaultComputerJobs(jobs: RepresentativeJobCard[]): RepresentativeJobCard[] {
  const computerJobs = jobs.filter(isComputerRelatedJob);
  return (computerJobs.length >= 8 ? computerJobs : [...computerJobs, ...jobs.filter((job) => !computerJobs.includes(job))]).slice(0, 8);
}

function getJobFamilyClass(job: RepresentativeJobCard): string {
  const text = [job.job_title, job.industry, job.summary, ...job.must_have_skills].join(" ").toLowerCase();

  if (/(ai|算法|人工智能|机器学习|大模型|数据)/i.test(text)) {
    return "job-result-card--data";
  }
  if (/(前端|react|vue|javascript|typescript|html|css)/i.test(text)) {
    return "job-result-card--frontend";
  }
  if (/(测试|质量|qa)/i.test(text)) {
    return "job-result-card--testing";
  }
  if (/(产品|运营|市场|用户)/i.test(text)) {
    return "job-result-card--product";
  }

  return "job-result-card--backend";
}

export function JobGraphPage({ onNavigateHome }: JobGraphPageProps) {
  const [exhibitJobs, setExhibitJobs] = useState<RepresentativeJobCard[]>([]);
  const [exhibitIndex, setExhibitIndex] = useState(0);
  const [exhibitState, setExhibitState] = useState<RequestState>("loading");
  const [exhibitMessage, setExhibitMessage] = useState("正在加载代表岗位展板...");
  const [searchJobs, setSearchJobs] = useState<RepresentativeJobCard[]>([]);
  const [searchState, setSearchState] = useState<RequestState>("loading");
  const [searchMessage, setSearchMessage] = useState("正在准备岗位搜索结果...");
  const [gallerySearch, setGallerySearch] = useState("");
  const [analysisSearch, setAnalysisSearch] = useState("");
  const [analysisState, setAnalysisState] = useState<RequestState>("loading");
  const [analysisMessage, setAnalysisMessage] = useState("正在准备岗位发展路径...");
  const [pathDetail, setPathDetail] = useState<JobPathExplorerResponse | null>(null);
  const [studentProfiles, setStudentProfiles] = useState<StudentWorkspaceSummary[]>([]);
  const [selectedStudentProfileId, setSelectedStudentProfileId] = useState<number | "">("");
  const [selectedResultJobId, setSelectedResultJobId] = useState<number | null>(null);
  const [isAutoplayPaused, setIsAutoplayPaused] = useState(false);
  const [activeTimelineIndex, setActiveTimelineIndex] = useState(0);

  const exhibitJob = exhibitJobs[exhibitIndex] ?? null;
  const exhibitImage = getJobImage(exhibitIndex);
  const timelineSteps = pathDetail?.timeline_steps ?? [];
  const exhibitMeta = exhibitJob
    ? [exhibitJob.company_name, exhibitJob.salary_range, exhibitJob.work_city].filter(isDisplayValue)
    : [];
  const exhibitSkills = exhibitJob ? displayList(exhibitJob.must_have_skills).slice(0, 4) : [];

  const selectedStudentProfile = useMemo(
    () => studentProfiles.find((profile) => profile.profile_id === selectedStudentProfileId) ?? null,
    [selectedStudentProfileId, studentProfiles]
  );

  const loadInitialData = async () => {
    setExhibitState("loading");
    setSearchState("loading");
    try {
      const [exhibit, results, workspace] = await Promise.all([
        getJobGallery("", 8),
        getJobGallery("", 60),
        getWorkspaceOverview(),
      ]);
      const defaultSearchJobs = pickDefaultComputerJobs(results.jobs);
      setExhibitJobs(exhibit.jobs);
      setSearchJobs(defaultSearchJobs);
      setStudentProfiles(workspace.student_profiles);
      setExhibitIndex(0);
      setSelectedResultJobId(defaultSearchJobs[0]?.job_id ?? null);
      setExhibitState("success");
      setSearchState("success");
      setExhibitMessage(`已选出 ${exhibit.jobs.length} 个代表岗位展板。`);
      setSearchMessage(`已加载 ${defaultSearchJobs.length} 个计算机相关岗位结果。`);
      if (defaultSearchJobs[0]) {
        await loadPathByJob(defaultSearchJobs[0]);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "岗位展览加载失败。";
      setExhibitState("error");
      setSearchState("error");
      setExhibitMessage(message);
      setSearchMessage(message);
    }
  };

  const loadSearchResults = async (query: string) => {
    setSearchState("loading");
    setSearchMessage("正在搜索具体岗位...");
    try {
      const results = await getJobGallery(query, 18);
      setSearchJobs(results.jobs);
      setSelectedResultJobId(results.jobs[0]?.job_id ?? null);
      setSearchState("success");
      setSearchMessage(`已找到 ${results.jobs.length} 个岗位结果。`);
    } catch (error) {
      setSearchState("error");
      setSearchMessage(error instanceof Error ? error.message : "岗位搜索失败。");
    }
  };

  const loadPathByJob = async (job: RepresentativeJobCard) => {
    setAnalysisState("loading");
    setAnalysisMessage(`正在分析 ${job.job_title} 的发展路径...`);
    try {
      const detail = await getJobPathByJobId(job.job_id);
      setPathDetail(detail);
      setActiveTimelineIndex(0);
      setSelectedResultJobId(job.job_id);
      setAnalysisState("success");
      setAnalysisMessage(`已生成 ${detail.selected_job.job_title} 的图文发展路径。`);
    } catch (error) {
      setAnalysisState("error");
      setAnalysisMessage(error instanceof Error ? error.message : "发展路径分析失败。");
    }
  };

  useEffect(() => {
    void loadInitialData();
  }, []);

  useEffect(() => {
    if (!exhibitJobs.length || isAutoplayPaused) {
      return;
    }
    const timer = window.setInterval(() => {
      setExhibitIndex((current) => (current + 1) % exhibitJobs.length);
    }, 4200);
    return () => window.clearInterval(timer);
  }, [exhibitJobs.length, isAutoplayPaused]);

  const handleExhibitSelect = (index: number) => {
    setIsAutoplayPaused(true);
    setExhibitIndex(index);
    window.setTimeout(() => setIsAutoplayPaused(false), 6000);
  };

  const handleGallerySearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await loadSearchResults(gallerySearch);
  };

  const handleQuickSearch = async (query: string) => {
    setGallerySearch(query);
    await loadSearchResults(query);
  };

  const handleJobTitleAnalysis = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!analysisSearch.trim()) {
      return;
    }
    setAnalysisState("loading");
    setAnalysisMessage(`正在检索“${analysisSearch.trim()}”的发展路径...`);
    try {
      const detail = await getJobPathByJobTitle(analysisSearch.trim());
      setPathDetail(detail);
      setActiveTimelineIndex(0);
      setSelectedResultJobId(detail.selected_job.job_id);
      setAnalysisState("success");
      setAnalysisMessage(`已按岗位搜索生成 ${detail.selected_job.job_title} 的发展路径。`);
    } catch (error) {
      setAnalysisState("error");
      setAnalysisMessage(error instanceof Error ? error.message : "岗位路径搜索失败。");
    }
  };

  const handleStudentProfileAnalysis = async () => {
    if (!selectedStudentProfileId) {
      return;
    }
    setAnalysisState("loading");
    setAnalysisMessage("正在结合学生画像生成路径建议...");
    try {
      const detail = await getJobPathByStudentProfileId(selectedStudentProfileId);
      setPathDetail(detail);
      setActiveTimelineIndex(0);
      setSelectedResultJobId(detail.selected_job.job_id);
      setAnalysisState("success");
      setAnalysisMessage(`已基于学生画像联动到 ${detail.selected_job.job_title} 的发展路径。`);
    } catch (error) {
      setAnalysisState("error");
      setAnalysisMessage(error instanceof Error ? error.message : "学生画像路径分析失败。");
    }
  };

  return (
    <main className="app-shell job-gallery-page">
      <section className="hero-card glass-card job-gallery-hero">
        <div className="job-gallery-hero__copy">
          <p className="eyebrow">Career Exhibition</p>
          <h1>岗位展览馆</h1>
          <p className="hero-copy">
            在这里浏览热门岗位展览，搜索心仪岗位的城市、薪资与公司信息，并继续探索适合自己的成长路线。
          </p>
          <div className="job-gallery-hero__tags" aria-label="展馆能力标签">
            <span>岗位海报</span>
            <span>城市薪资</span>
            <span>成长路线</span>
          </div>
        </div>
        <aside className={`job-gallery-hero__panel status-panel status-panel--${exhibitState}`}>
          <span>Live Gallery</span>
          <strong>{exhibitMessage}</strong>
          <div className="job-gallery-orbit" aria-hidden="true">
            <span className="job-gallery-orbit__ring" />
            <span className="job-gallery-orbit__ring job-gallery-orbit__ring--tilt" />
            <i>JOB</i>
            <i>PATH</i>
            <i>SKILL</i>
          </div>
          <div className="job-gallery-hero__stats">
            <span>
              <strong>{exhibitJobs.length || "--"}</strong>
              展板
            </span>
            <span>
              <strong>{searchJobs.length || "--"}</strong>
              卡片
            </span>
          </div>
        </aside>
      </section>

      <section className="job-exhibit-board glass-card" onMouseEnter={() => setIsAutoplayPaused(true)} onMouseLeave={() => setIsAutoplayPaused(false)}>
        {exhibitJob ? (
          <>
            <div className="job-exhibit-board__media">
              {exhibitImage ? <img alt={exhibitJob.job_title} src={exhibitImage} /> : <div className="job-card-showcase__placeholder" />}
            </div>
            <div className="job-exhibit-board__shade" />
            <div className="job-exhibit-board__content">
              <p className="eyebrow">Representative Job</p>
              <h2>{exhibitJob.job_title}</h2>
              <p>{displaySummary(exhibitJob.summary)}</p>
              {exhibitMeta.length > 0 ? (
                <div className="job-exhibit-board__meta">
                  {exhibitMeta.map((item) => (
                    <span key={`${exhibitJob.job_id}-${item}`}>{item}</span>
                  ))}
                </div>
              ) : null}
              <div className="badge-row">
                {isDisplayValue(exhibitJob.job_level) ? <span className="tag">{exhibitJob.job_level}</span> : null}
                {exhibitSkills.map((skill) => (
                  <span className="tag" key={`${exhibitJob.job_id}-${skill}`}>
                    {skill}
                  </span>
                ))}
              </div>
            </div>
            <button
              aria-label="上一张代表岗位展板"
              className="job-exhibit-arrow job-exhibit-arrow--left"
              disabled={exhibitJobs.length === 0}
              onClick={() => handleExhibitSelect((exhibitIndex - 1 + exhibitJobs.length) % exhibitJobs.length)}
              type="button"
            >
              ‹
            </button>
            <button
              aria-label="下一张代表岗位展板"
              className="job-exhibit-arrow job-exhibit-arrow--right"
              disabled={exhibitJobs.length === 0}
              onClick={() => handleExhibitSelect((exhibitIndex + 1) % exhibitJobs.length)}
              type="button"
            >
              ›
            </button>
            <div className="job-exhibit-dots">
              {exhibitJobs.slice(0, 8).map((job, index) => (
                <button
                  aria-label={`切换到 ${job.job_title}`}
                  className={index === exhibitIndex ? "job-exhibit-dot job-exhibit-dot--active" : "job-exhibit-dot"}
                  key={`${job.job_id}-dot`}
                  onClick={() => handleExhibitSelect(index)}
                  type="button"
                />
              ))}
            </div>
          </>
        ) : (
          <div className="empty-card">
            <h3>暂无代表岗位展板</h3>
            <p className="panel-empty">请先根据 jobs_master 和 job_cleaning_master 生成岗位画像。</p>
          </div>
        )}
      </section>

      <section className="job-gallery-toolbar glass-card">
        <form className="job-gallery-search" onSubmit={(event) => void handleGallerySearch(event)}>
          <label className="field-group">
            <span className="field-label">搜索具体岗位</span>
            <input
              className="text-input"
              onChange={(event) => setGallerySearch(event.target.value)}
              placeholder="搜索岗位名、公司、城市、地址或关键词"
              value={gallerySearch}
            />
          </label>
          <div className="button-row">
            <button className="primary-button" type="submit">
              搜索岗位
            </button>
            <button className="ghost-button" onClick={onNavigateHome} type="button">
              返回工作台
            </button>
          </div>
        </form>
        <div className="job-gallery-guide" aria-label="快捷岗位导览">
          {QUICK_SEARCHES.map((query) => (
            <button
              className={gallerySearch === query ? "job-gallery-guide__chip job-gallery-guide__chip--active" : "job-gallery-guide__chip"}
              key={query}
              onClick={() => void handleQuickSearch(query)}
              type="button"
            >
              {query}
            </button>
          ))}
        </div>
      </section>

      <section className="job-result-section">
        <div className="job-result-section__head">
          <div>
            <p className="eyebrow">Search Results</p>
            <h2>岗位信息卡</h2>
          </div>
          <span className={`job-result-section__status job-result-section__status--${searchState}`}>{searchMessage}</span>
        </div>
        <div className="job-results-grid">
          {searchJobs.map((job) => {
            const location = compactLocation(job);
            const chips = [job.industry, job.company_size, job.company_type].filter(isDisplayValue);
            const skills = displayList(job.must_have_skills).slice(0, 5);

            return (
              <article
                className={[
                  "job-result-card",
                  getJobFamilyClass(job),
                  job.job_id === selectedResultJobId ? "job-result-card--active" : "",
                ].filter(Boolean).join(" ")}
                key={job.job_id}
              >
                <button className="job-result-card__hitbox" onClick={() => void loadPathByJob(job)} type="button">
                  <span className="sr-only">查看 {job.job_title}</span>
                </button>
                <div className="job-result-card__top">
                  <div>
                    {isDisplayValue(job.job_level) ? <p className="eyebrow">{job.job_level}</p> : null}
                    <h3>{job.job_title}</h3>
                  </div>
                  {isDisplayValue(job.salary_range) ? <strong className="job-result-card__salary">{job.salary_range}</strong> : null}
                </div>
                {isDisplayValue(job.company_name) ? <p className="job-result-card__company">{job.company_name}</p> : null}
                {location ? <p className="job-result-card__location">{location}</p> : null}
                {chips.length > 0 ? (
                  <div className="job-result-card__chips">
                    {chips.map((item) => (
                      <span key={`${job.job_id}-${item}`}>{item}</span>
                    ))}
                  </div>
                ) : null}
                <p className="job-result-card__summary">{displaySummary(job.summary)}</p>
                {skills.length > 0 ? (
                  <div className="badge-row">
                    {skills.map((skill) => (
                      <span className="tag" key={`${job.job_id}-${skill}`}>
                        {skill}
                      </span>
                    ))}
                  </div>
                ) : null}
                <button className="job-result-card__action" onClick={() => void loadPathByJob(job)} type="button">
                  查看成长路线
                </button>
              </article>
            );
          })}
        </div>
      </section>

      <section className="job-path-layout">
        <article className="glass-card job-path-sidepanel">
          <div className="panel-title">
            <p className="eyebrow">Path Explorer</p>
            <h2>路径分析入口</h2>
          </div>

          <form className="field-group" onSubmit={(event) => void handleJobTitleAnalysis(event)}>
            <span className="field-label">按岗位搜索发展路径</span>
            <input
              className="text-input"
              onChange={(event) => setAnalysisSearch(event.target.value)}
              placeholder="例如：后端开发工程师"
              value={analysisSearch}
            />
            <button className="secondary-button" type="submit">
              搜索岗位路径
            </button>
          </form>

          <div className="field-group">
            <span className="field-label">按学生画像联动分析</span>
            <select
              className="text-input"
              onChange={(event) => setSelectedStudentProfileId(event.target.value ? Number(event.target.value) : "")}
              value={selectedStudentProfileId}
            >
              <option value="">选择一个学生画像</option>
              {studentProfiles.map((profile) => (
                <option key={profile.profile_id} value={profile.profile_id}>
                  #{profile.profile_id} - {profile.career_intention || profile.summary}
                </option>
              ))}
            </select>
            <button className="secondary-button" disabled={!selectedStudentProfileId} onClick={() => void handleStudentProfileAnalysis()} type="button">
              用学生画像分析
            </button>
            {selectedStudentProfile ? <p className="muted-text">{selectedStudentProfile.summary}</p> : null}
          </div>

          <aside className={`status-panel status-panel--${analysisState}`}>
            <span>路径状态</span>
            <strong>{analysisMessage}</strong>
          </aside>
        </article>

        <article className="glass-card job-path-visual">
          <div className="panel-title">
            <p className="eyebrow">Timeline Journey</p>
            <h2>{pathDetail?.selected_job.job_title ?? "岗位成长路线"}</h2>
            <p className="muted-text">
              {pathDetail ? `来源：${pathDetail.source_mode} / ${pathDetail.source_label}` : "等待分析结果"}
            </p>
          </div>

          {timelineSteps.length > 0 ? (
            <>
              <div className="path-rail">
                <div className="path-rail__line" />
                <div className="path-rail__walker" style={{ left: getWalkerPosition(timelineSteps.length, activeTimelineIndex) }}>
                  <span className="path-rail__walker-shadow" />
                  <span className="timeline-assistant-avatar" aria-hidden="true">
                    <span className="assistant-avatar__spark assistant-avatar__spark--one" />
                    <span className="assistant-avatar__spark assistant-avatar__spark--two" />
                    <span className="assistant-avatar__halo" />
                    <span className="assistant-avatar__hair assistant-avatar__hair--back" />
                    <span className="assistant-avatar__face">
                      <span className="assistant-avatar__bang assistant-avatar__bang--left" />
                      <span className="assistant-avatar__bang assistant-avatar__bang--center" />
                      <span className="assistant-avatar__bang assistant-avatar__bang--right" />
                      <span className="assistant-avatar__ribbon assistant-avatar__ribbon--left" />
                      <span className="assistant-avatar__ribbon assistant-avatar__ribbon--right" />
                      <span className="assistant-avatar__eyes">
                        <span />
                        <span />
                      </span>
                      <span className="assistant-avatar__mouth" />
                      <span className="assistant-avatar__blush assistant-avatar__blush--left" />
                      <span className="assistant-avatar__blush assistant-avatar__blush--right" />
                    </span>
                  </span>
                </div>
                <div className="path-rail__stages">
                  {timelineSteps.map((step, index) => (
                    <button
                      className={`path-stage${index === activeTimelineIndex ? " path-stage--active" : ""}`}
                      key={`${step.title}-${index}`}
                      onClick={() => setActiveTimelineIndex(index)}
                      type="button"
                    >
                      <span className="path-stage__dot" />
                      <strong>{step.title}</strong>
                      <span>{step.phase}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="path-stage-detail">
                <div className="path-stage-detail__card">
                  <p className="eyebrow">{timelineSteps[activeTimelineIndex]?.phase}</p>
                  <h3>{timelineSteps[activeTimelineIndex]?.title}</h3>
                  <p className="muted-text">{timelineSteps[activeTimelineIndex]?.description}</p>
                  <div className="badge-row">
                    {(timelineSteps[activeTimelineIndex]?.skills ?? []).map((skill) => (
                      <span className="tag" key={`${timelineSteps[activeTimelineIndex]?.title}-${skill}`}>
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="path-stage-detail__card">
                  <p className="eyebrow">Path Samples</p>
                  <h3>图文路线样例</h3>
                  {(timelineSteps[activeTimelineIndex]?.path_examples ?? []).length ? (
                    <ul className="bullet-list">
                      {timelineSteps[activeTimelineIndex]?.path_examples.map((path, index) => (
                        <li key={`${path.join("-")}-${index}`}>{path.join(" -> ")}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="panel-empty">这一阶段更适合作为连续成长中的一个节点来理解。</p>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="empty-card">
              <h3>暂时没有路径内容</h3>
              <p className="panel-empty">你可以先从搜索结果选择岗位，或者用岗位搜索 / 学生画像联动来生成路线。</p>
            </div>
          )}
        </article>
      </section>
    </main>
  );
}

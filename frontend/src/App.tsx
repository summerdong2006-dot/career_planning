import { useEffect, useState } from "react";

import { getCurrentUser, loginAccount, logoutAccount, registerAccount } from "./features/auth/api";
import type { AuthSessionResponse, AuthUser } from "./features/auth/types";
import { JobGraphPage } from "./features/jobGraph/pages/JobGraphPage";
import { RecommendationPage } from "./features/matching/pages/RecommendationPage";
import { ReportDetailPage } from "./features/reporting/pages/ReportDetailPage";
import { ReportGeneratePage } from "./features/reporting/pages/ReportGeneratePage";
import { ResumeGeneratePage } from "./features/resumes/pages/ResumeGeneratePage";
import { StudentProfileGeneratePage } from "./features/studentProfile/pages/StudentProfileGeneratePage";
import { WorkspaceDashboardPage } from "./features/workspace/pages/WorkspaceDashboardPage";
import { clearAuthToken, getAuthToken, setAuthToken } from "./shared/authStorage";
import {
  buildDashboardPath,
  buildJobGraphPath,
  buildJobRecommendationPath,
  buildReportGeneratePath,
  buildReportPath,
  buildResumeGeneratePath,
  buildStudentProfilePath,
  useAppRouter
} from "./shared/router";

import "./styles.css";

const DEMO_ACCOUNT = {
  displayName: "Demo User",
  email: "demo@example.com",
  password: "123456"
};

async function ensureDemoSession(): Promise<AuthSessionResponse> {
  try {
    return await loginAccount({
      email: DEMO_ACCOUNT.email,
      password: DEMO_ACCOUNT.password
    });
  } catch {
    try {
      return await registerAccount(DEMO_ACCOUNT);
    } catch {
      return loginAccount({
        email: DEMO_ACCOUNT.email,
        password: DEMO_ACCOUNT.password
      });
    }
  }
}

function App() {
  const { route, navigate } = useAppRouter();
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [sessionState, setSessionState] = useState<"loading" | "ready">("loading");

  useEffect(() => {
    const bootstrapSession = async () => {
      try {
        const token = getAuthToken();
        if (token) {
          const user = await getCurrentUser();
          setCurrentUser(user);
          setSessionState("ready");
          return;
        }

        const session = await ensureDemoSession();
        setAuthToken(session.token);
        setCurrentUser(session.user);
        setSessionState("ready");
      } catch {
        clearAuthToken();
        setCurrentUser(null);
        setSessionState("ready");
      }
    };

    void bootstrapSession();
  }, []);

  const handleLogout = async () => {
    try {
      await logoutAccount();
    } catch {
      // best effort
    }

    clearAuthToken();
    setCurrentUser(null);
    setSessionState("loading");

    const session = await ensureDemoSession();
    setAuthToken(session.token);
    setCurrentUser(session.user);
    setSessionState("ready");
    navigate(buildDashboardPath());
  };

  if (sessionState === "loading") {
    return (
      <main className="app-shell">
        <section className="hero-card glass-card">
          <div>
            <p className="eyebrow">Demo Mode</p>
            <h1>正在初始化演示站点</h1>
            <p className="hero-copy">系统会自动进入默认 Demo 账号，方便直接演示画像、推荐、图谱、报告和简历全链路。</p>
          </div>
          <aside className="status-panel status-panel--loading">
            <span>当前状态</span>
            <strong>正在准备 Demo 会话，请稍候。</strong>
          </aside>
        </section>
      </main>
    );
  }

  if (!currentUser) {
    return (
      <main className="app-shell">
        <section className="hero-card glass-card">
          <div>
            <p className="eyebrow">Demo Mode</p>
            <h1>演示账号初始化失败</h1>
            <p className="hero-copy">请刷新页面重试，或检查后端鉴权接口和数据库是否正常。</p>
          </div>
          <aside className="status-panel status-panel--error">
            <span>当前状态</span>
            <strong>未能自动建立 Demo 会话。</strong>
          </aside>
        </section>
      </main>
    );
  }

  const navItems = [
    { label: "工作台", path: buildDashboardPath(), active: route.name === "dashboard" },
    { label: "学生画像", path: buildStudentProfilePath(), active: route.name === "student-profile" },
    { label: "岗位推荐", path: buildJobRecommendationPath(), active: route.name === "job-recommendation" },
    { label: "岗位图谱", path: buildJobGraphPath(), active: route.name === "job-graph" },
    { label: "职业报告", path: buildReportGeneratePath(), active: route.name === "report-generate" || route.name === "report-detail" },
    { label: "定制简历", path: buildResumeGeneratePath(), active: route.name === "resume-generate" }
  ];

  let content = (
    <WorkspaceDashboardPage
      onCreateProfile={() => navigate(buildStudentProfilePath())}
      onOpenRecommendations={(studentProfileId) => navigate(buildJobRecommendationPath(studentProfileId))}
      onOpenReport={(reportId) => navigate(buildReportPath(reportId))}
      onOpenResume={(studentProfileId) => navigate(buildResumeGeneratePath(studentProfileId))}
    />
  );

  if (route.name === "student-profile") {
    content = (
      <StudentProfileGeneratePage
        onOpenJobRecommendations={(studentProfileId) => navigate(buildJobRecommendationPath(studentProfileId))}
        onOpenReportWorkspace={(studentProfileId) => navigate(buildReportGeneratePath(studentProfileId))}
        onOpenResumeWorkspace={(studentProfileId) => navigate(buildResumeGeneratePath(studentProfileId))}
      />
    );
  }

  if (route.name === "job-recommendation") {
    content = (
      <RecommendationPage
        initialStudentProfileId={route.studentProfileId}
        onBackHome={() => navigate(buildDashboardPath())}
        onOpenReportWorkspace={(studentProfileId) => navigate(buildReportGeneratePath(studentProfileId))}
        onOpenResumeWorkspace={(studentProfileId) => navigate(buildResumeGeneratePath(studentProfileId))}
      />
    );
  }

  if (route.name === "job-graph") {
    content = <JobGraphPage onNavigateHome={() => navigate(buildDashboardPath())} />;
  }

  if (route.name === "report-generate") {
    content = (
      <ReportGeneratePage
        initialStudentProfileId={route.studentProfileId}
        onNavigateHome={() => navigate(buildDashboardPath())}
        onOpenReport={(reportId) => navigate(buildReportPath(reportId))}
      />
    );
  }

  if (route.name === "report-detail") {
    content = (
      <ReportDetailPage
        onNavigateHome={() => navigate(buildDashboardPath())}
        onOpenReport={(reportId) => navigate(buildReportPath(reportId))}
        reportId={route.reportId}
      />
    );
  }

  if (route.name === "resume-generate") {
    content = <ResumeGeneratePage initialStudentProfileId={route.studentProfileId} onNavigateHome={() => navigate(buildDashboardPath())} />;
  }

  return (
    <div className="site-shell">
      <header className="site-header">
        <div className="site-header__brand">
          <p className="eyebrow">Career Planning</p>
          <strong>AI 职业规划网站</strong>
        </div>
        <nav className="site-nav">
          {navItems.map((item) => (
            <button
              className={item.active ? "primary-button" : "ghost-button"}
              key={item.path}
              onClick={() => navigate(item.path)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="site-header__user">
          <span>{currentUser.display_name}</span>
          <button className="secondary-button" onClick={() => void handleLogout()} type="button">
            重置演示会话
          </button>
        </div>
      </header>
      {content}
    </div>
  );
}

export default App;

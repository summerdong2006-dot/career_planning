import { type ChangeEvent, useEffect, useRef, useState } from "react";

import { AssistantWidget } from "./features/assistant/components/AssistantWidget";
import { deleteCurrentUser, getCurrentUser, logoutAccount, updateCurrentUser } from "./features/auth/api";
import type { AuthSessionResponse, AuthUser } from "./features/auth/types";
import { AuthPage } from "./features/auth/pages/AuthPage";
import { JobGraphPage } from "./features/jobGraph/pages/JobGraphPage";
import { RecommendationPage } from "./features/matching/pages/RecommendationPage";
import { ReportDetailPage } from "./features/reporting/pages/ReportDetailPage";
import { ReportGeneratePage } from "./features/reporting/pages/ReportGeneratePage";
import { ResumeGeneratePage } from "./features/resumes/pages/ResumeGeneratePage";
import { StudentProfileGeneratePage } from "./features/studentProfile/pages/StudentProfileGeneratePage";
import { WorkspaceDashboardPage } from "./features/workspace/pages/WorkspaceDashboardPage";
import { clearAuthToken, getAuthToken, setAuthToken } from "./shared/authStorage";
import { clearStoredAvatar, getStoredAvatar, setStoredAvatar } from "./shared/avatarStorage";
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

type ProfileCenterProps = {
  avatarUrl: string | null;
  isOpen: boolean;
  onAvatarChange: (dataUrl: string | null) => void;
  onClose: () => void;
  onDeleteAccount: () => Promise<void>;
  onLogout: () => Promise<void>;
  onUserUpdated: (user: AuthUser) => void;
  user: AuthUser;
};

function ProfileCenter({
  avatarUrl,
  isOpen,
  onAvatarChange,
  onClose,
  onDeleteAccount,
  onLogout,
  onUserUpdated,
  user
}: ProfileCenterProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [displayName, setDisplayName] = useState(user.display_name);
  const [email, setEmail] = useState(user.email);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState("可以修改头像、昵称、邮箱和密码。");
  const [requestState, setRequestState] = useState<"idle" | "loading" | "success" | "error">("idle");

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    setDisplayName(user.display_name);
    setEmail(user.email);
    setCurrentPassword("");
    setNewPassword("");
    setMessage("可以修改头像、昵称、邮箱和密码。");
    setRequestState("idle");
  }, [isOpen, user.display_name, user.email]);

  if (!isOpen) {
    return null;
  }

  const initials = user.display_name.trim().slice(0, 1).toUpperCase() || "U";

  const handleAvatarUpload = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    if (!file.type.startsWith("image/")) {
      setRequestState("error");
      setMessage("请选择图片文件作为头像。");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : null;
      if (result) {
        onAvatarChange(result);
        setRequestState("success");
        setMessage("头像已更新。");
      }
    };
    reader.readAsDataURL(file);
  };

  const handleSave = async () => {
    if (!displayName.trim() || !email.trim()) {
      setRequestState("error");
      setMessage("昵称和邮箱不能为空。");
      return;
    }
    if (newPassword && !currentPassword) {
      setRequestState("error");
      setMessage("修改密码前请输入当前密码。");
      return;
    }

    setRequestState("loading");
    setMessage("正在保存个人资料。");
    try {
      const updated = await updateCurrentUser({
        currentPassword: currentPassword || undefined,
        displayName: displayName.trim(),
        email: email.trim(),
        newPassword: newPassword || undefined
      });
      onUserUpdated(updated);
      setCurrentPassword("");
      setNewPassword("");
      setRequestState("success");
      setMessage("个人资料已保存。");
    } catch (error) {
      setRequestState("error");
      setMessage(error instanceof Error ? error.message : "保存失败。");
    }
  };

  return (
    <div className="profile-center-backdrop" role="presentation">
      <section className="profile-center-panel" aria-label="个人中心">
        <header className="profile-center-panel__header">
          <div>
            <p className="studio-eyebrow">Profile Center</p>
            <h2>个人中心</h2>
          </div>
          <button className="profile-center-close" onClick={onClose} type="button">
            ×
          </button>
        </header>

        <div className="profile-center-avatar-row">
          <button className="profile-center-avatar" onClick={() => fileInputRef.current?.click()} type="button">
            {avatarUrl ? <img alt="用户头像" src={avatarUrl} /> : <span>{initials}</span>}
          </button>
          <div>
            <strong>{user.display_name}</strong>
            <p>{user.email}</p>
            <div className="profile-center-actions-inline">
              <button className="studio-link" onClick={() => fileInputRef.current?.click()} type="button">
                上传头像
              </button>
              {avatarUrl ? (
                <button className="studio-link" onClick={() => onAvatarChange(null)} type="button">
                  移除头像
                </button>
              ) : null}
            </div>
          </div>
          <input accept="image/*" hidden onChange={handleAvatarUpload} ref={fileInputRef} type="file" />
        </div>

        <div className={`profile-center-message profile-center-message--${requestState}`}>{message}</div>

        <div className="profile-center-form">
          <label className="field-group">
            <span className="field-label">昵称</span>
            <input className="text-input" onChange={(event) => setDisplayName(event.target.value)} value={displayName} />
          </label>
          <label className="field-group">
            <span className="field-label">邮箱</span>
            <input className="text-input" onChange={(event) => setEmail(event.target.value)} type="email" value={email} />
          </label>
          <label className="field-group">
            <span className="field-label">当前密码</span>
            <input
              className="text-input"
              onChange={(event) => setCurrentPassword(event.target.value)}
              placeholder="修改密码时填写"
              type="password"
              value={currentPassword}
            />
          </label>
          <label className="field-group">
            <span className="field-label">新密码</span>
            <input
              className="text-input"
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="不修改可留空"
              type="password"
              value={newPassword}
            />
          </label>
        </div>

        <footer className="profile-center-footer">
          <button className="studio-button studio-button--primary" disabled={requestState === "loading"} onClick={() => void handleSave()} type="button">
            保存修改
          </button>
          <button className="studio-button" onClick={() => void onLogout()} type="button">
            退出登录
          </button>
          <button className="profile-center-danger" onClick={() => void onDeleteAccount()} type="button">
            注销账号
          </button>
        </footer>
      </section>
    </div>
  );
}

function App() {
  const { route, navigate } = useAppRouter();
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [sessionState, setSessionState] = useState<"loading" | "ready">("loading");
  const [isProfileCenterOpen, setIsProfileCenterOpen] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);

  useEffect(() => {
    const bootstrapSession = async () => {
      try {
        const token = getAuthToken();
        if (token) {
          const user = await getCurrentUser();
          setCurrentUser(user);
          setAvatarUrl(getStoredAvatar(user.id));
          setSessionState("ready");
          return;
        }

        setCurrentUser(null);
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
    if (currentUser) {
      setAvatarUrl(null);
    }
    setCurrentUser(null);
    setSessionState("ready");
    setIsProfileCenterOpen(false);
    navigate(buildDashboardPath());
  };

  const handleAuthenticated = (session: AuthSessionResponse) => {
    setAuthToken(session.token);
    setCurrentUser(session.user);
    setAvatarUrl(getStoredAvatar(session.user.id));
    setSessionState("ready");
    navigate(buildDashboardPath());
  };

  const handleAvatarChange = (dataUrl: string | null) => {
    if (!currentUser) {
      return;
    }
    if (dataUrl) {
      setStoredAvatar(currentUser.id, dataUrl);
    } else {
      clearStoredAvatar(currentUser.id);
    }
    setAvatarUrl(dataUrl);
  };

  const handleDeleteAccount = async () => {
    if (!currentUser) {
      return;
    }
    const confirmed = window.confirm("确定要注销当前账号吗？此操作会移除账号登录信息，且不可撤销。");
    if (!confirmed) {
      return;
    }
    await deleteCurrentUser();
    clearStoredAvatar(currentUser.id);
    clearAuthToken();
    setAvatarUrl(null);
    setCurrentUser(null);
    setIsProfileCenterOpen(false);
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
    return <AuthPage onAuthenticated={handleAuthenticated} />;
  }

  const navItems = [
    { label: "工作台", path: buildDashboardPath(), active: route.name === "dashboard" },
    { label: "学生画像", path: buildStudentProfilePath(), active: route.name === "student-profile" },
    { label: "岗位推荐", path: buildJobRecommendationPath(), active: route.name === "job-recommendation" },
    { label: "岗位展览", path: buildJobGraphPath(), active: route.name === "job-graph" },
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
    <div className={route.name === "dashboard" ? "site-shell site-shell--dashboard" : "site-shell"}>
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
          <button className="profile-center-trigger" onClick={() => setIsProfileCenterOpen(true)} type="button">
            <span className="profile-center-trigger__avatar">
              {avatarUrl ? <img alt="用户头像" src={avatarUrl} /> : currentUser.display_name.slice(0, 1).toUpperCase()}
            </span>
            <span>{currentUser.display_name}</span>
            <strong>个人中心</strong>
          </button>
        </div>
      </header>
      {content}
      <ProfileCenter
        avatarUrl={avatarUrl}
        isOpen={isProfileCenterOpen}
        onAvatarChange={handleAvatarChange}
        onClose={() => setIsProfileCenterOpen(false)}
        onDeleteAccount={handleDeleteAccount}
        onLogout={handleLogout}
        onUserUpdated={setCurrentUser}
        user={currentUser}
      />
      <AssistantWidget currentUser={currentUser} route={route} />
    </div>
  );
}

export default App;

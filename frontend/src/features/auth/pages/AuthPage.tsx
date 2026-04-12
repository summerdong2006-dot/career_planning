import { useState } from "react";

import { loginAccount, registerAccount } from "../api";
import type { AuthSessionResponse } from "../types";

type AuthMode = "login" | "register";
type RequestState = "idle" | "loading" | "success" | "error";

type AuthPageProps = {
  onAuthenticated: (session: AuthSessionResponse) => void;
};

export function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [requestState, setRequestState] = useState<RequestState>("idle");
  const [message, setMessage] = useState("登录后即可创建自己的学生画像、职业报告和定制简历。");

  const handleSubmit = async () => {
    if (!email.trim() || !password.trim() || (mode === "register" && !displayName.trim())) {
      setRequestState("error");
      setMessage("请完整填写账号信息。");
      return;
    }

    setRequestState("loading");
    setMessage(mode === "login" ? "正在登录，请稍候。" : "正在创建账号，请稍候。");

    try {
      const session =
        mode === "login"
          ? await loginAccount({ email: email.trim(), password: password.trim() })
          : await registerAccount({
              email: email.trim(),
              displayName: displayName.trim(),
              password: password.trim()
            });
      setRequestState("success");
      setMessage(`${session.user.display_name}，欢迎回来。`);
      onAuthenticated(session);
    } catch (error) {
      setRequestState("error");
      setMessage(error instanceof Error ? error.message : "认证失败。");
    }
  };

  return (
    <main className="auth-shell">
      <section className="auth-panel glass-card">
        <div className="auth-copy">
          <p className="eyebrow">AI Career Planning</p>
          <h1>登录你的职业规划工作台</h1>
          <p className="hero-copy">
            登录后可以保存学生画像、岗位推荐、职业报告和定制简历，让每一次职业探索都能连续推进。
          </p>
          <div className={`status-panel status-panel--${requestState}`}>
            <span>当前状态</span>
            <strong>{message}</strong>
          </div>
        </div>

        <article className="form-card auth-form-card">
          <div className="auth-switcher">
            <button
              className={mode === "login" ? "primary-button" : "secondary-button"}
              onClick={() => setMode("login")}
              type="button"
            >
              登录
            </button>
            <button
              className={mode === "register" ? "primary-button" : "secondary-button"}
              onClick={() => setMode("register")}
              type="button"
            >
              注册
            </button>
          </div>

          <div className="panel-title">
            <p className="eyebrow">Account</p>
            <h2>{mode === "login" ? "登录工作台" : "创建新账号"}</h2>
            <p className="muted-text">使用邮箱和密码进入系统，后续生成的画像、报告和简历都会保存在你的账号下。</p>
          </div>

          <div className="form-grid form-grid--single">
            {mode === "register" ? (
              <label className="field-group">
                <span className="field-label">显示名称</span>
                <input className="text-input" onChange={(event) => setDisplayName(event.target.value)} value={displayName} />
              </label>
            ) : null}

            <label className="field-group">
              <span className="field-label">邮箱</span>
              <input className="text-input" onChange={(event) => setEmail(event.target.value)} type="email" value={email} />
            </label>

            <label className="field-group">
              <span className="field-label">密码</span>
              <input
                className="text-input"
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                value={password}
              />
            </label>
          </div>

          <div className="button-row">
            <button className="primary-button" onClick={() => void handleSubmit()} type="button">
              {mode === "login" ? "进入网站" : "注册并进入"}
            </button>
          </div>
        </article>
      </section>
    </main>
  );
}

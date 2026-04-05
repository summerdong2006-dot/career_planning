type WorkbenchPlaceholderPageProps = {
  eyebrow: string;
  title: string;
  description: string;
  studentProfileId?: number;
  primaryActionLabel: string;
  onPrimaryAction: () => void;
  onBackHome: () => void;
};

export function WorkbenchPlaceholderPage({
  eyebrow,
  title,
  description,
  studentProfileId,
  primaryActionLabel,
  onPrimaryAction,
  onBackHome
}: WorkbenchPlaceholderPageProps) {
  return (
    <main className="app-shell">
      <section className="hero-card glass-card">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p className="hero-copy">{description}</p>
        </div>
        <aside className="status-panel status-panel--idle">
          <span>当前上下文</span>
          <strong>{studentProfileId ? `已带入 student_profile_id=${studentProfileId}` : "当前未带入 student_profile_id"}</strong>
        </aside>
      </section>

      <section className="two-column-grid">
        <article className="form-card glass-card">
          <div className="panel-title">
            <p className="eyebrow">Current Stage</p>
            <h2>页面占位已打通</h2>
            <p className="muted-text">这一步先保证画像页可以跳转过来，后续接入真实推荐或定制简历工作台时，可直接沿用当前路由和上下文透传方式。</p>
          </div>

          <div className="button-row">
            <button className="primary-button" onClick={onPrimaryAction} type="button">
              {primaryActionLabel}
            </button>
            <button className="ghost-button" onClick={onBackHome} type="button">
              返回画像页
            </button>
          </div>
        </article>

        <article className="info-card glass-card">
          <div className="panel-title">
            <p className="eyebrow">Integration</p>
            <h2>预留说明</h2>
          </div>

          <div className="list-stack">
            <article className="list-card">
              <h4>路由已可演示</h4>
              <p className="muted-text">按钮点击后可进入对应页面，不会中断主流程演示。</p>
            </article>
            <article className="list-card">
              <h4>画像上下文已预留</h4>
              <p className="muted-text">后续若要自动请求推荐、生成报告或简历，可直接读取 `student_profile_id` 继续串联。</p>
            </article>
          </div>
        </article>
      </section>
    </main>
  );
}

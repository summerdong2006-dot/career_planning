import { useEffect, useMemo, useRef, useState } from "react";

import type { AuthUser } from "../../auth/types";
import type { AppRoute } from "../../../shared/router";
import { renderMarkdownToHtml } from "../../../shared/markdown";
import { chatWithAssistant } from "../api";
import type { AssistantChatRequest, AssistantMessage, AssistantPageContext } from "../types";

type AssistantWidgetProps = {
  currentUser: AuthUser;
  route: AppRoute;
};

type RequestState = "idle" | "loading" | "error";

const PAGE_LABELS: Record<AppRoute["name"], string> = {
  dashboard: "工作台",
  "job-graph": "岗位图谱",
  "job-recommendation": "岗位推荐",
  login: "登录页",
  "report-detail": "报告详情",
  "report-generate": "报告生成",
  "resume-generate": "简历生成",
  "student-profile": "学生画像"
};

const STARTER_PROMPTS = [
  "我现在这个页面适合先做什么？",
  "帮我理解这个系统的使用流程",
  "简历和职业报告分别适合什么时候生成？"
];

function buildRouteContext(route: AppRoute): AssistantPageContext {
  const context: AssistantPageContext = {
    page_label: PAGE_LABELS[route.name],
    page_name: route.name
  };

  if ("studentProfileId" in route && route.studentProfileId) {
    context.student_profile_id = route.studentProfileId;
  }

  if ("reportId" in route) {
    context.report_id = route.reportId;
  }

  return context;
}

export function AssistantWidget({ currentUser, route }: AssistantWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<AssistantMessage[]>([
    {
      role: "assistant",
      content: `你好，${currentUser.display_name}。我是小涯，可以帮你理解页面功能、梳理下一步操作，也可以回答职业规划和求职材料相关问题。`
    }
  ]);
  const [requestState, setRequestState] = useState<RequestState>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [modelLabel, setModelLabel] = useState("");
  const [unreadCount, setUnreadCount] = useState(0);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const speakingTimerRef = useRef<number | null>(null);

  const context = useMemo(() => buildRouteContext(route), [route]);

  useEffect(() => {
    if (isOpen) {
      setUnreadCount(0);
    }
  }, [isOpen]);

  useEffect(() => {
    return () => {
      if (speakingTimerRef.current) {
        window.clearTimeout(speakingTimerRef.current);
      }
    };
  }, []);

  const triggerSpeaking = (durationMs: number) => {
    setIsSpeaking(true);
    if (speakingTimerRef.current) {
      window.clearTimeout(speakingTimerRef.current);
    }
    speakingTimerRef.current = window.setTimeout(() => {
      setIsSpeaking(false);
      speakingTimerRef.current = null;
    }, durationMs);
  };

  const sendMessage = async (content: string) => {
    const normalized = content.trim();
    if (!normalized || requestState === "loading") {
      return;
    }

    const nextMessages: AssistantMessage[] = [...messages, { role: "user", content: normalized }];
    const payload: AssistantChatRequest = {
      context,
      messages: nextMessages
    };

    setMessages(nextMessages);
    setInput("");
    setRequestState("loading");
    setErrorMessage("");
    setIsSpeaking(true);

    try {
      const response = await chatWithAssistant(payload);
      setMessages((current) => [...current, { role: "assistant", content: response.reply }]);
      setModelLabel(`${response.provider} / ${response.model}`);
      setRequestState("idle");
      triggerSpeaking(1600);
      if (!isOpen) {
        setUnreadCount((current) => current + 1);
      }
    } catch (error) {
      setRequestState("error");
      setErrorMessage(error instanceof Error ? error.message : "小涯暂时不可用，请稍后重试。");
      setIsSpeaking(false);
    }
  };

  return (
    <div className={`assistant-widget${isOpen ? " assistant-widget--open" : ""}`}>
      {isOpen ? (
        <section className="assistant-panel glass-card" aria-label="AI assistant panel">
          <header className="assistant-panel__header">
            <div>
              <p className="eyebrow">AI Assistant</p>
              <strong>小涯</strong>
            </div>
            <button className="ghost-button" onClick={() => setIsOpen(false)} type="button">
              收起
            </button>
          </header>

          <div className="assistant-panel__meta">
            <span>当前页面：{PAGE_LABELS[route.name]}</span>
            {modelLabel ? <span>模型：{modelLabel}</span> : null}
          </div>

          <div className="assistant-starters">
            {STARTER_PROMPTS.map((prompt) => (
              <button
                className="assistant-chip"
                disabled={requestState === "loading"}
                key={prompt}
                onClick={() => void sendMessage(prompt)}
                type="button"
              >
                {prompt}
              </button>
            ))}
          </div>

          <div className="assistant-thread">
            {messages.map((message, index) => (
              <article
                className={`assistant-message assistant-message--${message.role}`}
                key={`${message.role}-${index}-${message.content.slice(0, 24)}`}
              >
                <span className="assistant-message__role">{message.role === "assistant" ? "小涯" : "你"}</span>
                {message.role === "assistant" ? (
                  <div
                    className="markdown-preview assistant-markdown"
                    dangerouslySetInnerHTML={{
                      __html: renderMarkdownToHtml(message.content, '<p class="preview-empty">小涯暂时没有返回内容。</p>')
                    }}
                  />
                ) : (
                  <p>{message.content}</p>
                )}
              </article>
            ))}

            {requestState === "loading" ? (
              <article className="assistant-message assistant-message--assistant assistant-message--pending">
                <span className="assistant-message__role">小涯</span>
                <div className="markdown-preview assistant-markdown">
                  <p>正在整理回复，请稍等...</p>
                </div>
              </article>
            ) : null}
          </div>

          {errorMessage ? (
            <div className="assistant-error" role="alert">
              {errorMessage}
            </div>
          ) : null}

          <form
            className="assistant-composer"
            onSubmit={(event) => {
              event.preventDefault();
              void sendMessage(input);
            }}
          >
            <textarea
              className="text-area assistant-composer__input"
              onChange={(event) => setInput(event.target.value)}
              placeholder="问我：这个页面下一步做什么、怎么理解岗位推荐、如何优化简历..."
              rows={4}
              value={input}
            />
            <div className="assistant-composer__actions">
              <span>本阶段支持通用问答，已预留页面上下文能力。</span>
              <button className="primary-button" disabled={requestState === "loading" || !input.trim()} type="submit">
                发送
              </button>
            </div>
          </form>
        </section>
      ) : null}

      <div className="assistant-avatar-wrap">
        <div className="assistant-nameplate">
          <strong>小涯</strong>
          <span>Career Senpai</span>
        </div>
        <button
          aria-expanded={isOpen}
          className={`assistant-avatar${isSpeaking || requestState === "loading" ? " assistant-avatar--speaking" : ""}`}
          onClick={() => setIsOpen((current) => !current)}
          type="button"
        >
          {unreadCount > 0 ? <span className="assistant-avatar__badge">{unreadCount > 9 ? "9+" : unreadCount}</span> : null}
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
        </button>
      </div>
    </div>
  );
}

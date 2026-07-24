"use client";

import Link from "next/link";
import { FormEvent, KeyboardEvent, useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AppShell } from "@/components/app/AppShell";
import { apiDelete, apiGet, apiPatch, apiPost, isApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth";

interface ChatMessage {
  id: string;
  role: "user" | "agent";
  text: string;
  pending?: boolean;
  error?: boolean;
  action?: {
    eyebrow: string;
    title: string;
    detail: string;
    href: string;
    label: string;
  };
}

const QUICK_PROMPTS = [
  { icon: "今", title: "整理今天重点", detail: "汇总课程、通知与待办", prompt: "请帮我整理今天最重要的课程、通知和待办，并按优先级说明。" },
  { icon: "排", title: "规划今日安排", detail: "结合空闲时间安排任务", prompt: "请根据我今天的课程和待办，帮我规划一个现实可执行的日程。" },
  { icon: "问", title: "解释办事流程", detail: "先了解步骤和注意事项", prompt: "我想办理一项校园事务，请先告诉我常见流程、需要准备什么，以及哪些步骤需要我确认。" },
  { icon: "材", title: "整理材料清单", detail: "避免申请材料遗漏", prompt: "请帮我整理校园申请常用的材料清单，并提醒我不要在对话里发送敏感证件信息。" },
];

interface WorkspaceChatResponse {
  thread_id: string;
  thread_title: string;
  reply: string;
  provider: string;
  model: string | null;
  request_id: string | null;
  route_source?: "personal" | "platform";
}

interface WorkspaceThread {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface WorkspaceThreadList {
  threads: WorkspaceThread[];
  total: number;
}

interface WorkspaceThreadDetail extends WorkspaceThread {
  messages: Array<{
    id: string;
    role: "user" | "assistant";
    content: string;
    created_at: string;
  }>;
}

type ModelProvider = "OPENAI" | "DEEPSEEK" | "STEPFUN" | "CUSTOM";

interface ModelRouteProfile {
  id: string;
  name: string;
  provider: ModelProvider;
  model: string;
  base_url: string;
  has_api_key: boolean;
}

interface ModelRouteSettings {
  mode: "PLATFORM" | "PERSONAL";
  active_profile_id: string | null;
  profiles: ModelRouteProfile[];
  provider: string;
  model: string;
  base_url: string;
  has_api_key: boolean;
}

const MODEL_PROVIDER_PRESETS: Record<ModelProvider, { label: string; baseUrl: string; model: string }> = {
  OPENAI: { label: "OpenAI", baseUrl: "https://api.openai.com/v1", model: "gpt-4.1-mini" },
  DEEPSEEK: { label: "DeepSeek", baseUrl: "https://api.deepseek.com", model: "deepseek-v4-flash" },
  STEPFUN: { label: "阶跃星辰 StepFun", baseUrl: "https://api.stepfun.com/v1", model: "step-3.5-flash" },
  CUSTOM: { label: "自定义 OpenAI 兼容服务", baseUrl: "", model: "" },
};

function modelProviderLabel(provider: string | null | undefined): string {
  const normalized = (provider ?? "").replace(/^personal-/i, "").toUpperCase();
  if (normalized === "PLATFORM") return "平台模型";
  if (normalized in MODEL_PROVIDER_PRESETS) {
    return MODEL_PROVIDER_PRESETS[normalized as ModelProvider].label;
  }
  return provider || "当前模型";
}

function modelRouteLabel(settings: ModelRouteSettings): string {
  return `${modelProviderLabel(settings.provider)} · ${settings.model || "待配置"}`;
}

function modelIdHint(provider: ModelProvider, model: string): string | null {
  const compact = model.trim().toLowerCase();
  if (provider === "OPENAI" && compact === "gpt5.6-sol") {
    return "OpenAI 模型标识应写为 gpt-5.6-sol（全小写并保留连字符）。";
  }
  return null;
}

interface ModelRouteTestResult {
  healthy: boolean;
  status: string;
  latency_ms: number | null;
  model: string;
}

const INITIAL_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "agent",
  text: "你好，我是你的个人 Agent。你可以直接告诉我想查什么、办什么，或者希望我帮你安排什么。",
};

function WorkspaceContent() {
  const { user } = useAuth();
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const threadLoadRequestRef = useRef(0);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MESSAGE]);
  const [threads, setThreads] = useState<WorkspaceThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [connectionLabel, setConnectionLabel] = useState("模型路由 · 正在读取");
  const [connectionState, setConnectionState] = useState<"idle" | "connecting" | "ready" | "error">("idle");
  const [showAgentSettings, setShowAgentSettings] = useState(false);
  const [routeSettings, setRouteSettings] = useState<ModelRouteSettings | null>(null);
  const [routeMode, setRouteMode] = useState<"PLATFORM" | "PERSONAL">("PLATFORM");
  const [routeProfileId, setRouteProfileId] = useState<string | null>(null);
  const [routeName, setRouteName] = useState("我的模型");
  const [routeProvider, setRouteProvider] = useState<ModelProvider>("STEPFUN");
  const [routeBaseUrl, setRouteBaseUrl] = useState("https://api.stepfun.com/v1");
  const [routeModel, setRouteModel] = useState("step-3.5-flash");
  const [routeApiKey, setRouteApiKey] = useState("");
  const [routeBusy, setRouteBusy] = useState(false);
  const [routeMessage, setRouteMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const applyRouteSettings = useCallback((settings: ModelRouteSettings) => {
    setRouteSettings(settings);
    setRouteMode(settings.mode);
    const active = settings.profiles.find((profile) => profile.id === settings.active_profile_id);
    setRouteProfileId(active?.id ?? null);
    setRouteName(active?.name ?? "我的模型");
    setRouteProvider(active?.provider ?? "STEPFUN");
    setRouteBaseUrl(active?.base_url ?? MODEL_PROVIDER_PRESETS.STEPFUN.baseUrl);
    setRouteModel(active?.model ?? MODEL_PROVIDER_PRESETS.STEPFUN.model);
    setRouteApiKey("");
    setConnectionLabel(modelRouteLabel(settings));
  }, []);

  const openAgentSettings = useCallback(async () => {
    setShowAgentSettings(true);
    setRouteBusy(true);
    setRouteMessage(null);
    try {
      const settings = await apiGet<ModelRouteSettings>("/agents/me/model-route");
      applyRouteSettings(settings);
    } catch {
      setRouteMessage({ type: "error", text: "暂时无法读取模型路由设置。" });
    } finally {
      setRouteBusy(false);
    }
  }, [applyRouteSettings]);

  const persistModelRoute = useCallback(async () => {
    const payload: {
      mode: "PLATFORM" | "PERSONAL";
      profile_id?: string;
      name?: string;
      provider?: ModelProvider;
      base_url?: string;
      model?: string;
      api_key?: string;
    } = {
      mode: routeMode,
      ...(routeMode === "PERSONAL" ? {
        profile_id: routeProfileId ?? undefined,
        name: routeName.trim(),
        provider: routeProvider,
        base_url: routeBaseUrl.trim(),
      } : {}),
      model: routeModel.trim(),
    };
    if (routeApiKey.trim()) payload.api_key = routeApiKey.trim();
    const saved = await apiPatch<ModelRouteSettings>("/agents/me/model-route", payload);
    applyRouteSettings(saved);
    setConnectionState("idle");
    return saved;
  }, [applyRouteSettings, routeApiKey, routeBaseUrl, routeMode, routeModel, routeName, routeProfileId, routeProvider]);

  const selectSavedProfile = (profileId: string) => {
    if (!profileId) {
      const preset = MODEL_PROVIDER_PRESETS.STEPFUN;
      setRouteProfileId(null);
      setRouteName("我的模型");
      setRouteProvider("STEPFUN");
      setRouteBaseUrl(preset.baseUrl);
      setRouteModel(preset.model);
      setRouteApiKey("");
      return;
    }
    const profile = routeSettings?.profiles.find((item) => item.id === profileId);
    if (!profile) return;
    setRouteProfileId(profile.id);
    setRouteName(profile.name);
    setRouteProvider(profile.provider);
    setRouteBaseUrl(profile.base_url);
    setRouteModel(profile.model);
    setRouteApiKey("");
  };

  const selectProvider = (provider: ModelProvider) => {
    const preset = MODEL_PROVIDER_PRESETS[provider];
    setRouteProvider(provider);
    setRouteName(routeProfileId ? routeName : preset.label);
    setRouteBaseUrl(preset.baseUrl);
    setRouteModel(preset.model);
  };

  const handleDeleteRouteProfile = async () => {
    if (!routeProfileId || routeBusy) return;
    setRouteBusy(true);
    setRouteMessage(null);
    try {
      const settings = await apiDelete<ModelRouteSettings>(`/agents/me/model-route/profiles/${routeProfileId}`);
      setRouteSettings(settings);
      setRouteMode(settings.mode);
      selectSavedProfile("");
      setRouteMessage({ type: "success", text: "已删除该模型配置。" });
    } catch (error) {
      setRouteMessage({ type: "error", text: isApiError(error) ? error.message : "删除失败。" });
    } finally {
      setRouteBusy(false);
    }
  };

  const handleRouteSave = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setRouteBusy(true);
    setRouteMessage(null);
    try {
      await persistModelRoute();
      setRouteMessage({ type: "success", text: "已保存，下一次对话将使用该路由。" });
    } catch (error) {
      setRouteMessage({
        type: "error",
        text: isApiError(error) ? error.message : "模型路由保存失败。",
      });
    } finally {
      setRouteBusy(false);
    }
  };

  const handleRouteTest = async () => {
    setRouteBusy(true);
    setRouteMessage(null);
    try {
      await persistModelRoute();
      const result = await apiPost<ModelRouteTestResult>("/agents/me/model-route/test");
      setRouteMessage({
        type: result.healthy ? "success" : "error",
        text: result.healthy
          ? `连接正常 · ${result.model}${result.latency_ms !== null ? ` · ${result.latency_ms} ms` : ""}`
          : result.status,
      });
    } catch (error) {
      setRouteMessage({ type: "error", text: isApiError(error) ? error.message : "连接测试失败。" });
    } finally {
      setRouteBusy(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    const loadRoute = async () => {
      try {
        const settings = await apiGet<ModelRouteSettings>("/agents/me/model-route");
        if (!cancelled) applyRouteSettings(settings);
      } catch {
        if (!cancelled) setConnectionLabel("模型路由 · 读取失败");
      }
    };
    void loadRoute();
    return () => { cancelled = true; };
  }, [applyRouteSettings]);

  useEffect(() => {
    if (!showAgentSettings) return;
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape" && !routeBusy) setShowAgentSettings(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [routeBusy, showAgentSettings]);

  const openThread = useCallback(async (threadId: string) => {
    if (isSending || threadId === activeThreadId) return;
    const previousThreadId = activeThreadId;
    const requestId = ++threadLoadRequestRef.current;
    // Highlight immediately without inserting a loading row into the sidebar.
    // The current conversation remains in place until the next one is ready.
    setActiveThreadId(threadId);
    try {
      const detail = await apiGet<WorkspaceThreadDetail>(`/agents/me/workspace/threads/${threadId}`);
      if (requestId !== threadLoadRequestRef.current) return;
      setMessages([
        INITIAL_MESSAGE,
        ...detail.messages.map((message) => ({
          id: message.id,
          role: message.role === "assistant" ? "agent" as const : "user" as const,
          text: message.content,
        })),
      ]);
    } catch {
      if (requestId === threadLoadRequestRef.current) setActiveThreadId(previousThreadId);
    }
  }, [activeThreadId, isSending]);

  useEffect(() => {
    let cancelled = false;
    const loadThreads = async () => {
      try {
        const result = await apiGet<WorkspaceThreadList>("/agents/me/workspace/threads");
        if (cancelled) return;
        setThreads(result.threads);
        if (result.threads[0]) {
          const detail = await apiGet<WorkspaceThreadDetail>(`/agents/me/workspace/threads/${result.threads[0].id}`);
          if (cancelled) return;
          setActiveThreadId(detail.id);
          setMessages([
            INITIAL_MESSAGE,
            ...detail.messages.map((message) => ({
              id: message.id,
              role: message.role === "assistant" ? "agent" as const : "user" as const,
              text: message.content,
            })),
          ]);
        }
      } finally {
        if (!cancelled) setIsLoadingHistory(false);
      }
    };
    void loadThreads();
    return () => { cancelled = true; };
  }, []);

  const createThread = useCallback(async (): Promise<WorkspaceThread | null> => {
    try {
      const thread = await apiPost<WorkspaceThread>("/agents/me/workspace/threads", {});
      setThreads((current) => [thread, ...current.filter((item) => item.id !== thread.id)]);
      setActiveThreadId(thread.id);
      setMessages([INITIAL_MESSAGE]);
      setInput("");
      return thread;
    } catch {
      setConnectionState("error");
      setConnectionLabel("个人任务 · 创建失败");
      return null;
    }
  }, []);

  useEffect(() => {
    if (!isSending) return;
    const scrollArea = chatScrollRef.current;
    if (scrollArea && messages.length > 1) scrollArea.scrollTop = scrollArea.scrollHeight;
  }, [isSending, messages]);

  const sendPrompt = useCallback(async (prompt: string) => {
    const trimmed = prompt.trim();
    if (!trimmed || isSending) return;
    let threadId = activeThreadId;
    if (!threadId) {
      const thread = await createThread();
      if (!thread) return;
      threadId = thread.id;
    }
    const baseId = `${Date.now()}`;
    const userMessage: ChatMessage = { id: `${baseId}-user`, role: "user", text: trimmed };
    const pendingMessage: ChatMessage = {
      id: `${baseId}-pending`,
      role: "agent",
      text: "正在思考…",
      pending: true,
    };
    setMessages((current) => [...current, userMessage, pendingMessage]);
    setInput("");
    setIsSending(true);
    setConnectionState("connecting");
    setConnectionLabel(`正在连接 ${modelProviderLabel(routeSettings?.provider)}…`);

    try {
      const response = await apiPost<WorkspaceChatResponse>("/agents/me/chat", {
        thread_id: threadId,
        message: trimmed,
      });
      setMessages((current) => current.map((message) => (
        message.id === pendingMessage.id
          ? { id: message.id, role: "agent", text: response.reply }
          : message
      )));
      setConnectionState("ready");
      setConnectionLabel(`${modelProviderLabel(response.provider)} · ${response.model ?? "已连接"}`);
      setActiveThreadId(response.thread_id);
      setThreads((current) => {
        const existing = current.find((thread) => thread.id === response.thread_id);
        const updated: WorkspaceThread = {
          ...(existing ?? {
            id: response.thread_id,
            status: "ACTIVE",
            created_at: new Date().toISOString(),
            message_count: 0,
          }),
          title: response.thread_title,
          updated_at: new Date().toISOString(),
          message_count: (existing?.message_count ?? 0) + 2,
        };
        return [updated, ...current.filter((thread) => thread.id !== response.thread_id)];
      });
    } catch (error) {
      const providerLabel = modelProviderLabel(routeSettings?.provider);
      const upstreamStatus = isApiError(error) && typeof error.details?.status === "number"
        ? error.details.status
        : null;
      const upstreamCode = isApiError(error) && typeof error.details?.upstream_code === "string"
        ? error.details.upstream_code
        : null;
      let reason = "请检查模型标识、API 密钥、接口地址和账户额度。";
      if (upstreamStatus === 401 || upstreamStatus === 403) reason = "API 密钥无效，或当前项目没有该模型的访问权限。";
      if (upstreamStatus === 404 || upstreamCode === "model_not_found") reason = `未找到模型“${routeSettings?.model ?? "当前模型"}”，请核对模型标识。`;
      if (upstreamStatus === 429 && upstreamCode === "insufficient_quota") reason = "OpenAI 账户额度不足，请充值或更换有额度的项目密钥。";
      else if (upstreamStatus === 429) reason = "请求已被限流，或当前账户额度不足。";
      const text = isApiError(error) && [400, 401, 403, 422, 429, 502, 503, 504].includes(error.statusCode)
        ? `${providerLabel} 调用失败。${reason}你的输入已保存在当前任务中。`
        : "这次连接没有成功，但你的输入已保存在当前任务中。请稍后重试。";
      setMessages((current) => current.map((message) => (
        message.id === pendingMessage.id
          ? { id: message.id, role: "agent", text, error: true }
          : message
      )));
      setConnectionState("error");
      setConnectionLabel(`${providerLabel} · 连接异常`);
      setThreads((current) => current.map((thread) => thread.id === threadId ? {
        ...thread,
        title: thread.message_count === 0 ? `${trimmed.slice(0, 24)}${trimmed.length > 24 ? "…" : ""}` : thread.title,
        updated_at: new Date().toISOString(),
        message_count: thread.message_count + 1,
      } : thread).sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at)));
    } finally {
      setIsSending(false);
    }
  }, [activeThreadId, createThread, isSending, routeSettings]);

  const todayThreads = threads.filter((thread) => new Date(thread.updated_at).toDateString() === new Date().toDateString());
  const recentThreads = threads.filter((thread) => new Date(thread.updated_at).toDateString() !== new Date().toDateString());
  const formatThreadTime = (value: string) => {
    const date = new Date(value);
    if (date.toDateString() === new Date().toDateString()) {
      return new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false }).format(date);
    }
    return new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric" }).format(date);
  };
  const selectedRouteProfile = routeSettings?.profiles.find((profile) => profile.id === routeProfileId);
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void sendPrompt(input);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendPrompt(input);
    }
  };

  return (
    <div className="agent-workspace">
      <aside className="agent-workspace-history" aria-label="个人任务历史">
        <button className="agent-new-chat" onClick={() => void createThread()} disabled={isSending}>
          <span aria-hidden="true">＋</span>新建个人任务
        </button>
        <div className="agent-history-list">
          {isLoadingHistory && <p className="agent-history-loading">正在恢复个人任务…</p>}
          {!isLoadingHistory && threads.length === 0 && <p className="agent-history-empty">还没有个人任务<br />新建后，对话会自动保存</p>}
          {todayThreads.length > 0 && <div className="agent-history-section">
            <span>今天</span>
            {todayThreads.map((thread) => <button key={thread.id} className={thread.id === activeThreadId ? "is-active" : ""} onClick={() => void openThread(thread.id)} disabled={isSending}>
              <strong>{thread.title}</strong><small>{formatThreadTime(thread.updated_at)}</small>
            </button>)}
          </div>}
          {recentThreads.length > 0 && <div className="agent-history-section">
            <span>最近</span>
            {recentThreads.map((thread) => <button key={thread.id} className={thread.id === activeThreadId ? "is-active" : ""} onClick={() => void openThread(thread.id)} disabled={isSending}>
              <strong>{thread.title}</strong><small>{formatThreadTime(thread.updated_at)}</small>
            </button>)}
          </div>}
        </div>
        <div className="agent-history-footer">
          <span aria-hidden="true">✓</span>
          <p><strong>个人空间</strong><small>对话默认仅你和个人 Agent 可见</small></p>
        </div>
      </aside>

      <section className="agent-chat" aria-label="与个人 Agent 对话">
        <header className="agent-chat-header">
          <div className="agent-chat-identity">
            <span className="agent-chat-avatar" aria-hidden="true">CA</span>
            <span><strong>{user?.display_name ?? "同学"}的个人 Agent</strong><small className={`is-${connectionState}`}><i aria-hidden="true" />{connectionLabel}</small></span>
          </div>
          <nav className="agent-workspace-tabs" aria-label="个人工作台视图">
            <span aria-current="page">工作台</span>
            <Link href="/workspace/tasks">Agent 任务</Link>
          </nav>
          <div className="agent-chat-controls">
            <button aria-label="打开 Agent 设置" onClick={() => void openAgentSettings()}>Agent 设置</button>
            <button aria-label="更多对话选项">•••</button>
          </div>
        </header>

        <div ref={chatScrollRef} className="agent-chat-scroll" aria-live="polite" aria-busy={isSending}>
          <div className="agent-chat-intro">
            <span className="agent-intro-mark" aria-hidden="true">CA</span>
            <span className="agent-intro-kicker">你的个人工作站</span>
            <h1>{user?.display_name ?? "同学"}，今天想先完成什么？</h1>
            <p>直接说出你的问题或目标，Agent 会帮你理解、整理和规划；需要执行的事务可交给 Agent 任务。</p>
          </div>

          <div className="agent-workbench-section-head"><div><span>ASK AGENT</span><strong>你也可以这样问</strong></div><small>问答不会自动提交校园事务</small></div>
          <div className="agent-quick-prompts" aria-label="常用提问示例">
            {QUICK_PROMPTS.map((item) => (
              <button key={item.title} type="button" onClick={() => void sendPrompt(item.prompt)} disabled={isSending}>
                <span aria-hidden="true">{item.icon}</span>
                <div><strong>{item.title}</strong><small>{item.detail}</small></div>
                <i aria-hidden="true">↗</i>
              </button>
            ))}
          </div>

          <div className="agent-message-list">
            {messages.map((message) => (
              <article key={message.id} className={`agent-message is-${message.role}${message.pending ? " is-pending" : ""}${message.error ? " is-error" : ""}`}>
                <span className="agent-message-avatar" aria-hidden="true">{message.role === "agent" ? "CA" : (user?.display_name ?? "我").slice(0, 1)}</span>
                <div className="agent-message-content">
                  <strong>{message.role === "agent" ? "个人 Agent" : "你"}</strong>
                  <p>{message.text}</p>
                  {message.action && (
                    <div className="agent-action-card">
                      <span>{message.action.eyebrow}</span>
                      <strong>{message.action.title}</strong>
                      <p>{message.action.detail}</p>
                      <Link href={message.action.href}>{message.action.label}<i aria-hidden="true">→</i></Link>
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="agent-composer-wrap">
          <form className="agent-composer" onSubmit={handleSubmit}>
            <textarea
              aria-label="向个人 Agent 输入任务"
              placeholder="询问课程、通知、校园事务，或安排 Agent 完成任务…"
              rows={1}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isSending}
            />
            <div className="agent-composer-tools">
              <div>
                <button type="button" aria-label="添加附件">＋</button>
                <span><i aria-hidden="true" />仅个人 Agent</span>
              </div>
              <button type="submit" className="agent-send-button" disabled={!input.trim() || isSending} aria-label="发送任务">{isSending ? "···" : "↑"}</button>
            </div>
          </form>
          <p>对话文本将发送给当前选定的模型服务；请勿输入心理健康、证件、财务等敏感信息。重要操作仍需你最终确认。</p>
        </div>
      </section>

      {showAgentSettings && typeof document !== "undefined" && createPortal((
        <div className="agent-settings-backdrop" role="presentation" onMouseDown={() => !routeBusy && setShowAgentSettings(false)}>
          <section className="agent-settings-dialog" role="dialog" aria-modal="true" aria-labelledby="agent-settings-title" onMouseDown={(event) => event.stopPropagation()}>
            <header>
              <div><span>PERSONAL AGENT</span><h2 id="agent-settings-title">Agent 设置</h2><p>为当前个人 Agent 选择模型路由</p></div>
              <button type="button" aria-label="关闭 Agent 设置" onClick={() => setShowAgentSettings(false)} disabled={routeBusy}>×</button>
            </header>
            <form onSubmit={handleRouteSave}>
              <fieldset disabled={routeBusy}>
                <legend>路由方式</legend>
                <div className="agent-route-options">
                  <button type="button" className={routeMode === "PLATFORM" ? "is-selected" : ""} onClick={() => setRouteMode("PLATFORM")}>
                    <span aria-hidden="true">校</span><div><strong>平台默认</strong><small>使用 CampusAgent 统一配置</small></div><i>{routeMode === "PLATFORM" ? "✓" : ""}</i>
                  </button>
                  <button type="button" className={routeMode === "PERSONAL" ? "is-selected" : ""} onClick={() => setRouteMode("PERSONAL")}>
                    <span aria-hidden="true">AI</span><div><strong>个人路由</strong><small>OpenAI、DeepSeek 或自定义服务</small></div><i>{routeMode === "PERSONAL" ? "✓" : ""}</i>
                  </button>
                </div>
              </fieldset>

              {routeMode === "PLATFORM" ? (
                <div className="agent-platform-route-summary"><span>校</span><p><strong>{routeSettings?.model ?? "平台默认模型"}</strong><small>API 地址和密钥由 CampusAgent 统一管理</small></p></div>
              ) : (
                <div className="agent-route-form">
                  <label className="is-wide"><span>已保存配置</span><div className="agent-saved-route-row"><select value={routeProfileId ?? ""} onChange={(event) => selectSavedProfile(event.target.value)} disabled={routeBusy}><option value="">＋ 新建模型配置</option>{routeSettings?.profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name} · {profile.model}</option>)}</select><button type="button" onClick={() => selectSavedProfile("")} disabled={routeBusy}>＋ 新建</button></div></label>
                  <label><span>配置名称</span><input value={routeName} onChange={(event) => setRouteName(event.target.value)} placeholder="例如：我的 GPT" disabled={routeBusy} autoComplete="off" /></label>
                  <label><span>模型服务</span><select value={routeProvider} onChange={(event) => selectProvider(event.target.value as ModelProvider)} disabled={routeBusy}>{Object.entries(MODEL_PROVIDER_PRESETS).map(([value, preset]) => <option key={value} value={value}>{preset.label}</option>)}</select></label>
                  <label className="is-wide"><span>模型标识</span><input value={routeModel} onChange={(event) => setRouteModel(event.target.value)} placeholder="gpt-5.6-sol / deepseek-v4-flash" disabled={routeBusy} autoComplete="off" />{modelIdHint(routeProvider, routeModel) && <small className="agent-model-id-hint">{modelIdHint(routeProvider, routeModel)}</small>}</label>
                  <label className="is-wide"><span>API 地址</span><input value={routeBaseUrl} onChange={(event) => setRouteBaseUrl(event.target.value)} placeholder="https://api.example.com/v1" disabled={routeBusy} inputMode="url" autoComplete="url" /></label>
                  <label className="is-wide"><span>API 密钥 {selectedRouteProfile?.has_api_key && <em>已安全保存</em>}</span><input type="password" value={routeApiKey} onChange={(event) => setRouteApiKey(event.target.value)} placeholder={selectedRouteProfile?.has_api_key ? "留空表示继续使用已保存密钥" : "输入该服务的 API Key"} disabled={routeBusy} autoComplete="new-password" /></label>
                </div>
              )}

              <div className="agent-route-security"><span aria-hidden="true">✓</span><p><strong>只属于你的路由配置</strong><small>密钥加密保存，页面不会再显示明文；教师和管理员不能读取。</small></p></div>
              {routeMessage && <p className={`agent-route-message is-${routeMessage.type}`} role="status">{routeMessage.text}</p>}
              <footer>
                <button type="button" onClick={() => void handleRouteTest()} disabled={routeBusy}>测试连接</button>
                {routeMode === "PERSONAL" && routeProfileId && <button type="button" className="is-danger" onClick={() => void handleDeleteRouteProfile()} disabled={routeBusy}>删除配置</button>}
                <span />
                <button type="button" onClick={() => setShowAgentSettings(false)} disabled={routeBusy}>取消</button>
                <button type="submit" disabled={routeBusy || !routeModel.trim()}>{routeBusy ? "正在处理…" : "保存设置"}</button>
              </footer>
            </form>
          </section>
        </div>
      ), document.body)}
    </div>
  );
}

export default function WorkspacePage() {
  return <AppShell requireAuth><WorkspaceContent /></AppShell>;
}

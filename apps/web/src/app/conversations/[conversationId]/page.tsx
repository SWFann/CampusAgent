"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getConversation,
  listMessages,
  listParticipants,
  sendMessage as apiSendMessage,
  deleteMessage,
  type Conversation,
  type Message,
  type Participant,
} from "@/lib/conversations";
import {
  getRealtimeClient,
  useRealtimeState,
  type ServerEvent,
  type RealtimeClient,
} from "@/lib/realtime";
import { listMessages as fetchBackfill } from "@/lib/conversations";
import {
  getDormDinnerChatStatus,
  canActOnDormDinner,
  isDormDinnerClosed,
  setDormDinnerParticipation,
  startDormDinnerChat,
  startDormDinnerDebate,
  submitDormDinnerPreferences,
  voteDormDinnerCandidate,
  closeDormDinnerVote,
  endDormDinner,
  requestNextDormDinnerNegotiation,
  type DormDinnerChatStatus,
} from "@/lib/dormDinnerChat";
import { formatDate } from "@/lib/utils";

// ---------------------------------------------------------------------------
// WebSocket status indicator
// ---------------------------------------------------------------------------

function WsStatusIndicator() {
  const { state, failCount, retry } = useRealtimeState();

  const statusConfig: Record<string, { color: string; label: string }> = {
    IDLE: { color: "#9ca3af", label: "未连接" },
    CONNECTING: { color: "#f59e0b", label: "连接中..." },
    OPEN: { color: "#10b981", label: "已连接" },
    RECONNECTING: { color: "#f59e0b", label: `重连中 (${failCount})` },
    REFRESHING: { color: "#3b82f6", label: "刷新令牌中..." },
    PAUSED: { color: "#ef4444", label: "已暂停" },
    CLOSED: { color: "#6b7280", label: "已关闭" },
    AUTH_FAILED: { color: "#ef4444", label: "认证失败" },
    FORBIDDEN: { color: "#ef4444", label: "连接被拒" },
  };

  const config = statusConfig[state] ?? statusConfig.IDLE;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: config.color,
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      <span style={{ fontSize: 12, color: "#666" }}>{config.label}</span>
      {(state === "PAUSED" || state === "CLOSED" || state === "AUTH_FAILED" || state === "FORBIDDEN") && (
        <button
          onClick={retry}
          style={{
            fontSize: 12,
            padding: "2px 8px",
            cursor: "pointer",
            border: "1px solid #d1d5db",
            borderRadius: 4,
            background: "#fff",
            color: "#374151",
          }}
        >
          重试
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Scene card placeholder
// ---------------------------------------------------------------------------

function SceneCardPlaceholder({ content, onOpen }: { content: string | null; onOpen: () => void }) {
  return (
    <div
      style={{
        padding: 12,
        margin: "8px 0",
        border: "1px solid #c4b5fd",
        borderRadius: 8,
        background: "#f5f3ff",
      }}
    >
      <span style={{ fontSize: 14, color: "#5b21b6", fontWeight: 600 }}>
        宿舍聚餐协商
      </span>
      <p style={{ fontSize: 12, color: "#6d28d9", margin: "4px 0 0 0" }}>
        {content ?? "群聊场景状态已更新"}
      </p>
      <button className="btn btn-sm" onClick={onOpen} style={{ marginTop: 8 }}>打开投票</button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------

function MessageBubble({
  message,
  currentUserId,
  senderName,
  onOpenDinner,
}: {
  message: Message;
  currentUserId: string | null;
  senderName: string | null;
  onOpenDinner: () => void;
}) {
  const isSelf = message.sender_user_id === currentUserId;
  const isDeleted = message.status === "DELETED";
  const isSystem = message.sender_type === "SYSTEM";
  const isSceneCard = message.message_type === "SCENE_CARD";

  if (isSceneCard) {
    return <SceneCardPlaceholder content={message.content} onOpen={onOpenDinner} />;
  }

  if (isSystem) {
    return (
      <div style={{ textAlign: "center", margin: "8px 0" }}>
        <span
          style={{
            fontSize: 12,
            color: "#6b7280",
            background: "#f3f4f6",
            padding: "4px 12px",
            borderRadius: 12,
          }}
        >
          {message.content ?? "[系统消息]"}
        </span>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isSelf ? "flex-end" : "flex-start",
        marginBottom: 8,
      }}
    >
      <div
        style={{
          maxWidth: "70%",
          padding: "8px 12px",
          borderRadius: 8,
          background: isSelf ? "#3b82f6" : "#f3f4f6",
          color: isSelf ? "#fff" : "#1f2937",
        }}
      >
        {!isSelf && (
          <div style={{ fontSize: 11, marginBottom: 2, color: "#6b7280", fontWeight: 500 }}>
            {senderName ?? "未知成员"}
          </div>
        )}
        <div style={{ wordBreak: "break-word", fontSize: 14 }}>
          {isDeleted ? (
            <span style={{ fontStyle: "italic", opacity: 0.6 }}>此消息已被删除</span>
          ) : (
            message.content ?? ""
          )}
        </div>
        <div
          style={{
            fontSize: 10,
            marginTop: 2,
            opacity: 0.6,
            textAlign: isSelf ? "right" : "left",
          }}
        >
          {formatDate(message.created_at)}
        </div>
      </div>
    </div>
  );
}

function DormDinnerChatCard({
  status,
  maxRounds,
  setMaxRounds,
  onStart,
  onParticipate,
  onSubmitPreferences,
  onStartDebate,
  onVote,
  onRequestNext,
  actionLoading,
  actionError,
}: {
  status: DormDinnerChatStatus | null;
  maxRounds: number;
  setMaxRounds: (value: number) => void;
  onStart: (input: { city: string; origin: string; topic: string }) => void;
  onParticipate: (participate: boolean) => void;
  onSubmitPreferences: (preferences: Record<string, unknown>) => void;
  onStartDebate: () => void;
  onVote: (candidateKey: string) => void;
  onRequestNext: () => void;
  actionLoading: boolean;
  actionError: string | null;
}) {
  const sceneIsActive = canActOnDormDinner(status);
  const sceneIsClosed = isDormDinnerClosed(status);
  const [budgetRange, setBudgetRange] = useState("30-60");
  const [preferredTime, setPreferredTime] = useState("18:00");
  const [city, setCity] = useState("");
  const [origin, setOrigin] = useState("");
  const [topic, setTopic] = useState("宿舍聚餐");
  const [notes, setNotes] = useState("");
  const [dietaryRestrictions, setDietaryRestrictions] = useState<string[]>(["无"]);
  const dietaryOptions = ["无", "素食", "清真", "不吃辣"];
  const toggleDietary = (option: string) => {
    setDietaryRestrictions((current) => {
      if (option === "无") return ["无"];
      const withoutNone = current.filter((item) => item !== "无");
      if (withoutNone.includes(option)) {
        const next = withoutNone.filter((item) => item !== option);
        return next.length > 0 ? next : ["无"];
      }
      return [...withoutNone, option];
    });
  };
  return (
    <section style={{ border: "1px solid #c4b5fd", background: "#f5f3ff", borderRadius: 10, padding: 12, marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 16, color: "#5b21b6" }}>宿舍聚餐协商</h2>
          <p style={{ margin: "4px 0 0", fontSize: 12, color: "#6d28d9" }}>
            群聊内发起，私密偏好仅本人可见，群里只展示进度、公开辩论和候选结果。
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <label style={{ fontSize: 12, color: "#4c1d95" }}>
            最大轮数
            <input
              type="number"
              min={1}
              max={10}
              value={maxRounds}
              onChange={(e) => setMaxRounds(Number(e.target.value))}
              style={{ width: 56, marginLeft: 6, padding: 4, border: "1px solid #c4b5fd", borderRadius: 4 }}
            />
          </label>
          <button className="btn btn-sm btn-primary" onClick={() => onStart({ city, origin, topic })} disabled={actionLoading || sceneIsActive || !city.trim() || !origin.trim()}>
            {sceneIsActive ? "进行中" : "发起新投票"}
          </button>
        </div>
      </div>

      {status && (
        <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
          {!sceneIsActive && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 8 }}>
              <label>城市<input aria-label="城市" value={city} onChange={(e) => setCity(e.target.value)} /></label>
              <label>校区/出发地点<input aria-label="校区/出发地点" value={origin} onChange={(e) => setOrigin(e.target.value)} /></label>
              <label>聚餐主题<input aria-label="聚餐主题" value={topic} onChange={(e) => setTopic(e.target.value)} /></label>
            </div>
          )}
          {sceneIsClosed && (
            <p style={{ margin: 0, fontSize: 12, color: "#6b21a8" }}>
              上一轮投票已关闭，可以填写地点后发起新的宿舍聚餐投票。
            </p>
          )}

          {sceneIsActive && (
            <>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", fontSize: 12 }}>
                <span>阶段：{status.phase}</span>
                <span>参与：{status.joined_count}</span>
                <span>不参与：{status.skipped_count}</span>
                <span>已提交：{status.submitted_count}/{status.joined_count}</span>
                <span>辩论轮数：{status.current_round}/{status.max_rounds}</span>
              </div>

              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button className="btn btn-sm" onClick={() => onParticipate(true)} disabled={actionLoading}>
                  我参与
                </button>
                <button className="btn btn-sm" onClick={() => onParticipate(false)} disabled={actionLoading}>
                  我不参与
                </button>
                <button className="btn btn-sm btn-primary" onClick={onStartDebate} disabled={actionLoading || !status.ready_for_debate}>
                  开始智能体辩论
                </button>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8, padding: 8, background: "#fff", borderRadius: 6 }}>
                <label style={{ fontSize: 12, color: "#4c1d95" }}>
                  预算
                  <select
                    value={budgetRange}
                    onChange={(e) => setBudgetRange(e.target.value)}
                    style={{ display: "block", width: "100%", marginTop: 4, padding: 6, border: "1px solid #ddd6fe", borderRadius: 4 }}
                  >
                    <option value="20-40">20-40 元</option>
                    <option value="30-60">30-60 元</option>
                    <option value="60-100">60-100 元</option>
                  </select>
                </label>
                <label style={{ fontSize: 12, color: "#4c1d95" }}>
                  时间
                  <select
                    value={preferredTime}
                    onChange={(e) => setPreferredTime(e.target.value)}
                    style={{ display: "block", width: "100%", marginTop: 4, padding: 6, border: "1px solid #ddd6fe", borderRadius: 4 }}
                  >
                    <option value="17:00">17:00</option>
                    <option value="18:00">18:00</option>
                    <option value="19:00">19:00</option>
                    <option value="20:00">20:00</option>
                  </select>
                </label>
                <div style={{ fontSize: 12, color: "#4c1d95" }}>
                  饮食限制
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                    {dietaryOptions.map((option) => (
                      <label key={option} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <input
                          type="checkbox"
                          checked={dietaryRestrictions.includes(option)}
                          onChange={() => toggleDietary(option)}
                        />
                        {option}
                      </label>
                    ))}
                  </div>
                </div>
                <button
                  className="btn btn-sm btn-primary"
                  onClick={() => onSubmitPreferences({
                    budget_range: budgetRange,
                    dietary_restrictions: dietaryRestrictions,
                    preferred_time: preferredTime,
                    notes,
                  })}
                  disabled={actionLoading || status.my_participation === "DECLINED"}
                  style={{ alignSelf: "end" }}
                >
                  提交我的偏好
                </button>
                <label style={{ gridColumn: "1 / -1", fontSize: 12, color: "#4c1d95" }}>
                  补充需求（仅本人和智能体可见）
                  <textarea value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={1000} style={{ display: "block", width: "100%" }} />
                </label>
              </div>

              {status.debate_turns.length > 0 && (
                <div style={{ display: "grid", gap: 4 }}>
                  {status.debate_turns.map((turn) => (
                    <p key={turn.round} style={{ margin: 0, fontSize: 12, color: "#4c1d95" }}>
                      {turn.speaker}：{turn.content}
                    </p>
                  ))}
                </div>
              )}

              {status.candidates.length > 0 && (
                <div style={{ display: "grid", gap: 6 }}>
                  {status.candidates.map((candidate) => (
                    <div key={candidate.candidate_key} style={{ display: "flex", justifyContent: "space-between", gap: 8, padding: 8, background: "#fff", borderRadius: 6 }}>
                      <div>
                        <strong>{candidate.display_name}</strong>
                        <p style={{ margin: "2px 0 0", fontSize: 12, color: "#6b7280" }}>{candidate.public_reason}</p>
                        <p style={{ margin: "2px 0", fontSize: 11 }}>{candidate.public_metadata?.address ?? "地址未核实"} · {candidate.public_metadata?.price_hint ?? "价格未核实"}</p>
                        {(candidate.public_metadata?.sources ?? []).map((source) => (
                          <a key={source.url} href={source.url} target="_blank" rel="noreferrer" style={{ display: "block", fontSize: 11 }}>{source.title}</a>
                        ))}
                        <small>信息可能变化，请到店前确认</small>
                      </div>
                      <button className="btn btn-sm" onClick={() => onVote(candidate.candidate_key)} disabled={actionLoading}>
                        投票
                      </button>
                    </div>
                  ))}
                </div>
              )}
              {status.candidates.length > 0 && (
                <button className="btn btn-sm" onClick={onRequestNext} disabled={actionLoading}>
                  都不同意，请求下一次协商（已有 {status.next_negotiation_requests} 人）
                </button>
              )}
            </>
          )}
          {!sceneIsActive && !sceneIsClosed && (
            <div style={{ padding: 8, background: "#fff", borderRadius: 6, fontSize: 12, color: "#6b21a8" }}>
              <span>填写城市和校区/出发地点后，即可在群聊里发起一条新的聚餐投票卡片。</span>
            </div>
          )}
          {actionError && <p style={{ color: "#b91c1c", margin: 0, fontSize: 12 }}>{actionError}</p>}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export default function ConversationDetailPage() {
  const params = useParams();
  const conversationId = params.conversationId as string;

  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [showMembers, setShowMembers] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [dormDinner, setDormDinner] = useState<DormDinnerChatStatus | null>(null);
  const [dormDinnerLoading, setDormDinnerLoading] = useState(false);
  const [dormDinnerError, setDormDinnerError] = useState<string | null>(null);
  const [maxRounds, setMaxRounds] = useState(3);
  const [showDinnerModal, setShowDinnerModal] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const processedMessageIds = useRef<Set<string>>(new Set());
  const clientRef = useRef<RealtimeClient | null>(null);

  // -----------------------------------------------------------------------
  // Data fetching
  // -----------------------------------------------------------------------

  const fetchConversation = useCallback(async () => {
    setError(null);
    try {
      const result = await getConversation(conversationId);
      if (result.success && result.data) {
        setConversation(result.data);
      } else {
        setError(result.error?.message ?? "加载会话失败");
      }
    } catch {
      setError("网络错误");
    }
  }, [conversationId]);

  const fetchMessages = useCallback(
    async (pageNum: number = 1, append: boolean = false) => {
      try {
        const result = await listMessages(conversationId, pageNum, 50);
        if (result.success && result.data) {
          const newMessages = result.data.messages;
          if (append) {
            // Prepend older messages (paginated from newest to oldest)
            setMessages((prev) => [...newMessages, ...prev]);
          } else {
            setMessages(newMessages);
            // Mark all as processed
            newMessages.forEach((m) => processedMessageIds.current.add(m.id));
          }
          setHasMore(result.data.total > pageNum * 50);
        }
      } catch {
        // Silent fail，用途：message fetch
      }
    },
    [conversationId]
  );

  const fetchParticipants = useCallback(async () => {
    try {
      const result = await listParticipants(conversationId);
      if (result.success && result.data) {
        setParticipants(result.data.participants);
      }
    } catch {
      // Silent fail
    }
  }, [conversationId]);

  const fetchDormDinner = useCallback(async () => {
    const result = await getDormDinnerChatStatus(conversationId);
    if (result.success && result.data) {
      setDormDinner(result.data);
      setMaxRounds(result.data.max_rounds || 3);
    }
  }, [conversationId]);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([
      fetchConversation(),
      fetchMessages(1, false),
      fetchParticipants(),
      fetchDormDinner(),
    ]);
    setLoading(false);
  }, [fetchConversation, fetchMessages, fetchParticipants, fetchDormDinner]);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  // Fetch current user
  useEffect(() => {
    void (async () => {
      try {
        const { getMe } = await import("@/lib/api");
        const result = await getMe();
        if (result.success && result.data) {
          setCurrentUserId(result.data.id);
        }
      } catch {
        // Silent fail
      }
    })();
  }, []);

  // -----------------------------------------------------------------------
  // WebSocket connection management
  // -----------------------------------------------------------------------

  // HTTP backfill function (§6.3)
  const backfillMessages = useCallback(
    async (convId: string) => {
      // Only backfill，用途：current conversation
      if (convId !== conversationId) return;
      try {
        const result = await fetchBackfill(convId, 1, 50);
        if (result.success && result.data) {
          const newMessages = result.data.messages;
          // Deduplicate by message_id
          const fresh = newMessages.filter(
            (m) => !processedMessageIds.current.has(m.id)
          );
          if (fresh.length > 0) {
            setMessages((prev) => {
              // Merge and deduplicate
              const existingIds = new Set(prev.map((m) => m.id));
              const toAdd = fresh.filter((m) => !existingIds.has(m.id));
              // Sort by created_at descending (newest first)
              return [...prev, ...toAdd].sort(
                (a, b) =>
                  new Date(b.created_at).getTime() -
                  new Date(a.created_at).getTime()
              );
            });
            fresh.forEach((m) => processedMessageIds.current.add(m.id));
          }
        }
      } catch {
        // Silent fail — HTTP is source of truth
      }
    },
    [conversationId]
  );

  useEffect(() => {
    const client = getRealtimeClient();
    clientRef.current = client;

    // Set backfill function
    client.setBackfillFunction(backfillMessages);

    // Connect if not already connected
    if (client.getState() === "IDLE" || client.getState() === "CLOSED") {
      client.connect();
    }

    // Subscribe to this conversation
    client.subscribe(conversationId);

    // Event handler，用途：WebSocket events
    const unsubEvents = client.onEvent((event: ServerEvent) => {
      if (event.event === "message.created") {
        const data = event.data;
        const convId = data.conversation_id as string;

        // Only handle events，用途：this conversation
        if (convId !== conversationId) return;

        void fetchMessages(1, false);
        if (["SCENE_CARD", "AGENT_PUBLIC", "VOTE", "RESULT"].includes(String(data.message_type))) {
          void fetchDormDinner();
        }
      } else if (event.event === "message.deleted") {
        const data = event.data;
        const messageId = data.message_id as string;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? { ...m, status: "DELETED", content: null, deleted_at: data.deleted_at as string }
              : m
          )
        );
      } else if (event.event === "participant.joined") {
        // Refresh participants list
        void fetchParticipants();
      } else if (event.event === "participant.left") {
        void fetchParticipants();
      } else if (event.event === "conversation.updated") {
        void fetchConversation();
      }
    });

    // Cleanup 作用于 unmount or conversation change
    return () => {
      unsubEvents();
      client.unsubscribe(conversationId);
    };
  }, [conversationId, fetchMessages, fetchParticipants, fetchConversation, fetchDormDinner, backfillMessages]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Listen，用途：browser online event to reset fail count (§6.1)
  useEffect(() => {
    const handleOnline = () => {
      const client = clientRef.current;
      if (client) client.retry();
    };
    window.addEventListener("online", handleOnline);
    return () => window.removeEventListener("online", handleOnline);
  }, []);

  // -----------------------------------------------------------------------
  // Actions
  // -----------------------------------------------------------------------

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text || sending) return;

    setSending(true);
    setSendError(null);

    // Generate idempotency key，用途：retry safety
    const idempotencyKey = `${Date.now()}-${Math.random().toString(36).slice(2)}`;

    try {
      const result = await apiSendMessage(conversationId, {
        content: text,
        message_type: "TEXT",
        idempotency_key: idempotencyKey,
      });

      if (result.success && result.data) {
        const newMsg = result.data;
        // Add to local list if not already there (WebSocket might beat us)
        if (!processedMessageIds.current.has(newMsg.id)) {
          processedMessageIds.current.add(newMsg.id);
          setMessages((prev) => {
            const updated = [...prev, newMsg];
            return updated.sort(
              (a, b) =>
                new Date(b.created_at).getTime() -
                new Date(a.created_at).getTime()
            );
          });
        }
        setInputText("");
      } else {
        setSendError(result.error?.message ?? "发送失败");
      }
    } catch {
      setSendError("网络错误");
    } finally {
      setSending(false);
    }
  };

  const handleDelete = async (messageId: string) => {
    try {
      await deleteMessage(conversationId, messageId);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId ? { ...m, status: "DELETED", content: null } : m
        )
      );
    } catch {
      // Silent fail
    }
  };

  const handleLoadMore = async () => {
    setLoadingMore(true);
    const nextPage = page + 1;
    setPage(nextPage);
    await fetchMessages(nextPage, true);
    setLoadingMore(false);
  };

  const runDormDinnerAction = async (
    action: () => Promise<{ success: boolean; data?: DormDinnerChatStatus; error?: { message: string } }>
  ) => {
    setDormDinnerLoading(true);
    setDormDinnerError(null);
    try {
      const result = await action();
      if (result.success && result.data) {
        setDormDinner(result.data);
        void fetchMessages(1, false);
      } else {
        setDormDinnerError(result.error?.message ?? "场景操作失败");
      }
    } catch {
      setDormDinnerError("网络错误");
    } finally {
      setDormDinnerLoading(false);
    }
  };

  const participantNameByUserId = new Map(
    participants
      .filter((p) => p.participant_user_id)
      .map((p) => [p.participant_user_id as string, p.display_name ?? "未知成员"])
  );

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  if (loading) {
    return (
      <main style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px" }}>
        <p>加载中...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px" }}>
        <p style={{ color: "red" }}>{error}</p>
        <Link href="/conversations" style={{ color: "#3b82f6" }}>
          ← 返回会话列表
        </Link>
      </main>
    );
  }

  if (!conversation) {
    return (
      <main style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px" }}>
        <p>会话不存在</p>
        <Link href="/conversations" style={{ color: "#3b82f6" }}>
          ← 返回会话列表
        </Link>
      </main>
    );
  }

  const getTypeLabel = (type: string): string => {
    switch (type) {
      case "PRIVATE": return "私聊";
      case "GROUP": return "群聊";
      case "ORG_GROUP": return "组织群聊";
      case "SCENE": return "场景";
      default: return type;
    }
  };

  return (
    <main
      style={{
        maxWidth: 960,
        margin: "0 auto",
        padding: "24px 16px",
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 48px)",
        boxSizing: "border-box",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
          paddingBottom: 12,
          borderBottom: "1px solid #e5e7eb",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link href="/conversations" style={{ color: "#3b82f6", textDecoration: "none" }}>
            ←
          </Link>
          <h1 style={{ margin: 0, fontSize: 18 }}>
            {conversation.title || getTypeLabel(conversation.type)}
          </h1>
          <span style={{ fontSize: 12, color: "#9ca3af" }}>
            {getTypeLabel(conversation.type)}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <WsStatusIndicator />
          <button
            onClick={() => setShowMembers(!showMembers)}
            style={{
              padding: "4px 10px",
              fontSize: 12,
              cursor: "pointer",
              border: "1px solid #d1d5db",
              borderRadius: 4,
              background: "#fff",
            }}
          >
            {showMembers ? "隐藏成员" : `成员 (${participants.length})`}
          </button>
        </div>
      </div>

      {/* Main content area: messages + sidebar */}
      <div style={{ display: "flex", flex: 1, gap: 16, minHeight: 0 }}>
        {/* Message area */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
          }}
        >
          {/* Load more button */}
          {hasMore && (
            <div style={{ textAlign: "center", padding: 8 }}>
              <button
                onClick={handleLoadMore}
                disabled={loadingMore}
                style={{
                  padding: "4px 12px",
                  fontSize: 12,
                  cursor: "pointer",
                  border: "1px solid #d1d5db",
                  borderRadius: 4,
                  background: "#fff",
                }}
              >
                {loadingMore ? "加载中..." : "加载更多消息"}
              </button>
            </div>
          )}

          {/* Message list */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "8px 0",
              display: "flex",
              flexDirection: "column-reverse",
            }}
          >
            {messages.length === 0 ? (
              <p style={{ color: "#9ca3af", textAlign: "center", padding: 24 }}>
                还没有消息，发送第一条消息吧！
              </p>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  onClick={() => {
                    if (msg.sender_user_id === currentUserId && msg.status === "ACTIVE") {
                      if (confirm("确认删除这条消息？")) void handleDelete(msg.id);
                    }
                  }}
                  style={{ cursor: msg.sender_user_id === currentUserId && msg.status === "ACTIVE" ? "pointer" : "default" }}
                >
                  <MessageBubble
                    message={msg}
                    currentUserId={currentUserId}
                    senderName={
                      msg.sender_user_id
                        ? participantNameByUserId.get(msg.sender_user_id) ?? null
                        : null
                    }
                    onOpenDinner={() => setShowDinnerModal(true)}
                  />
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <form
            onSubmit={handleSend}
            style={{
              display: "flex",
              gap: 8,
              padding: "12px 0",
              borderTop: "1px solid #e5e7eb",
            }}
          >
            {(conversation.type === "GROUP" || conversation.type === "ORG_GROUP") && (
              <button type="button" className="btn btn-sm" onClick={() => setShowDinnerModal(true)}>宿舍聚餐</button>
            )}
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="输入消息..."
              maxLength={5000}
              style={{
                flex: 1,
                padding: "8px 12px",
                borderRadius: 6,
                border: "1px solid #d1d5db",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
            <button
              type="submit"
              disabled={sending || !inputText.trim()}
              style={{
                padding: "8px 20px",
                cursor: "pointer",
                borderRadius: 6,
                border: "none",
                background: sending || !inputText.trim() ? "#9ca3af" : "#3b82f6",
                color: "#fff",
              }}
            >
              {sending ? "发送中..." : "发送"}
            </button>
          </form>
          {sendError && (
            <p style={{ color: "red", fontSize: 12, margin: 0 }}>{sendError}</p>
          )}
        </div>

        {/* Members sidebar */}
        {showMembers && (
          <div
            style={{
              width: 200,
              borderLeft: "1px solid #e5e7eb",
              paddingLeft: 16,
              overflowY: "auto",
              flexShrink: 0,
            }}
          >
            <h2 style={{ fontSize: 14, marginBottom: 8, color: "#374151" }}>
              成员 ({participants.length})
            </h2>
            {participants.length === 0 ? (
              <p style={{ color: "#9ca3af", fontSize: 12 }}>暂无成员</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {participants.map((p) => (
                  <div
                    key={p.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "4px 0",
                    }}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: p.status === "ACTIVE" ? "#10b981" : "#9ca3af",
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {p.display_name ?? (p.participant_user_id ?? "未知").slice(0, 8)}
                    </span>
                    <span style={{ fontSize: 10, color: "#9ca3af", whiteSpace: "nowrap" }}>
                      {p.role}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      {showDinnerModal && (
        <div role="dialog" aria-modal="true" aria-label="宿舍聚餐投票" style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,.48)", display: "grid", placeItems: "center", zIndex: 50, padding: 16 }}>
          <div style={{ width: "min(900px, 96vw)", maxHeight: "90vh", overflow: "auto", background: "white", borderRadius: 12, padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <strong>宿舍聚餐投票</strong>
              <button type="button" onClick={() => setShowDinnerModal(false)}>关闭窗口</button>
            </div>
            <DormDinnerChatCard
              status={dormDinner}
              maxRounds={maxRounds}
              setMaxRounds={setMaxRounds}
              actionLoading={dormDinnerLoading}
              actionError={dormDinnerError ?? dormDinner?.public_error ?? null}
              onStart={({ city, origin, topic }) => void runDormDinnerAction(() => startDormDinnerChat(conversationId, { maxRounds, city, origin, topic }))}
              onParticipate={(participate) => void runDormDinnerAction(() => setDormDinnerParticipation(conversationId, participate))}
              onSubmitPreferences={(preferences) => void runDormDinnerAction(() => submitDormDinnerPreferences(conversationId, preferences))}
              onStartDebate={() => void runDormDinnerAction(() => startDormDinnerDebate(conversationId, maxRounds))}
              onVote={(candidateKey) => void runDormDinnerAction(() => voteDormDinnerCandidate(conversationId, candidateKey))}
              onRequestNext={() => void runDormDinnerAction(() => requestNextDormDinnerNegotiation(conversationId))}
            />
            {dormDinner?.capabilities.can_manage && dormDinner.scene_id && (
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <button type="button" onClick={() => void runDormDinnerAction(() => closeDormDinnerVote(conversationId))}>关闭投票</button>
                <button type="button" onClick={() => void runDormDinnerAction(() => endDormDinner(conversationId))}>结束聚餐</button>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}

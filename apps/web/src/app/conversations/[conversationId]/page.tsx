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

function SceneCardPlaceholder() {
  return (
    <div
      style={{
        padding: 12,
        margin: "8px 0",
        border: "1px dashed #8b5cf6",
        borderRadius: 8,
        background: "#f5f3ff",
        textAlign: "center",
      }}
    >
      <span style={{ fontSize: 14, color: "#7c3aed", fontWeight: 500 }}>
        🎬 场景卡片占位
      </span>
      <p style={{ fontSize: 12, color: "#9ca3af", margin: "4px 0 0 0" }}>
        场景执行将在后续阶段实现
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------

function MessageBubble({
  message,
  currentUserId,
}: {
  message: Message;
  currentUserId: string | null;
}) {
  const isSelf = message.sender_user_id === currentUserId;
  const isDeleted = message.status === "DELETED";
  const isSystem = message.sender_type === "SYSTEM";
  const isSceneCard = message.message_type === "SCENE_CARD";

  if (isSceneCard) {
    return <SceneCardPlaceholder />;
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
            {message.sender_user_id ? message.sender_user_id.slice(0, 8) : "未知"}
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
        // Silent fail for message fetch
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

  const fetchAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([
      fetchConversation(),
      fetchMessages(1, false),
      fetchParticipants(),
    ]);
    setLoading(false);
  }, [fetchConversation, fetchMessages, fetchParticipants]);

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
      // Only backfill for current conversation
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

    // Event handler for WebSocket events
    const unsubEvents = client.onEvent((event: ServerEvent) => {
      if (event.event === "message.created") {
        const data = event.data;
        const messageId = data.message_id as string;
        const convId = data.conversation_id as string;

        // Only handle events for this conversation
        if (convId !== conversationId) return;

        // Dedup by message_id (business idempotency)
        if (processedMessageIds.current.has(messageId)) return;
        processedMessageIds.current.add(messageId);

        const newMessage: Message = {
          id: messageId,
          conversation_id: convId,
          sender_type: data.sender_type as Message["sender_type"],
          sender_user_id: (data.sender_user_id as string) ?? null,
          sender_agent_id: (data.sender_agent_id as string) ?? null,
          message_type: data.message_type as Message["message_type"],
          content: (data.content as string) ?? null,
          status: "ACTIVE",
          sequence: 0,
          created_at: data.created_at as string,
          deleted_at: null,
        };

        setMessages((prev) => {
          // Insert and sort by created_at
          const updated = [...prev, newMessage];
          return updated.sort(
            (a, b) =>
              new Date(b.created_at).getTime() -
              new Date(a.created_at).getTime()
          );
        });
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

    // Cleanup on unmount or conversation change
    return () => {
      unsubEvents();
      client.unsubscribe(conversationId);
    };
  }, [conversationId, fetchParticipants, fetchConversation, backfillMessages]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Listen for browser online event to reset fail count (§6.1)
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

    // Generate idempotency key for retry safety
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
        {/* Messages area */}
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
                  <MessageBubble message={msg} currentUserId={currentUserId} />
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
              {sending ? "..." : "发送"}
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
    </main>
  );
}

"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/app/AppShell";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { OfflineState } from "@/components/ui/OfflineState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiGet, apiPost, isApiError } from "@/lib/api/client";
import { useAsync } from "@/lib/useAsync";
import type { ConversationSummary } from "@/lib/api/types";

interface Message {
  id: string;
  sender_id: string;
  sender_name: string;
  content_preview: string;
  created_at: string;
  status: "sent" | "pending" | "failed";
}

function MessagesContent() {
  const [selectedConv, setSelectedConv] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [msgLoading, setMsgLoading] = useState(false);
  const [msgError, setMsgError] = useState<string | null>(null);
  const [inputText, setInputText] = useState("");
  const [online, setOnline] = useState(true);
  const [reconnecting, setReconnecting] = useState(false);

  const { data: conversations, loading, error } = useAsync<ConversationSummary[]>(
    async () => apiGet("/conversations"),
    [],
  );

  // Monitor online status
  useEffect(() => {
    const handleOffline = () => setOnline(false);
    const handleOnline = () => {
      setReconnecting(true);
      setOnline(true);
      setTimeout(() => setReconnecting(false), 2000);
    };
    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);
    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
    };
  }, []);

  const loadMessages = useCallback(async (convId: string) => {
    setMsgLoading(true);
    setMsgError(null);
    try {
      const data = await apiGet<Message[]>(`/conversations/${convId}/messages`, { limit: "50" });
      setMessages(data);
    } catch (err) {
      setMsgError(isApiError(err) ? err.message : "Failed to load messages");
    } finally {
      setMsgLoading(false);
    }
  }, []);

  const handleSend = async () => {
    if (!inputText.trim() || !selectedConv) return;

    const tempId = `temp-${Date.now()}`;
    const optimisticMsg: Message = {
      id: tempId,
      sender_id: "me",
      sender_name: "You",
      content_preview: inputText,
      created_at: new Date().toISOString(),
      status: "pending",
    };
    setMessages((prev) => [...prev, optimisticMsg]);
    const sentText = inputText;
    setInputText("");

    try {
      await apiPost(`/conversations/${selectedConv}/messages`, { content: sentText });
      setMessages((prev) =>
        prev.map((m) => (m.id === tempId ? { ...m, status: "sent" as const } : m)),
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) => (m.id === tempId ? { ...m, status: "failed" as const } : m)),
      );
    }
  };

  const handleRetry = async (msgId: string) => {
    const msg = messages.find((m) => m.id === msgId);
    if (!msg || !selectedConv) return;
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, status: "pending" as const } : m)),
    );
    try {
      await apiPost(`/conversations/${selectedConv}/messages`, { content: msg.content_preview });
      setMessages((prev) =>
        prev.map((m) => (m.id === msgId ? { ...m, status: "sent" as const } : m)),
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) => (m.id === msgId ? { ...m, status: "failed" as const } : m)),
      );
    }
  };

  return (
    <div style={{ display: "flex", height: "calc(100vh - 100px)", gap: "var(--space-md)" }}>
      {/* Left: conversation list */}
      <div className="card" style={{ width: 280, overflow: "auto", padding: "var(--space-sm)" }}>
        <h2 style={{ fontSize: "var(--font-size-sm)", padding: "var(--space-xs) var(--space-sm)", color: "var(--color-text-secondary)" }}>
          Conversations
        </h2>
        {loading && <LoadingState message="Loading..." />}
        {error && <ErrorState message="Failed to load conversations." />}
        {conversations && conversations.length === 0 && (
          <EmptyState title="No conversations" />
        )}
        {conversations && conversations.map((conv) => (
          <button
            key={conv.id}
            onClick={() => {
              setSelectedConv(conv.id);
              loadMessages(conv.id);
            }}
            style={{
              display: "flex",
              flexDirection: "column",
              width: "100%",
              textAlign: "left",
              padding: "var(--space-sm)",
              borderRadius: "var(--radius-md)",
              border: "none",
              background: selectedConv === conv.id ? "var(--color-primary-light)" : "transparent",
              cursor: "pointer",
              marginBottom: "var(--space-xs)",
            }}
          >
            <span style={{ fontWeight: "var(--font-weight-medium)", fontSize: "var(--font-size-sm)" }}>
              {conv.title}
            </span>
            {conv.last_message_preview && (
              <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {conv.last_message_preview}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Center: message stream */}
      <div className="card" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {!selectedConv ? (
          <EmptyState title="Select a conversation" description="Choose a conversation from the list to start messaging." />
        ) : (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "var(--space-sm)", borderBottom: "1px solid var(--color-border)" }}>
              <span style={{ fontWeight: "var(--font-weight-semibold)" }}>Messages</span>
              {!online ? (
                <StatusBadge label="Offline" variant="danger" />
              ) : reconnecting ? (
                <StatusBadge label="Reconnecting..." variant="warning" />
              ) : (
                <StatusBadge label="Connected" variant="success" />
              )}
            </div>

            {!online ? (
              <OfflineState />
            ) : msgLoading ? (
              <LoadingState message="Loading messages..." />
            ) : msgError ? (
              <ErrorState message={msgError} />
            ) : (
              <div style={{ flex: 1, overflow: "auto", padding: "var(--space-sm)" }}>
                {messages.length === 0 ? (
                  <EmptyState title="No messages" description="Send a message to start the conversation." />
                ) : (
                  messages.map((msg) => (
                    <div
                      key={msg.id}
                      style={{
                        marginBottom: "var(--space-sm)",
                        padding: "var(--space-sm)",
                        borderRadius: "var(--radius-md)",
                        background: msg.sender_id === "me" ? "var(--color-primary-light)" : "var(--color-surface-hover)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "var(--space-xs)" }}>
                        <span style={{ fontWeight: "var(--font-weight-medium)", fontSize: "var(--font-size-xs)" }}>
                          {msg.sender_name}
                        </span>
                        {msg.status === "pending" && <StatusBadge label="Sending..." variant="warning" />}
                        {msg.status === "failed" && (
                          <button onClick={() => handleRetry(msg.id)} className="btn btn-sm btn-danger">
                            Retry
                          </button>
                        )}
                      </div>
                      <p style={{ fontSize: "var(--font-size-sm)" }}>{msg.content_preview}</p>
                    </div>
                  ))
                )}
              </div>
            )}

            <div style={{ display: "flex", gap: "var(--space-sm)", padding: "var(--space-sm)", borderTop: "1px solid var(--color-border)" }}>
              <input
                className="input"
                placeholder="Type a message..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                aria-label="Message input"
                disabled={!online}
              />
              <button className="btn btn-primary" onClick={handleSend} disabled={!inputText.trim() || !online}>
                Send
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function MessagesPage() {
  return (
    <AppShell requireAuth>
      <MessagesContent />
    </AppShell>
  );
}

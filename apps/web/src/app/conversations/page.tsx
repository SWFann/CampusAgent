"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  listConversations,
  createPrivateConversation,
  createGroupConversation,
  type ConversationListItem,
} from "@/lib/conversations";
import { formatDate } from "@/lib/utils";

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createType, setCreateType] = useState<"private" | "group">("private");
  const [targetUserId, setTargetUserId] = useState("");
  const [groupTitle, setGroupTitle] = useState("");
  const [participantIds, setParticipantIds] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listConversations();
      if (result.success && result.data) {
        setConversations(result.data.conversations);
      } else {
        setError(result.error?.message ?? "加载会话列表失败");
      }
    } catch {
      setError("网络错误");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchConversations();
  }, [fetchConversations]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    setActionLoading(true);
    try {
      if (createType === "private") {
        if (!targetUserId.trim()) {
          setActionError("请输入目标用户 ID");
          setActionLoading(false);
          return;
        }
        const result = await createPrivateConversation(targetUserId.trim());
        if (result.success && result.data) {
          setShowCreate(false);
          setTargetUserId("");
          void fetchConversations();
        } else {
          setActionError(result.error?.message ?? "创建私聊失败");
        }
      } else {
        const ids = participantIds
          .split(/[\s,]+/)
          .map((s) => s.trim())
          .filter(Boolean);
        if (ids.length === 0) {
          setActionError("请至少输入一个参与者 ID");
          setActionLoading(false);
          return;
        }
        const result = await createGroupConversation({
          title: groupTitle.trim() || undefined,
          participant_user_ids: ids,
        });
        if (result.success && result.data) {
          setShowCreate(false);
          setGroupTitle("");
          setParticipantIds("");
          void fetchConversations();
        } else {
          setActionError(result.error?.message ?? "创建群聊失败");
        }
      }
    } catch {
      setActionError("网络错误");
    } finally {
      setActionLoading(false);
    }
  };

  const getTypeLabel = (type: string): string => {
    switch (type) {
      case "PRIVATE": return "私聊";
      case "GROUP": return "群聊";
      case "ORG_GROUP": return "组织群聊";
      case "SCENE": return "场景";
      default: return type;
    }
  };

  const getTypeColor = (type: string): string => {
    switch (type) {
      case "PRIVATE": return "#3b82f6";
      case "GROUP": return "#10b981";
      case "ORG_GROUP": return "#f59e0b";
      case "SCENE": return "#8b5cf6";
      default: return "#6b7280";
    }
  };

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>会话</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{ padding: "8px 16px", cursor: "pointer", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff" }}
        >
          {showCreate ? "取消" : "新建会话"}
        </button>
      </div>

      {error && <p style={{ color: "red", marginBottom: 16 }}>{error}</p>}

      {showCreate && (
        <form onSubmit={handleCreate} style={{ marginBottom: 24, padding: 16, border: "1px solid #e0e0e0", borderRadius: 8, background: "#f9fafb" }}>
          <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}>
              <input
                type="radio"
                checked={createType === "private"}
                onChange={() => setCreateType("private")}
              />
              私聊
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}>
              <input
                type="radio"
                checked={createType === "group"}
                onChange={() => setCreateType("group")}
              />
              群聊
            </label>
          </div>

          {createType === "private" ? (
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>目标用户 ID</label>
              <input
                type="text"
                value={targetUserId}
                onChange={(e) => setTargetUserId(e.target.value)}
                placeholder="粘贴用户 UUID"
                style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
              />
            </div>
          ) : (
            <>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>群聊标题（可选）</label>
                <input
                  type="text"
                  value={groupTitle}
                  onChange={(e) => setGroupTitle(e.target.value)}
                  placeholder="群聊名称"
                  style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>参与者用户 ID（逗号或空格分隔）</label>
                <input
                  type="text"
                  value={participantIds}
                  onChange={(e) => setParticipantIds(e.target.value)}
                  placeholder="uuid1, uuid2, uuid3"
                  style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
                />
              </div>
            </>
          )}

          {actionError && <p style={{ color: "red", marginBottom: 8, fontSize: 14 }}>{actionError}</p>}
          <button
            type="submit"
            disabled={actionLoading}
            style={{ padding: "8px 20px", cursor: "pointer", borderRadius: 6, border: "none", background: "#3b82f6", color: "#fff", disabled: { opacity: 0.5 } } as React.CSSProperties}
          >
            {actionLoading ? "创建中..." : "创建"}
          </button>
        </form>
      )}

      {loading ? (
        <p>加载中...</p>
      ) : conversations.length === 0 ? (
        <p style={{ color: "#666" }}>暂无会话。点击「新建会话」开始聊天。</p>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {conversations.map((conv) => (
            <Link
              key={conv.id}
              href={`/conversations/${conv.id}`}
              style={{ display: "block", padding: 12, border: "1px solid #e0e0e0", borderRadius: 6, textDecoration: "none", color: "inherit", transition: "border-color 0.2s" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span
                      style={{
                        fontSize: 12,
                        padding: "2px 8px",
                        borderRadius: 12,
                        color: "#fff",
                        background: getTypeColor(conv.type),
                        whiteSpace: "nowrap",
                      }}
                    >
                      {getTypeLabel(conv.type)}
                    </span>
                    <strong style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {conv.title || (conv.type === "PRIVATE" ? "私聊" : "群聊")}
                    </strong>
                  </div>
                  {conv.last_message_at && (
                    <span style={{ color: "#999", fontSize: 12 }}>
                      最后消息: {formatDate(conv.last_message_at)}
                    </span>
                  )}
                </div>
                <span style={{ color: "#666", fontSize: 14, whiteSpace: "nowrap", marginLeft: 8 }}>
                  {conv.participant_count} 人
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      <div style={{ marginTop: 24 }}>
        <Link href="/directory" style={{ color: "#3b82f6", fontSize: 14, textDecoration: "none" }}>
          ← 返回校园目录
        </Link>
      </div>
    </main>
  );
}

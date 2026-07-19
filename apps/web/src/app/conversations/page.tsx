"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  listConversations,
  createPrivateConversation,
  createGroupConversation,
  type ConversationListItem,
} from "@/lib/conversations";
import { listContacts, type ContactItem } from "@/lib/contacts";
import { searchDirectory, type DirectoryUserResult } from "@/lib/directory";
import { formatDate } from "@/lib/utils";

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createType, setCreateType] = useState<"private" | "group">("private");
  const [targetUserId, setTargetUserId] = useState("");
  const [contacts, setContacts] = useState<ContactItem[]>([]);
  const [groupTitle, setGroupTitle] = useState("");
  const [memberSearchQuery, setMemberSearchQuery] = useState("");
  const [memberSearchResults, setMemberSearchResults] = useState<DirectoryUserResult[]>([]);
  const [memberSearchLoading, setMemberSearchLoading] = useState(false);
  const [selectedMembers, setSelectedMembers] = useState<DirectoryUserResult[]>([]);
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

  const fetchContacts = useCallback(async () => {
    const result = await listContacts();
    if (result.success && result.data) {
      setContacts(result.data.contacts);
      const firstContactUserId = result.data.contacts[0]?.user.id || "";
      setTargetUserId((current) => current || firstContactUserId);
    }
  }, []);

  useEffect(() => {
    void fetchConversations();
    void fetchContacts();
  }, [fetchConversations, fetchContacts]);

  const handleMemberSearch = async () => {
    const query = memberSearchQuery.trim();
    setActionError(null);

    if (query.length < 2) {
      setMemberSearchResults([]);
      setActionError("请输入至少 2 个字再搜索成员");
      return;
    }

    setMemberSearchLoading(true);
    try {
      const result = await searchDirectory(query, "users", 8);
      if (result.success && result.data) {
        const selectedIds = new Set(selectedMembers.map((member) => member.id));
        setMemberSearchResults(
          result.data.users.filter((user) => !selectedIds.has(user.id))
        );
      } else {
        setActionError(result.error?.message ?? "搜索成员失败");
      }
    } catch {
      setActionError("网络错误");
    } finally {
      setMemberSearchLoading(false);
    }
  };

  const addSelectedMember = (member: DirectoryUserResult) => {
    setSelectedMembers((current) => (
      current.some((item) => item.id === member.id) ? current : [...current, member]
    ));
    setMemberSearchResults((current) => current.filter((item) => item.id !== member.id));
  };

  const removeSelectedMember = (memberId: string) => {
    setSelectedMembers((current) => current.filter((member) => member.id !== memberId));
  };

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
        if (selectedMembers.length === 0) {
          setActionError("请至少选择一位成员");
          setActionLoading(false);
          return;
        }
        const result = await createGroupConversation({
          title: groupTitle.trim() || undefined,
          participant_user_ids: selectedMembers.map((member) => member.id),
        });
        if (result.success && result.data) {
          setShowCreate(false);
          setGroupTitle("");
          setMemberSearchQuery("");
          setMemberSearchResults([]);
          setSelectedMembers([]);
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
          type="button"
          onClick={() => {
            setShowCreate(!showCreate);
            setActionError(null);
          }}
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
                onChange={() => {
                  setCreateType("private");
                  setActionError(null);
                }}
              />
              私聊
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}>
              <input
                type="radio"
                checked={createType === "group"}
                onChange={() => {
                  setCreateType("group");
                  setActionError(null);
                }}
              />
              群聊
            </label>
          </div>

          {createType === "private" ? (
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>选择好友</label>
              {contacts.length > 0 ? (
                <select
                  value={targetUserId}
                  onChange={(e) => setTargetUserId(e.target.value)}
                  style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
                >
                  {contacts.map((contact) => (
                    <option key={contact.user.id} value={contact.user.id}>
                      {contact.user.display_name}
                    </option>
                  ))}
                </select>
              ) : (
                <div style={{ display: "grid", gap: 8 }}>
                  <p style={{ color: "#666", fontSize: 14 }}>暂无好友。请先到校园目录搜索用户并发送好友申请。</p>
                  <input
                    type="text"
                    value={targetUserId}
                    onChange={(e) => setTargetUserId(e.target.value)}
                    placeholder="临时输入用户 ID"
                    style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
                  />
                </div>
              )}
            </div>
          ) : (
            <>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>群聊标题（可选）</label>
                <input
                  aria-label="群聊标题（可选）"
                  type="text"
                  value={groupTitle}
                  onChange={(e) => setGroupTitle(e.target.value)}
                  placeholder="群聊名称"
                  style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>搜索成员</label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    aria-label="搜索成员"
                    type="search"
                    value={memberSearchQuery}
                    onChange={(e) => setMemberSearchQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        void handleMemberSearch();
                      }
                    }}
                    placeholder="输入同学姓名或关键词"
                    style={{ flex: 1, padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
                  />
                  <button
                    type="button"
                    onClick={() => void handleMemberSearch()}
                    disabled={memberSearchLoading || memberSearchQuery.trim().length < 2}
                    style={{
                      padding: "8px 16px",
                      borderRadius: 6,
                      border: "1px solid #d1d5db",
                      background: memberSearchLoading || memberSearchQuery.trim().length < 2 ? "#e5e7eb" : "#fff",
                      cursor: memberSearchLoading || memberSearchQuery.trim().length < 2 ? "not-allowed" : "pointer",
                    }}
                  >
                    {memberSearchLoading ? "搜索中..." : "搜索"}
                  </button>
                </div>

                {memberSearchResults.length > 0 && (
                  <div style={{ marginTop: 8, display: "grid", gap: 6 }}>
                    {memberSearchResults.map((member) => (
                      <div
                        key={member.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: 8,
                          padding: 8,
                          border: "1px solid #e5e7eb",
                          borderRadius: 6,
                          background: "#fff",
                        }}
                      >
                        <span style={{ fontSize: 14 }}>{member.display_name}</span>
                        <button
                          type="button"
                          aria-label={`添加 ${member.display_name}`}
                          onClick={() => addSelectedMember(member)}
                          style={{ padding: "4px 10px", borderRadius: 4, border: "1px solid #3b82f6", background: "#eff6ff", color: "#1d4ed8", cursor: "pointer" }}
                        >
                          添加
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                  <label style={{ fontSize: 14, color: "#374151" }}>已选成员</label>
                  <span style={{ fontSize: 12, color: "#6b7280" }}>{selectedMembers.length} 人</span>
                </div>
                {selectedMembers.length > 0 ? (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {selectedMembers.map((member) => (
                      <span
                        key={member.id}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "4px 8px",
                          border: "1px solid #bfdbfe",
                          borderRadius: 999,
                          background: "#eff6ff",
                          color: "#1e40af",
                          fontSize: 14,
                        }}
                      >
                        {member.display_name}
                        <button
                          type="button"
                          aria-label={`移除 ${member.display_name}`}
                          onClick={() => removeSelectedMember(member.id)}
                          style={{ border: "none", background: "transparent", color: "#1d4ed8", cursor: "pointer", padding: 0 }}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                ) : (
                  <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>还没有选择成员，先搜索同学再添加。</p>
                )}
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
                      最后消息：{formatDate(conv.last_message_at)}
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

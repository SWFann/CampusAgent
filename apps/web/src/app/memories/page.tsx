"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  listMemories,
  createMemory,
  deleteMemory,
  listConsents,
  grantConsent,
  revokeConsent,
  type MemoryRead,
  type ConsentRead,
} from "@/lib/memories";
import { getMyAgent } from "@/lib/agents";
import { formatDate } from "@/lib/utils";

export default function MemoriesPage() {
  const [memories, setMemories] = useState<MemoryRead[]>([]);
  const [consents, setConsents] = useState<ConsentRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState("PREFERENCE");
  const [newExpiry, setNewExpiry] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [agentId, setAgentId] = useState<string | null>(null);
  const [showConsent, setShowConsent] = useState(false);
  const [consentPurpose, setConsentPurpose] = useState("chat_reply");
  const [consentScope, setConsentScope] = useState("");

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [memResult, consentResult, agentResult] = await Promise.all([
        listMemories(),
        listConsents(),
        getMyAgent(),
      ]);
      if (memResult.success && memResult.data) {
        setMemories(memResult.data.memories);
      } else {
        setError(memResult.error?.message ?? "加载记忆失败");
      }
      if (consentResult.success && consentResult.data) {
        setConsents(consentResult.data.consents);
      }
      if (agentResult.success && agentResult.data) {
        setAgentId(agentResult.data.id);
      }
    } catch {
      setError("网络错误");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    setActionLoading(true);
    try {
      const payload: { content: string; category: string; expires_at?: string } = {
        content: newContent,
        category: newCategory,
      };
      if (newExpiry) payload.expires_at = new Date(newExpiry).toISOString();

      const result = await createMemory(payload);
      if (result.success) {
        setShowCreate(false);
        setNewContent("");
        setNewExpiry("");
        void fetchAll();
      } else {
        setActionError(result.error?.message ?? "创建失败");
      }
    } catch {
      setActionError("网络错误");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async (memoryId: string) => {
    if (!confirm("确定删除此记忆？此操作不可撤销。")) return;
    const result = await deleteMemory(memoryId);
    if (result.success) {
      void fetchAll();
    } else {
      alert(result.error?.message ?? "删除失败");
    }
  };

  const handleGrantConsent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agentId) {
      setActionError("未找到智能体");
      return;
    }
    setActionError(null);
    setActionLoading(true);
    try {
      const payload: { agent_id: string; purpose: string; scope?: Record<string, unknown> } = {
        agent_id: agentId,
        purpose: consentPurpose,
      };
      if (consentScope.trim()) {
        const categories = consentScope.split(",").map((s) => s.trim()).filter(Boolean);
        payload.scope = { category: categories };
      }
      const result = await grantConsent(payload);
      if (result.success) {
        setShowConsent(false);
        setConsentScope("");
        void fetchAll();
      } else {
        setActionError(result.error?.message ?? "授权失败");
      }
    } catch {
      setActionError("网络错误");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRevokeConsent = async (consentId: string) => {
    if (!confirm("确定撤销此授权？撤销后立即生效。")) return;
    const result = await revokeConsent(consentId);
    if (result.success) {
      void fetchAll();
    } else {
      alert(result.error?.message ?? "撤销失败");
    }
  };

  const getCategoryColor = (cat: string): string => {
    const colors: Record<string, string> = {
      PREFERENCE: "#8b5cf6",
      FACT: "#3b82f6",
      CONTEXT: "#10b981",
      FEEDBACK: "#f59e0b",
    };
    return colors[cat] ?? "#6b7280";
  };

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "24px 16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>记忆管理</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => setShowConsent(!showConsent)}
            style={{ padding: "8px 16px", cursor: "pointer", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff" }}
          >
            {showConsent ? "取消" : "管理授权"}
          </button>
          <button
            onClick={() => setShowCreate(!showCreate)}
            style={{ padding: "8px 16px", cursor: "pointer", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff" }}
          >
            {showCreate ? "取消" : "新建记忆"}
          </button>
        </div>
      </div>

      <div style={{ marginBottom: 16, padding: 12, background: "#fef3c7", borderRadius: 6, fontSize: 14, color: "#92400e" }}>
        🔒 所有记忆内容均加密存储。仅您本人可查看明文。撤销授权后立即生效。
      </div>

      {error && <p style={{ color: "red", marginBottom: 16 }}>{error}</p>}

      {showCreate && (
        <form onSubmit={handleCreate} style={{ marginBottom: 24, padding: 16, border: "1px solid #e0e0e0", borderRadius: 8, background: "#f9fafb" }}>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>内容</label>
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              rows={3}
              required
              style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
              placeholder="输入记忆内容（将加密存储）"
            />
          </div>
          <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>类别</label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
              >
                <option value="PREFERENCE">偏好</option>
                <option value="FACT">事实</option>
                <option value="CONTEXT">上下文</option>
                <option value="FEEDBACK">反馈</option>
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>过期时间（可选）</label>
              <input
                type="datetime-local"
                value={newExpiry}
                onChange={(e) => setNewExpiry(e.target.value)}
                style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
              />
            </div>
          </div>
          {actionError && <p style={{ color: "red", marginBottom: 8, fontSize: 14 }}>{actionError}</p>}
          <button
            type="submit"
            disabled={actionLoading}
            style={{ padding: "8px 20px", cursor: "pointer", borderRadius: 6, border: "none", background: "#3b82f6", color: "#fff" }}
          >
            {actionLoading ? "创建中..." : "创建"}
          </button>
        </form>
      )}

      {showConsent && (
        <form onSubmit={handleGrantConsent} style={{ marginBottom: 24, padding: 16, border: "1px solid #e0e0e0", borderRadius: 8, background: "#f9fafb" }}>
          <h3 style={{ marginTop: 0 }}>授予智能体访问权限</h3>
          <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>用途</label>
              <select
                value={consentPurpose}
                onChange={(e) => setConsentPurpose(e.target.value)}
                style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
              >
                <option value="chat_reply">聊天回复</option>
                <option value="scene_execution">场景执行</option>
                <option value="memory_review">记忆审查</option>
                <option value="recommendation">推荐</option>
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>范围（类别，逗号分隔）</label>
              <input
                type="text"
                value={consentScope}
                onChange={(e) => setConsentScope(e.target.value)}
                placeholder="如：PREFERENCE,FACT"
                style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
              />
            </div>
          </div>
          {actionError && <p style={{ color: "red", marginBottom: 8, fontSize: 14 }}>{actionError}</p>}
          <button
            type="submit"
            disabled={actionLoading}
            style={{ padding: "8px 20px", cursor: "pointer", borderRadius: 6, border: "none", background: "#10b981", color: "#fff" }}
          >
            {actionLoading ? "授权中..." : "授权"}
          </button>
        </form>
      )}

      {loading ? (
        <p>加载中...</p>
      ) : (
        <>
          {memories.length > 0 && (
            <div style={{ marginBottom: 32 }}>
              <h2 style={{ fontSize: 18, marginBottom: 12 }}>我的记忆（{memories.length}）</h2>
              <div style={{ display: "grid", gap: 8 }}>
                {memories.map((mem) => (
                  <div
                    key={mem.id}
                    style={{ padding: 12, border: "1px solid #e0e0e0", borderRadius: 6, background: "#fff" }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                          <span
                            style={{
                              fontSize: 12,
                              padding: "2px 8px",
                              borderRadius: 12,
                              color: "#fff",
                              background: getCategoryColor(mem.category),
                            }}
                          >
                            {mem.category}
                          </span>
                          {mem.expires_at && (
                            <span style={{ fontSize: 12, color: "#f59e0b" }}>
                              过期: {formatDate(mem.expires_at)}
                            </span>
                          )}
                        </div>
                        <p style={{ margin: "4px 0", wordBreak: "break-word" }}>{mem.content}</p>
                        {mem.created_at && (
                          <span style={{ color: "#999", fontSize: 12 }}>{formatDate(mem.created_at)}</span>
                        )}
                      </div>
                      <button
                        onClick={() => handleDelete(mem.id)}
                        style={{
                          padding: "4px 12px",
                          cursor: "pointer",
                          borderRadius: 4,
                          border: "1px solid #ef4444",
                          background: "#fff",
                          color: "#ef4444",
                          fontSize: 12,
                          whiteSpace: "nowrap",
                        }}
                      >
                        删除
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {memories.length === 0 && (
            <p style={{ color: "#666", marginBottom: 32 }}>暂无记忆。点击「新建记忆」创建。</p>
          )}

          {consents.length > 0 && (
            <div>
              <h2 style={{ fontSize: 18, marginBottom: 12 }}>授权记录（{consents.length}）</h2>
              <div style={{ display: "grid", gap: 8 }}>
                {consents.map((c) => (
                  <div
                    key={c.id}
                    style={{ padding: 12, border: "1px solid #e0e0e0", borderRadius: 6, display: "flex", justifyContent: "space-between", alignItems: "center" }}
                  >
                    <div>
                      <span style={{ fontSize: 14 }}>
                        用途: <strong>{c.purpose}</strong>
                      </span>
                      <span
                        style={{
                          marginLeft: 8,
                          fontSize: 12,
                          padding: "2px 8px",
                          borderRadius: 12,
                          background: c.status === "GRANTED" ? "#d1fae5" : "#fee2e2",
                          color: c.status === "GRANTED" ? "#065f46" : "#991b1b",
                        }}
                      >
                        {c.status === "GRANTED" ? "已授权" : "已撤销"}
                      </span>
                      {c.expires_at && (
                        <span style={{ marginLeft: 8, fontSize: 12, color: "#999" }}>
                          过期: {formatDate(c.expires_at)}
                        </span>
                      )}
                    </div>
                    {c.status === "GRANTED" && (
                      <button
                        onClick={() => handleRevokeConsent(c.id)}
                        style={{
                          padding: "4px 12px",
                          cursor: "pointer",
                          borderRadius: 4,
                          border: "1px solid #ef4444",
                          background: "#fff",
                          color: "#ef4444",
                          fontSize: 12,
                        }}
                      >
                        撤销
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <div style={{ marginTop: 24, display: "flex", gap: 16 }}>
        <Link href="/agents" style={{ color: "#3b82f6", fontSize: 14, textDecoration: "none" }}>
          ← 智能体配置
        </Link>
        <Link href="/audit" style={{ color: "#3b82f6", fontSize: 14, textDecoration: "none" }}>
          访问记录 →
        </Link>
      </div>
    </main>
  );
}

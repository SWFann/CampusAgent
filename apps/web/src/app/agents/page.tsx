"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  getMyAgent,
  updateAgent,
  type AgentRead,
} from "@/lib/agents";
import { formatDate } from "@/lib/utils";

export default function AgentsPage() {
  const [agent, setAgent] = useState<AgentRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editPersona, setEditPersona] = useState("");
  const [editLevel, setEditLevel] = useState("L0");
  const [editConfig, setEditConfig] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchAgent = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getMyAgent();
      if (result.success && result.data) {
        setAgent(result.data);
        setEditName(result.data.name);
        setEditPersona(result.data.public_persona ?? "");
        setEditLevel(result.data.delegation_level);
      } else {
        setError(result.error?.message ?? "加载智能体失败");
      }
    } catch {
      setError("网络错误");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAgent();
  }, [fetchAgent]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    setActionLoading(true);
    try {
      const payload: Record<string, string> = {};
      if (editName !== agent?.name) payload.name = editName;
      if (editPersona !== (agent?.public_persona ?? "")) payload.public_persona = editPersona;
      if (editLevel !== agent?.delegation_level) payload.delegation_level = editLevel;
      if (editConfig.trim()) payload.private_config_encrypted = editConfig.trim();

      if (Object.keys(payload).length === 0) {
        setEditing(false);
        setActionLoading(false);
        return;
      }

      const result = await updateAgent(agent!.id, payload);
      if (result.success && result.data) {
        setAgent(result.data);
        setEditing(false);
        setEditConfig("");
      } else {
        setActionError(result.error?.message ?? "更新失败");
      }
    } catch {
      setActionError("网络错误");
    } finally {
      setActionLoading(false);
    }
  };

  const getLevelLabel = (level: string): string => {
    const labels: Record<string, string> = {
      L0: "L0 - 基础",
      L1: "L1 - 辅助",
      L2: "L2 - 场景执行",
      L3: "L3 - 高级代理",
    };
    return labels[level] ?? level;
  };

  return (
    <main style={{ maxWidth: 800, margin: "0 auto", padding: "24px 16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>我的智能体</h1>
        {agent && !editing && (
          <button
            onClick={() => setEditing(true)}
            style={{ padding: "8px 16px", cursor: "pointer", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff" }}
          >
            编辑配置
          </button>
        )}
      </div>

      {error && <p style={{ color: "red", marginBottom: 16 }}>{error}</p>}

      {loading ? (
        <p>加载中...</p>
      ) : !agent ? (
        <div>
          <p style={{ color: "#666" }}>您还没有个人智能体。注册后系统会自动为您创建。</p>
        </div>
      ) : editing ? (
        <form onSubmit={handleUpdate} style={{ padding: 16, border: "1px solid #e0e0e0", borderRadius: 8, background: "#f9fafb" }}>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>名称</label>
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
            />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>公开人格</label>
            <textarea
              value={editPersona}
              onChange={(e) => setEditPersona(e.target.value)}
              rows={3}
              style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
              placeholder="例如：友好的校园助手"
            />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>委托级别</label>
            <select
              value={editLevel}
              onChange={(e) => setEditLevel(e.target.value)}
              style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
            >
              <option value="L0">L0 - 基础</option>
              <option value="L1">L1 - 辅助</option>
              <option value="L2">L2 - 场景执行</option>
              <option value="L3">L3 - 高级代理</option>
            </select>
            <p style={{ fontSize: 12, color: "#999", marginTop: 4 }}>P6 阶段不支持 L4 委托级别</p>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>私有配置（加密存储）</label>
            <textarea
              value={editConfig}
              onChange={(e) => setEditConfig(e.target.value)}
              rows={2}
              style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
              placeholder="留空则不修改"
            />
            <p style={{ fontSize: 12, color: "#999", marginTop: 4 }}>私有配置仅您可见，加密存储</p>
          </div>
          {actionError && <p style={{ color: "red", marginBottom: 8, fontSize: 14 }}>{actionError}</p>}
          <div style={{ display: "flex", gap: 8 }}>
            <button
              type="submit"
              disabled={actionLoading}
              style={{ padding: "8px 20px", cursor: "pointer", borderRadius: 6, border: "none", background: "#3b82f6", color: "#fff" }}
            >
              {actionLoading ? "保存中..." : "保存"}
            </button>
            <button
              type="button"
              onClick={() => { setEditing(false); setActionError(null); }}
              style={{ padding: "8px 20px", cursor: "pointer", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff" }}
            >
              取消
            </button>
          </div>
        </form>
      ) : (
        <div style={{ padding: 16, border: "1px solid #e0e0e0", borderRadius: 8 }}>
          <div style={{ marginBottom: 16 }}>
            <strong style={{ fontSize: 18 }}>{agent.name}</strong>
            <span style={{ marginLeft: 8, fontSize: 12, padding: "2px 8px", borderRadius: 12, background: "#e0e7ff", color: "#4338ca" }}>
              {agent.type === "PERSONAL" ? "个人" : agent.type}
            </span>
            <span style={{ marginLeft: 4, fontSize: 12, padding: "2px 8px", borderRadius: 12, background: agent.status === "ACTIVE" ? "#d1fae5" : "#fee2e2", color: agent.status === "ACTIVE" ? "#065f46" : "#991b1b" }}>
              {agent.status === "ACTIVE" ? "活跃" : "禁用"}
            </span>
          </div>
          <div style={{ display: "grid", gap: 8, color: "#374151" }}>
            <div>
              <span style={{ color: "#999", fontSize: 14 }}>委托级别：</span>
              {getLevelLabel(agent.delegation_level)}
            </div>
            <div>
              <span style={{ color: "#999", fontSize: 14 }}>公开人格：</span>
              {agent.public_persona || "未设置"}
            </div>
            <div>
              <span style={{ color: "#999", fontSize: 14 }}>私有配置：</span>
              {agent.has_private_config ? "已设置（加密存储）" : "未设置"}
            </div>
            {agent.created_at && (
              <div>
                <span style={{ color: "#999", fontSize: 14 }}>创建时间：</span>
                {formatDate(agent.created_at)}
              </div>
            )}
          </div>
        </div>
      )}

      <div style={{ marginTop: 24, display: "flex", gap: 16 }}>
        <Link href="/memories" style={{ color: "#3b82f6", fontSize: 14, textDecoration: "none" }}>
          记忆管理 →
        </Link>
        <Link href="/audit" style={{ color: "#3b82f6", fontSize: 14, textDecoration: "none" }}>
          访问记录 →
        </Link>
        <Link href="/conversations" style={{ color: "#3b82f6", fontSize: 14, textDecoration: "none" }}>
          返回会话 →
        </Link>
      </div>
    </main>
  );
}

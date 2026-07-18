"use client";

import { useState } from "react";
import { AppShell } from "@/components/app/AppShell";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DangerConfirm } from "@/components/privacy/DangerConfirm";
import { apiGet, apiDelete } from "@/lib/api/client";
import { useAsync } from "@/lib/useAsync";
import type { MemorySummary, AuditLogEntry } from "@/lib/api/types";

interface MemoryDetail extends MemorySummary {
  agent_name?: string;
  consent_status?: string;
  consent_expires_at?: string;
}

interface MemoryListResponse {
  memories: MemoryDetail[];
  total: number;
}

interface AuditLogListResponse {
  audit_logs: AuditLogEntry[];
  total: number;
}

function MemoryContent() {
  const [reloadKey, setReloadKey] = useState(0);
  const [showContent, setShowContent] = useState<string | null>(null);

  const { data: memoryData, loading, error, reload } = useAsync<MemoryListResponse>(
    async () => apiGet("/memories"),
    [reloadKey],
  );

  const { data: auditData } = useAsync<AuditLogListResponse>(
    async () => apiGet("/audit/me", { limit: "20" }),
    [reloadKey],
  );

  const memories = memoryData?.memories ?? [];
  const auditLogs = auditData?.audit_logs ?? [];

  const handleDelete = async (memoryId: string) => {
    await apiDelete(`/memories/${memoryId}`);
    reload();
  };

  const handleRevoke = async (memoryId: string) => {
    await apiDelete(`/memories/${memoryId}/consents`);
    reload();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>记忆中心</h1>

      {/* Memory list */}
      <div className="card">
        <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>你的记忆</h2>
        {loading && <LoadingState message="正在加载记忆..." />}
        {error && <ErrorState message="加载记忆失败。" />}
        {!loading && memories.length === 0 && (
          <EmptyState title="暂无记忆" description="智能体创建的记忆会显示在这里。" />
        )}
        {memories.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
            {memories.map((mem) => (
              <div
                key={mem.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "var(--space-sm)",
                  borderRadius: "var(--radius-md)",
                  background: "var(--color-surface-hover)",
                }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", gap: "var(--space-xs)", alignItems: "center", marginBottom: "var(--space-xs)" }}>
                    <StatusBadge label={mem.category} variant="info" />
                    <StatusBadge
                      label={mem.sensitivity_level}
                      variant={mem.sensitivity_level === "HIGH" ? "danger" : mem.sensitivity_level === "MEDIUM" ? "warning" : "default"}
                    />
                    {mem.is_deleted && <StatusBadge label="已删除" variant="default" />}
                  </div>
                  <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
                    来源：{mem.source} ｜ 创建时间：{new Date(mem.created_at).toLocaleDateString()}
                    {mem.agent_name ? ` ｜ 智能体：${mem.agent_name}` : ""}
                  </p>
                </div>
                <div style={{ display: "flex", gap: "var(--space-xs)" }}>
                  {mem.consent_status && mem.consent_status !== "revoked" && !mem.is_deleted && (
                    <DangerConfirm
                      trigger={<button className="btn btn-sm">撤销授权</button>}
                      title="撤销授权"
                      message="确定撤销此记忆的授权吗？撤销后智能体将无法继续访问。"
                      confirmLabel="撤销"
                      onConfirm={() => handleRevoke(mem.id)}
                    />
                  )}
                  {!mem.is_deleted && (
                    <DangerConfirm
                      trigger={<button className="btn btn-sm btn-danger">删除</button>}
                      title="删除记忆"
                      message="确定删除此记忆吗？此操作不可撤销。"
                      confirmLabel="删除"
                      onConfirm={() => handleDelete(mem.id)}
                    />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-sm)" }}>
          默认不展示记忆正文，仅显示元数据。
        </p>
      </div>

      {/* Access log (metadata only) */}
      <div className="card">
        <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>最近访问记录</h2>
        {auditLogs.length === 0 ? (
          <EmptyState title="暂无访问记录" description="智能体访问你的记忆后，访问记录会显示在这里。" />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-xs)" }}>
            {auditLogs.map((log) => (
              <div
                key={log.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "var(--space-xs) var(--space-sm)",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--color-surface-hover)",
                  fontSize: "var(--font-size-xs)",
                }}
              >
                <span>
                  {log.action} 作用于 {log.resource_type}
                  {log.purpose ? `，用途：${log.purpose}` : ""}
                </span>
                <span style={{ color: "var(--color-text-muted)" }}>
                  {new Date(log.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
        <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-sm)" }}>
          这里只展示访问元数据，不展示载荷内容。
        </p>
      </div>
    </div>
  );
}

export default function MemoryPage() {
  return (
    <AppShell requireAuth>
      <MemoryContent />
    </AppShell>
  );
}

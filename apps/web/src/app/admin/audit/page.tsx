"use client";

import { AppShell } from "@/components/app/AppShell";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiGet } from "@/lib/api/client";
import { useAsync } from "@/lib/useAsync";
import type { AuditLogEntry } from "@/lib/api/types";

function AdminAuditContent() {
  const { data: logs, loading, error } = useAsync<AuditLogEntry[]>(
    async () => apiGet("/admin/audit-logs", { limit: "50" }),
    [],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>审计日志</h1>

      {loading && <LoadingState message="正在加载审计日志..." />}
      {error && <ErrorState message="加载审计日志失败。" />}
      {logs && logs.length === 0 && (
        <EmptyState title="暂无审计日志" description="用户与系统交互后，审计日志会显示在这里。" />
      )}
      {logs && logs.length > 0 && (
        <div className="card">
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-xs)" }}>
            {logs.map((log) => (
              <div key={log.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "var(--space-xs) var(--space-sm)", borderRadius: "var(--radius-sm)", background: "var(--color-surface-hover)" }}>
                <div style={{ display: "flex", gap: "var(--space-sm)", alignItems: "center" }}>
                  <StatusBadge label={log.action} variant="info" />
                  <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-secondary)" }}>
                    {log.resource_type}:{log.resource_id}
                  </span>
                  {log.purpose && (
                    <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
                      用途：{log.purpose}
                    </span>
                  )}
                </div>
                <div style={{ display: "flex", gap: "var(--space-sm)", alignItems: "center" }}>
                  <StatusBadge label={log.result} variant={log.result === "success" ? "success" : "danger"} />
                  <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                  {log.request_id && (
                    <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", fontFamily: "monospace" }}>
                      {log.request_id.slice(0, 8)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
        审计日志仅显示动作、资源、结果、时间和请求 ID 等元数据，不展示载荷内容。
      </p>
    </div>
  );
}

export default function AdminAuditPage() {
  return (
    <AppShell requireAuth adminOnly>
      <AdminAuditContent />
    </AppShell>
  );
}

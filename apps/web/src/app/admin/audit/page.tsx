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
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>Audit Logs</h1>

      {loading && <LoadingState message="Loading audit logs..." />}
      {error && <ErrorState message="Failed to load audit logs." />}
      {logs && logs.length === 0 && (
        <EmptyState title="No audit logs" description="Audit logs will appear here as users interact with the system." />
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
                      purpose: {log.purpose}
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
        Audit logs show only metadata: action, resource, result, timestamp, and request_id. No payload content is displayed.
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

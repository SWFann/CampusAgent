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

function MemoryContent() {
  const [reloadKey, setReloadKey] = useState(0);
  const [showContent, setShowContent] = useState<string | null>(null);

  const { data: memories, loading, error, reload } = useAsync<MemoryDetail[]>(
    async () => apiGet("/memories"),
    [reloadKey],
  );

  const { data: auditLogs } = useAsync<AuditLogEntry[]>(
    async () => apiGet("/audit/me", { limit: "20" }),
    [reloadKey],
  );

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
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>Memory Center</h1>

      {/* Memory list */}
      <div className="card">
        <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>Your Memories</h2>
        {loading && <LoadingState message="Loading memories..." />}
        {error && <ErrorState message="Failed to load memories." />}
        {memories && memories.length === 0 && (
          <EmptyState title="No memories" description="Memories created by your agents will appear here." />
        )}
        {memories && memories.length > 0 && (
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
                    {mem.is_deleted && <StatusBadge label="Deleted" variant="default" />}
                  </div>
                  <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
                    Source: {mem.source} | Created: {new Date(mem.created_at).toLocaleDateString()}
                    {mem.agent_name ? ` | Agent: ${mem.agent_name}` : ""}
                  </p>
                </div>
                <div style={{ display: "flex", gap: "var(--space-xs)" }}>
                  {mem.consent_status && mem.consent_status !== "revoked" && !mem.is_deleted && (
                    <DangerConfirm
                      trigger={<button className="btn btn-sm">Revoke Consent</button>}
                      title="Revoke Consent"
                      message="Are you sure you want to revoke consent for this memory? Agents will no longer be able to access it."
                      confirmLabel="Revoke"
                      onConfirm={() => handleRevoke(mem.id)}
                    />
                  )}
                  {!mem.is_deleted && (
                    <DangerConfirm
                      trigger={<button className="btn btn-sm btn-danger">Delete</button>}
                      title="Delete Memory"
                      message="Are you sure you want to delete this memory? This action cannot be undone."
                      confirmLabel="Delete"
                      onConfirm={() => handleDelete(mem.id)}
                    />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-sm)" }}>
          Memory content is not displayed by default. Only metadata is shown.
        </p>
      </div>

      {/* Access log (metadata only) */}
      <div className="card">
        <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>Recent Access Log</h2>
        {!auditLogs || auditLogs.length === 0 ? (
          <EmptyState title="No access logs" description="Access logs will appear here when agents access your memories." />
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
                  {log.action} on {log.resource_type}
                  {log.purpose ? ` for ${log.purpose}` : ""}
                </span>
                <span style={{ color: "var(--color-text-muted)" }}>
                  {new Date(log.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
        <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-sm)" }}>
          Only access metadata is shown. No payload content is displayed.
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

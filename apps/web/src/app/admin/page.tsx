"use client";

import { AppShell } from "@/components/app/AppShell";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiGet } from "@/lib/api/client";
import { useAsync } from "@/lib/useAsync";
import Link from "next/link";

interface SystemOverview {
  user_count: number;
  org_count: number;
  conversation_count: number;
  scene_count: number;
  model_request_count: number;
}

interface SecurityStatus {
  csrf_enabled: boolean;
  cookie_http_only: boolean;
  rate_limit_enabled: boolean;
  redaction_enabled: boolean;
  metrics_enabled: boolean;
}

function AdminContent() {
  const { data: overview, loading, error } = useAsync<SystemOverview>(
    async () => apiGet("/admin/overview"),
    [],
  );
  const { data: security } = useAsync<SecurityStatus>(
    async () => apiGet("/admin/security-status"),
    [],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>Admin Dashboard</h1>

      {/* System overview */}
      <div className="card">
        <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>System Overview</h2>
        {loading && <LoadingState message="Loading overview..." />}
        {error && <ErrorState message="Failed to load system overview." />}
        {overview && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: "var(--space-md)" }}>
            <div style={{ textAlign: "center", padding: "var(--space-md)", background: "var(--color-surface-hover)", borderRadius: "var(--radius-md)" }}>
              <p style={{ fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-bold)" }}>{overview.user_count}</p>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>Users</p>
            </div>
            <div style={{ textAlign: "center", padding: "var(--space-md)", background: "var(--color-surface-hover)", borderRadius: "var(--radius-md)" }}>
              <p style={{ fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-bold)" }}>{overview.org_count}</p>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>Organizations</p>
            </div>
            <div style={{ textAlign: "center", padding: "var(--space-md)", background: "var(--color-surface-hover)", borderRadius: "var(--radius-md)" }}>
              <p style={{ fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-bold)" }}>{overview.conversation_count}</p>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>Conversations</p>
            </div>
            <div style={{ textAlign: "center", padding: "var(--space-md)", background: "var(--color-surface-hover)", borderRadius: "var(--radius-md)" }}>
              <p style={{ fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-bold)" }}>{overview.scene_count}</p>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>Scenes</p>
            </div>
            <div style={{ textAlign: "center", padding: "var(--space-md)", background: "var(--color-surface-hover)", borderRadius: "var(--radius-md)" }}>
              <p style={{ fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-bold)" }}>{overview.model_request_count}</p>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>Model Requests</p>
            </div>
          </div>
        )}
      </div>

      {/* Quick links */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-md)" }}>
        <Link href="/admin/models" className="card" style={{ textDecoration: "none" }}>
          <h3>Model Nodes</h3>
          <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>View model providers, status, and latency.</p>
        </Link>
        <Link href="/admin/audit" className="card" style={{ textDecoration: "none" }}>
          <h3>Audit Logs</h3>
          <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>View audit metadata (no payload content).</p>
        </Link>
      </div>

      {/* Security status */}
      {security && (
        <div className="card">
          <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>Security Status</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "var(--font-size-sm)" }}>CSRF Protection</span>
              <StatusBadge label={security.csrf_enabled ? "Enabled" : "Disabled"} variant={security.csrf_enabled ? "success" : "danger"} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "var(--font-size-sm)" }}>HttpOnly Cookies</span>
              <StatusBadge label={security.cookie_http_only ? "Enabled" : "Disabled"} variant={security.cookie_http_only ? "success" : "danger"} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "var(--font-size-sm)" }}>Rate Limiting</span>
              <StatusBadge label={security.rate_limit_enabled ? "Enabled" : "Disabled"} variant={security.rate_limit_enabled ? "success" : "danger"} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "var(--font-size-sm)" }}>Data Redaction</span>
              <StatusBadge label={security.redaction_enabled ? "Enabled" : "Disabled"} variant={security.redaction_enabled ? "success" : "danger"} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "var(--font-size-sm)" }}>Metrics Collection</span>
              <StatusBadge label={security.metrics_enabled ? "Enabled" : "Disabled"} variant={security.metrics_enabled ? "success" : "danger"} />
            </div>
          </div>
        </div>
      )}

      <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
        Admin dashboard shows only metadata. No private preferences, message bodies, tokens, or API keys are displayed.
      </p>
    </div>
  );
}

export default function AdminPage() {
  return (
    <AppShell requireAuth adminOnly>
      <AdminContent />
    </AppShell>
  );
}

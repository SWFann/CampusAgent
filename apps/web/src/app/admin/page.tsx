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
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>管理后台</h1>

      {/* System overview */}
      <div className="card">
        <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>系统概览</h2>
        {loading && <LoadingState message="正在加载概览..." />}
        {error && <ErrorState message="加载系统概览失败。" />}
        {overview && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: "var(--space-md)" }}>
            <div style={{ textAlign: "center", padding: "var(--space-md)", background: "var(--color-surface-hover)", borderRadius: "var(--radius-md)" }}>
              <p style={{ fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-bold)" }}>{overview.user_count}</p>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>用户</p>
            </div>
            <div style={{ textAlign: "center", padding: "var(--space-md)", background: "var(--color-surface-hover)", borderRadius: "var(--radius-md)" }}>
              <p style={{ fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-bold)" }}>{overview.org_count}</p>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>组织</p>
            </div>
            <div style={{ textAlign: "center", padding: "var(--space-md)", background: "var(--color-surface-hover)", borderRadius: "var(--radius-md)" }}>
              <p style={{ fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-bold)" }}>{overview.conversation_count}</p>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>会话</p>
            </div>
            <div style={{ textAlign: "center", padding: "var(--space-md)", background: "var(--color-surface-hover)", borderRadius: "var(--radius-md)" }}>
              <p style={{ fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-bold)" }}>{overview.scene_count}</p>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>场景</p>
            </div>
            <div style={{ textAlign: "center", padding: "var(--space-md)", background: "var(--color-surface-hover)", borderRadius: "var(--radius-md)" }}>
              <p style={{ fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-bold)" }}>{overview.model_request_count}</p>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>模型请求</p>
            </div>
          </div>
        )}
      </div>

      {/* Quick links */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-md)" }}>
        <Link href="/admin/models" className="card" style={{ textDecoration: "none" }}>
          <h3>模型节点</h3>
          <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>查看模型供应商、状态和延迟。</p>
        </Link>
        <Link href="/admin/audit" className="card" style={{ textDecoration: "none" }}>
          <h3>审计日志</h3>
          <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>查看审计元数据（不展示载荷内容）。</p>
        </Link>
      </div>

      {/* Security status */}
      {security && (
        <div className="card">
          <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>安全状态</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "var(--font-size-sm)" }}>CSRF 防护</span>
              <StatusBadge label={security.csrf_enabled ? "已启用" : "已停用"} variant={security.csrf_enabled ? "success" : "danger"} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "var(--font-size-sm)" }}>仅 HTTP Cookie</span>
              <StatusBadge label={security.cookie_http_only ? "已启用" : "已停用"} variant={security.cookie_http_only ? "success" : "danger"} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "var(--font-size-sm)" }}>限流</span>
              <StatusBadge label={security.rate_limit_enabled ? "已启用" : "已停用"} variant={security.rate_limit_enabled ? "success" : "danger"} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "var(--font-size-sm)" }}>数据脱敏</span>
              <StatusBadge label={security.redaction_enabled ? "已启用" : "已停用"} variant={security.redaction_enabled ? "success" : "danger"} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "var(--font-size-sm)" }}>指标采集</span>
              <StatusBadge label={security.metrics_enabled ? "已启用" : "已停用"} variant={security.metrics_enabled ? "success" : "danger"} />
            </div>
          </div>
        </div>
      )}

      <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
        管理后台仅展示元数据，不展示私密偏好、消息正文、令牌或接口密钥。
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

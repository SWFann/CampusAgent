"use client";

import { AppShell } from "@/components/app/AppShell";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiGet } from "@/lib/api/client";
import { useAsync } from "@/lib/useAsync";
import type { AgentSummary } from "@/lib/api/types";

interface AgentDetail extends AgentSummary {
  delegation_level: string;
  status?: string;
  description?: string;
  scenes?: string[];
  last_run_status?: string;
  last_run_at?: string;
  requires_confirmation?: boolean;
  provider_summary?: string;
}

interface AgentListResponse {
  agents: AgentDetail[];
  total: number;
}

function AgentsContent() {
  const { data, loading, error } = useAsync<AgentListResponse>(
    async () => {
      const list = await apiGet<AgentListResponse>("/agents");
      if (list.agents.length > 0) {
        return list;
      }
      const agent = await apiGet<AgentDetail>("/agents/me");
      return { agents: [agent], total: 1 };
    },
    [],
  );
  const agents = data?.agents ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>智能体</h1>

      {loading && <LoadingState message="正在加载智能体..." />}
      {error && <ErrorState message="加载智能体失败。" />}
      {!loading && agents.length === 0 && (
        <EmptyState title="暂无智能体" description="系统会自动创建你的个人智能体。" />
      )}
      {agents.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "var(--space-md)" }}>
          {agents.map((agent) => {
            const level = agent.delegation_level?.toUpperCase() ?? "L0";
            const needsConfirm = level === "L2" || level === "L3" || agent.requires_confirmation;
            return (
              <div key={agent.id} className="card">
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "var(--space-sm)" }}>
                  <h3>{agent.name}</h3>
                  <StatusBadge label={agent.status === "ACTIVE" || agent.is_active ? "启用" : "停用"} variant={agent.status === "ACTIVE" || agent.is_active ? "success" : "default"} />
                </div>
                <div style={{ display: "flex", gap: "var(--space-xs)", flexWrap: "wrap", marginBottom: "var(--space-sm)" }}>
                  <StatusBadge label={level} variant={level === "L3" ? "danger" : level === "L2" ? "warning" : "info"} />
                  {agent.provider_summary && (
                    <StatusBadge label={agent.provider_summary} variant="default" />
                  )}
                </div>
                {needsConfirm && (
                  <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-warning)", marginBottom: "var(--space-sm)" }}>
                    &#9888; 此智能体执行操作前需要人工确认。
                  </p>
                )}
                {agent.scenes && agent.scenes.length > 0 && (
                  <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                    活跃场景：{agent.scenes.join(", ")}
                  </p>
                )}
                {agent.last_run_status && (
                  <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-xs)" }}>
                    最近运行：{agent.last_run_status} {agent.last_run_at ? `时间：${new Date(agent.last_run_at).toLocaleString()}` : ""}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
      {/* Privacy note: never render prompts, secrets, or private memory content */}
      <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
        不会展示智能体提示词、接口密钥或私密记忆内容。
      </p>
    </div>
  );
}

export default function AgentsPage() {
  return (
    <AppShell requireAuth>
      <AgentsContent />
    </AppShell>
  );
}

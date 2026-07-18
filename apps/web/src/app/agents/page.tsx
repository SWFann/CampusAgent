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
  description?: string;
  scenes?: string[];
  last_run_status?: string;
  last_run_at?: string;
  requires_confirmation?: boolean;
  provider_summary?: string;
}

function AgentsContent() {
  const { data: agents, loading, error } = useAsync<AgentDetail[]>(
    async () => apiGet("/agents"),
    [],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>Agents</h1>

      {loading && <LoadingState message="Loading agents..." />}
      {error && <ErrorState message="Failed to load agents." />}
      {agents && agents.length === 0 && (
        <EmptyState title="No agents" description="Your personal agent will be created automatically." />
      )}
      {agents && agents.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "var(--space-md)" }}>
          {agents.map((agent) => {
            const level = agent.delegation_level?.toUpperCase() ?? "L0";
            const needsConfirm = level === "L2" || level === "L3" || agent.requires_confirmation;
            return (
              <div key={agent.id} className="card">
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "var(--space-sm)" }}>
                  <h3>{agent.name}</h3>
                  <StatusBadge label={agent.is_active ? "Active" : "Inactive"} variant={agent.is_active ? "success" : "default"} />
                </div>
                <div style={{ display: "flex", gap: "var(--space-xs)", flexWrap: "wrap", marginBottom: "var(--space-sm)" }}>
                  <StatusBadge label={`Level ${level}`} variant={level === "L3" ? "danger" : level === "L2" ? "warning" : "info"} />
                  {agent.provider_summary && (
                    <StatusBadge label={agent.provider_summary} variant="default" />
                  )}
                </div>
                {needsConfirm && (
                  <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-warning)", marginBottom: "var(--space-sm)" }}>
                    &#9888; This agent requires human confirmation for actions.
                  </p>
                )}
                {agent.scenes && agent.scenes.length > 0 && (
                  <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                    Active scenes: {agent.scenes.join(", ")}
                  </p>
                )}
                {agent.last_run_status && (
                  <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-xs)" }}>
                    Last run: {agent.last_run_status} {agent.last_run_at ? `at ${new Date(agent.last_run_at).toLocaleString()}` : ""}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
      {/* Privacy note: never render prompts, secrets, or private memory content */}
      <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
        Agent prompts, API keys, and private memory content are never displayed.
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

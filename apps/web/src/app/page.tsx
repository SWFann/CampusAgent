"use client";

import { AppShell } from "@/components/app/AppShell";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useAuth } from "@/lib/auth";
import { apiGet } from "@/lib/api/client";
import { useAsync } from "@/lib/useAsync";
import type { ConversationSummary, OrganizationSummary, SceneSummary, AgentSummary } from "@/lib/api/types";
import Link from "next/link";

function HomeContent() {
  const { user } = useAuth();
  const { data: conversations, loading: convLoading, error: convError } = useAsync<ConversationSummary[]>(
    async () => apiGet("/conversations", { limit: "5" }),
    [],
  );
  const { data: orgs, loading: orgLoading, error: orgError } = useAsync<OrganizationSummary[]>(
    async () => apiGet("/organizations"),
    [],
  );
  const { data: scenes, loading: sceneLoading, error: sceneError } = useAsync<SceneSummary[]>(
    async () => apiGet("/scenes", { status: "active" }),
    [],
  );
  const { data: agents, loading: agentLoading, error: agentError } = useAsync<AgentSummary[]>(
    async () => apiGet("/agents"),
    [],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      {/* User and org summary */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h1 style={{ fontSize: "var(--font-size-xl)", marginBottom: "var(--space-xs)" }}>
              Welcome, {user?.display_name ?? "User"}
            </h1>
            <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
              {user?.email}
            </p>
          </div>
          {orgs && orgs.length > 0 && (
            <StatusBadge label={`${orgs.length} org${orgs.length > 1 ? "s" : ""}`} variant="info" />
          )}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-lg)" }}>
        {/* Recent conversations */}
        <div className="card">
          <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>
            Recent Conversations
          </h2>
          {convLoading && <LoadingState message="Loading conversations..." />}
          {convError && <ErrorState message="Failed to load conversations." requestId={null} />}
          {conversations && conversations.length === 0 && (
            <EmptyState title="No conversations" description="Start a conversation to see it here." />
          )}
          {conversations && conversations.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-xs)" }}>
              {conversations.slice(0, 5).map((conv) => (
                <Link
                  key={conv.id}
                  href={`/conversations/${conv.id}`}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "var(--space-sm)",
                    borderRadius: "var(--radius-md)",
                    textDecoration: "none",
                    background: "var(--color-surface-hover)",
                  }}
                >
                  <span style={{ fontWeight: "var(--font-weight-medium)", fontSize: "var(--font-size-sm)" }}>
                    {conv.title}
                  </span>
                  {conv.unread_count && conv.unread_count > 0 ? (
                    <StatusBadge label={`${conv.unread_count} unread`} variant="warning" />
                  ) : null}
                </Link>
              ))}
              <Link href="/messages" style={{ fontSize: "var(--font-size-sm)", marginTop: "var(--space-xs)" }}>
                View all →
              </Link>
            </div>
          )}
        </div>

        {/* Active scenes */}
        <div className="card">
          <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>
            Active Scenes
          </h2>
          {sceneLoading && <LoadingState message="Loading scenes..." />}
          {sceneError && <ErrorState message="Failed to load scenes." />}
          {scenes && scenes.length === 0 && (
            <EmptyState title="No active scenes" description="Start a scene from the Scenes page." />
          )}
          {scenes && scenes.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-xs)" }}>
              {scenes.map((scene) => (
                <Link
                  key={scene.id}
                  href={scene.scene_key === "dorm_dinner" ? "/scenes/dinner" : "/scenes"}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "var(--space-sm)",
                    borderRadius: "var(--radius-md)",
                    textDecoration: "none",
                    background: "var(--color-surface-hover)",
                  }}
                >
                  <span style={{ fontWeight: "var(--font-weight-medium)", fontSize: "var(--font-size-sm)" }}>
                    {scene.title}
                  </span>
                  <StatusBadge label={scene.status} variant="info" />
                </Link>
              ))}
            </div>
          )}
          <Link href="/scenes" style={{ fontSize: "var(--font-size-sm)", display: "inline-block", marginTop: "var(--space-sm)" }}>
            Browse scenes →
          </Link>
        </div>

        {/* Agents */}
        <div className="card">
          <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>
            Your Agents
          </h2>
          {agentLoading && <LoadingState message="Loading agents..." />}
          {agentError && <ErrorState message="Failed to load agents." />}
          {agents && agents.length === 0 && (
            <EmptyState title="No agents" description="Your personal agent will appear here." />
          )}
          {agents && agents.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-xs)" }}>
              {agents.map((agent) => (
                <div
                  key={agent.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "var(--space-sm)",
                    borderRadius: "var(--radius-md)",
                    background: "var(--color-surface-hover)",
                  }}
                >
                  <span style={{ fontWeight: "var(--font-weight-medium)", fontSize: "var(--font-size-sm)" }}>
                    {agent.name}
                  </span>
                  <StatusBadge label={agent.delegation_level} variant={agent.is_active ? "success" : "default"} />
                </div>
              ))}
            </div>
          )}
          <Link href="/agents" style={{ fontSize: "var(--font-size-sm)", display: "inline-block", marginTop: "var(--space-sm)" }}>
            Manage agents →
          </Link>
        </div>

        {/* Privacy reminder */}
        <div className="card" style={{ borderColor: "var(--color-privacy)", background: "var(--color-privacy-light)" }}>
          <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-sm)", color: "var(--color-privacy)" }}>
            Privacy Reminder
          </h2>
          <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-primary)", lineHeight: "var(--line-height-relaxed)" }}>
            Your private preferences are encrypted and only visible to you. Other members only see aggregated results.
            Manage your data in the <Link href="/memory">Memory Center</Link> or <Link href="/preferences/private">Private Preferences</Link>.
          </p>
        </div>
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <AppShell requireAuth>
      <HomeContent />
    </AppShell>
  );
}

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

interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
}

interface OrganizationListResponse {
  organizations: OrganizationSummary[];
  total: number;
}

interface SceneListResponse {
  scenes: Array<SceneSummary & { name?: string }>;
  total: number;
}

interface AgentListResponse {
  agents: AgentSummary[];
  total: number;
}

function HomeContent() {
  const { user } = useAuth();
  const { data: conversationData, loading: convLoading, error: convError } = useAsync<ConversationListResponse>(
    async () => apiGet("/conversations", { page_size: "5" }),
    [],
  );
  const { data: orgData, loading: orgLoading, error: orgError } = useAsync<OrganizationListResponse>(
    async () => apiGet("/organizations"),
    [],
  );
  const { data: sceneData, loading: sceneLoading, error: sceneError } = useAsync<SceneListResponse>(
    async () => apiGet("/scenes"),
    [],
  );
  const { data: agentData, loading: agentLoading, error: agentError } = useAsync<AgentListResponse>(
    async () => {
      const list = await apiGet<AgentListResponse>("/agents");
      if (list.agents.length > 0) return list;
      const agent = await apiGet<AgentSummary>("/agents/me");
      return { agents: [agent], total: 1 };
    },
    [],
  );
  const conversations = conversationData?.conversations ?? [];
  const orgs = orgData?.organizations ?? [];
  const scenes = sceneData?.scenes ?? [];
  const agents = agentData?.agents ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      {/* User and org summary */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h1 style={{ fontSize: "var(--font-size-xl)", marginBottom: "var(--space-xs)" }}>
              欢迎，{user?.display_name ?? "用户"}
            </h1>
            <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
              {user?.email}
            </p>
          </div>
          {orgs.length > 0 && (
            <StatusBadge label={`${orgs.length} 个组织`} variant="info" />
          )}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-lg)" }}>
        {/* Recent conversations */}
        <div className="card">
          <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>
            最近会话
          </h2>
          {convLoading && <LoadingState message="正在加载会话..." />}
          {convError && <ErrorState message="加载会话失败。" requestId={null} />}
          {!convLoading && conversations.length === 0 && (
            <EmptyState title="暂无会话" description="发起会话后会显示在这里。" />
          )}
          {conversations.length > 0 && (
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
                    {conv.title || "未命名会话"}
                  </span>
                  {conv.unread_count && conv.unread_count > 0 ? (
                    <StatusBadge label={`${conv.unread_count} 条未读`} variant="warning" />
                  ) : null}
                </Link>
              ))}
              <Link href="/conversations" style={{ fontSize: "var(--font-size-sm)", marginTop: "var(--space-xs)" }}>
                查看全部 →
              </Link>
            </div>
          )}
        </div>

        {/* Active scenes */}
        <div className="card">
          <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>
            进行中的场景
          </h2>
          {sceneLoading && <LoadingState message="正在加载场景..." />}
          {sceneError && <ErrorState message="加载场景失败。" />}
          {!sceneLoading && scenes.length === 0 && (
            <EmptyState title="暂无进行中的场景" description="可以从场景页发起新场景。" />
          )}
          {scenes.length > 0 && (
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
                    {scene.title ?? scene.name ?? "未命名场景"}
                  </span>
                  <StatusBadge label={scene.status} variant="info" />
                </Link>
              ))}
            </div>
          )}
          <Link href="/scenes" style={{ fontSize: "var(--font-size-sm)", display: "inline-block", marginTop: "var(--space-sm)" }}>
            浏览场景 →
          </Link>
        </div>

        {/* 智能体 */}
        <div className="card">
          <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>
            你的智能体
          </h2>
          {agentLoading && <LoadingState message="正在加载智能体..." />}
          {agentError && <ErrorState message="加载智能体失败。" />}
          {!agentLoading && agents.length === 0 && (
            <EmptyState title="暂无智能体" description="你的个人智能体会显示在这里。" />
          )}
          {agents.length > 0 && (
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
            管理智能体 →
          </Link>
        </div>

        {/* Privacy reminder */}
        <div className="card" style={{ borderColor: "var(--color-privacy)", background: "var(--color-privacy-light)" }}>
          <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-sm)", color: "var(--color-privacy)" }}>
            隐私提醒
          </h2>
          <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-primary)", lineHeight: "var(--line-height-relaxed)" }}>
            你的私密偏好会被加密，且仅你本人可见。其他成员只能看到聚合结果。
            你可以在 <Link href="/memory">记忆中心</Link> 或 <Link href="/preferences/private">私密偏好</Link> 管理自己的数据。
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

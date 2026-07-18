"use client";

import { useState } from "react";
import { AppShell } from "@/components/app/AppShell";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiGet, apiPost, isForbiddenError } from "@/lib/api/client";
import { useAsync } from "@/lib/useAsync";

interface OrgDetail {
  id: string;
  name: string;
  type: string;
  description?: string;
  join_policy: string;
}

interface Member {
  user_id: string;
  display_name: string;
  role: string;
  status: string;
}

function OrgDetailContent({ organizationId }: { organizationId: string }) {
  const [search, setSearch] = useState("");
  const [newMemberId, setNewMemberId] = useState("");
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const { data: org, loading: orgLoading, error: orgError, reload: reloadOrg } = useAsync<OrgDetail>(
    async () => apiGet(`/organizations/${organizationId}`),
    [organizationId],
  );
  const { data: memberData, loading: memLoading, error: memError, reload: reloadMembers } = useAsync<{ members: Member[]; total: number }>(
    async () => apiGet(`/organizations/${organizationId}/members`),
    [organizationId],
  );
  const members = memberData?.members ?? [];

  const filteredMembers = members.filter((m) =>
    !search ||
    m.display_name.toLowerCase().includes(search.toLowerCase()) ||
    m.role.toLowerCase().includes(search.toLowerCase())
  );

  const isForbidden = (orgError && isForbiddenError(orgError)) || (memError && isForbiddenError(memError));

  if (isForbidden) {
    return <ErrorState title="无权访问" message="你没有权限查看此组织。" />;
  }

  const handleJoin = async () => {
    setActionMessage(null);
    try {
      await apiPost(`/organizations/${organizationId}/join`);
      setActionMessage("已加入组织。");
      reloadOrg();
      reloadMembers();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "加入组织失败");
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemberId.trim()) return;
    setActionMessage(null);
    try {
      await apiPost(`/organizations/${organizationId}/members`, {
        user_id: newMemberId.trim(),
        role: "MEMBER",
      });
      setNewMemberId("");
      setActionMessage("成员已添加。");
      reloadMembers();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "添加成员失败");
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      {orgLoading ? (
        <LoadingState message="正在加载组织..." />
      ) : org ? (
        <div className="card">
          <h1 style={{ fontSize: "var(--font-size-xl)", marginBottom: "var(--space-xs)" }}>{org.name}</h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
            类型：{org.type} ｜ 加入方式：{org.join_policy}
          </p>
          {org.description && (
            <p style={{ marginTop: "var(--space-sm)", fontSize: "var(--font-size-sm)" }}>{org.description}</p>
          )}
          <button className="btn btn-primary" onClick={handleJoin} style={{ marginTop: "var(--space-md)" }}>
            加入组织
          </button>
        </div>
      ) : null}

      {actionMessage && <p style={{ color: "#2563eb" }}>{actionMessage}</p>}

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-md)" }}>
          <h2 style={{ fontSize: "var(--font-size-lg)" }}>成员</h2>
          <input
            className="input"
            style={{ width: 240 }}
            placeholder="按姓名或角色搜索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="搜索成员"
          />
        </div>
        <form onSubmit={handleAddMember} style={{ display: "flex", gap: "var(--space-sm)", marginBottom: "var(--space-md)" }}>
          <input
            className="input"
            placeholder="粘贴用户 ID 添加成员"
            value={newMemberId}
            onChange={(e) => setNewMemberId(e.target.value)}
          />
          <button className="btn" type="submit" disabled={!newMemberId.trim()}>
            添加成员
          </button>
        </form>
        {memLoading && <LoadingState message="正在加载成员..." />}
        {memError && !isForbidden && <ErrorState message="加载成员失败。" />}
        {filteredMembers.length === 0 && !memLoading && (
          <EmptyState title="未找到成员" description={search ? "请尝试其他搜索词。" : "此组织暂无成员。"} />
        )}
        {filteredMembers.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-xs)" }}>
            {filteredMembers.map((m) => (
              <div key={m.user_id} style={{ display: "flex", justifyContent: "space-between", padding: "var(--space-sm)", borderRadius: "var(--radius-md)", background: "var(--color-surface-hover)" }}>
                <div>
                  <span style={{ fontWeight: "var(--font-weight-medium)", fontSize: "var(--font-size-sm)" }}>{m.display_name}</span>
                  <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginLeft: "var(--space-sm)" }}>{m.status}</span>
                </div>
                <StatusBadge label={m.role} variant={m.role === "ADMIN" ? "info" : "default"} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function OrgDetailPage({ params }: { params: { organizationId: string } }) {
  return (
    <AppShell requireAuth>
      <OrgDetailContent organizationId={params.organizationId} />
    </AppShell>
  );
}

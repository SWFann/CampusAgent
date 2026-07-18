"use client";

import { useState } from "react";
import { AppShell } from "@/components/app/AppShell";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiGet, isForbiddenError } from "@/lib/api/client";
import { useAsync } from "@/lib/useAsync";
import { use } from "react";

interface OrgDetail {
  id: string;
  name: string;
  org_type: string;
  description?: string;
}

interface Member {
  id: string;
  user_id: string;
  display_name: string;
  email: string;
  role: string;
  status: string;
}

function OrgDetailContent({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = use(params);
  const [search, setSearch] = useState("");

  const { data: org, loading: orgLoading, error: orgError } = useAsync<OrgDetail>(
    async () => apiGet(`/organizations/${organizationId}`),
    [organizationId],
  );
  const { data: members, loading: memLoading, error: memError } = useAsync<Member[]>(
    async () => apiGet(`/organizations/${organizationId}/members`),
    [organizationId],
  );

  const filteredMembers = members?.filter((m) =>
    !search ||
    m.display_name.toLowerCase().includes(search.toLowerCase()) ||
    m.email.toLowerCase().includes(search.toLowerCase()) ||
    m.role.toLowerCase().includes(search.toLowerCase())
  ) ?? [];

  const isForbidden = (orgError && isForbiddenError(orgError)) || (memError && isForbiddenError(memError));

  if (isForbidden) {
    return <ErrorState title="Access Denied" message="You do not have permission to view this organization." />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      {orgLoading ? (
        <LoadingState message="Loading organization..." />
      ) : org ? (
        <div className="card">
          <h1 style={{ fontSize: "var(--font-size-xl)", marginBottom: "var(--space-xs)" }}>{org.name}</h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
            Type: {org.org_type}
          </p>
          {org.description && (
            <p style={{ marginTop: "var(--space-sm)", fontSize: "var(--font-size-sm)" }}>{org.description}</p>
          )}
        </div>
      ) : null}

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-md)" }}>
          <h2 style={{ fontSize: "var(--font-size-lg)" }}>Members</h2>
          <input
            className="input"
            style={{ width: 240 }}
            placeholder="Search by name, email, role..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search members"
          />
        </div>
        {memLoading && <LoadingState message="Loading members..." />}
        {memError && !isForbidden && <ErrorState message="Failed to load members." />}
        {filteredMembers.length === 0 && !memLoading && (
          <EmptyState title="No members found" description={search ? "Try a different search term." : "No members in this organization."} />
        )}
        {filteredMembers.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-xs)" }}>
            {filteredMembers.map((m) => (
              <div key={m.id} style={{ display: "flex", justifyContent: "space-between", padding: "var(--space-sm)", borderRadius: "var(--radius-md)", background: "var(--color-surface-hover)" }}>
                <div>
                  <span style={{ fontWeight: "var(--font-weight-medium)", fontSize: "var(--font-size-sm)" }}>{m.display_name}</span>
                  <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginLeft: "var(--space-sm)" }}>{m.email}</span>
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

export default function OrgDetailPage({ params }: { params: Promise<{ organizationId: string }> }) {
  return (
    <AppShell requireAuth>
      <OrgDetailContent params={params} />
    </AppShell>
  );
}

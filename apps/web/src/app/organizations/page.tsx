"use client";

import { AppShell } from "@/components/app/AppShell";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { apiGet, isForbiddenError } from "@/lib/api/client";
import { useAsync } from "@/lib/useAsync";
import type { OrganizationSummary } from "@/lib/api/types";
import Link from "next/link";

interface Member {
  id: string;
  user_id: string;
  display_name: string;
  email: string;
  role: string;
  status: string;
}

interface Invite {
  id: string;
  email: string;
  status: string;
  created_at: string;
}

function OrganizationsContent() {
  const { data: orgs, loading, error } = useAsync<OrganizationSummary[]>(
    async () => apiGet("/organizations"),
    [],
  );

  const isForbidden = error && isForbiddenError(error);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ fontSize: "var(--font-size-xl)" }}>Organizations</h1>
      </div>

      {loading && <LoadingState message="Loading organizations..." />}
      {isForbidden && (
        <ErrorState title="Access Denied" message="You do not have permission to view organizations." />
      )}
      {error && !isForbidden && <ErrorState message="Failed to load organizations." />}
      {orgs && orgs.length === 0 && (
        <EmptyState title="No organizations" description="Create or join an organization to get started." />
      )}
      {orgs && orgs.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "var(--space-md)" }}>
          {orgs.map((org) => (
            <Link key={org.id} href={`/organizations/${org.id}`} className="card" style={{ textDecoration: "none" }}>
              <h3 style={{ marginBottom: "var(--space-xs)" }}>{org.name}</h3>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)", marginBottom: "var(--space-sm)" }}>
                Type: {org.org_type}
              </p>
              {org.member_count !== undefined && (
                <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                  {org.member_count} members
                </p>
              )}
              {org.role && (
                <span className="badge badge-info" style={{ marginTop: "var(--space-sm)" }}>{org.role}</span>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function OrganizationsPage() {
  return (
    <AppShell requireAuth>
      <OrganizationsContent />
    </AppShell>
  );
}

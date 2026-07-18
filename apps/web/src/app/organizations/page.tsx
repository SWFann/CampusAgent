"use client";

import { AppShell } from "@/components/app/AppShell";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiGet, apiPost, isForbiddenError } from "@/lib/api/client";
import { useAsync } from "@/lib/useAsync";
import Link from "next/link";
import { useState } from "react";

interface OrganizationListItem {
  id: string;
  name: string;
  type: string;
  visibility: string;
  status: string;
  member_count: number;
}

interface OrganizationListResponse {
  organizations: OrganizationListItem[];
  total: number;
  page: number;
  page_size: number;
}

const ORG_TYPES = [
  { value: "SCHOOL", label: "学校" },
  { value: "COLLEGE", label: "学院" },
  { value: "CLASS", label: "班级" },
  { value: "DORM", label: "宿舍" },
  { value: "CLUB", label: "社团" },
  { value: "COURSE", label: "课程" },
  { value: "TEAM", label: "项目组" },
  { value: "OTHER", label: "其他" },
];

function orgTypeLabel(value: string): string {
  return ORG_TYPES.find((item) => item.value === value)?.label ?? value;
}

function OrganizationsContent() {
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("DORM");
  const [description, setDescription] = useState("");
  const [joinPolicy, setJoinPolicy] = useState("OPEN");
  const [visibility, setVisibility] = useState("PUBLIC");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const { data, loading, error, reload } = useAsync<OrganizationListResponse>(
    async () => apiGet("/organizations"),
    [],
  );
  const orgs = data?.organizations ?? [];

  const isForbidden = error && isForbiddenError(error);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      await apiPost("/organizations", {
        name: name.trim(),
        type,
        description: description.trim() || undefined,
        visibility,
        join_policy: joinPolicy,
      });
      setName("");
      setDescription("");
      setShowCreate(false);
      reload();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "创建组织失败");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ fontSize: "var(--font-size-xl)" }}>组织</h1>
        <button className="btn btn-primary" onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? "取消创建" : "创建组织"}
        </button>
      </div>

      {showCreate && (
        <form className="card" onSubmit={handleCreate} style={{ display: "grid", gap: "var(--space-md)" }}>
          <h2 style={{ fontSize: "var(--font-size-lg)" }}>创建校园组织</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--space-md)" }}>
            <label>
              <span style={{ display: "block", marginBottom: 6 }}>组织名称</span>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：光电学院 2026 级 1 班" />
            </label>
            <label>
              <span style={{ display: "block", marginBottom: 6 }}>组织类型</span>
              <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
                {ORG_TYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label>
              <span style={{ display: "block", marginBottom: 6 }}>加入方式</span>
              <select className="input" value={joinPolicy} onChange={(e) => setJoinPolicy(e.target.value)}>
                <option value="OPEN">开放加入</option>
                <option value="APPROVAL">需要审核</option>
                <option value="INVITE_ONLY">仅邀请</option>
                <option value="CLOSED">关闭加入</option>
              </select>
            </label>
            <label>
              <span style={{ display: "block", marginBottom: 6 }}>可见性</span>
              <select className="input" value={visibility} onChange={(e) => setVisibility(e.target.value)}>
                <option value="PUBLIC">公开</option>
                <option value="MEMBERS_ONLY">仅成员可见</option>
                <option value="PRIVATE">私密</option>
              </select>
            </label>
          </div>
          <label>
            <span style={{ display: "block", marginBottom: 6 }}>说明</span>
            <textarea className="input" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="这个组织用于什么协作？" rows={3} />
          </label>
          {createError && <ErrorState message={createError} />}
          <button className="btn btn-primary" disabled={creating || !name.trim()} type="submit">
            {creating ? "创建中..." : "创建"}
          </button>
        </form>
      )}

      {loading && <LoadingState message="正在加载组织..." />}
      {isForbidden && (
        <ErrorState title="无权访问" message="你没有权限查看组织。" />
      )}
      {error && !isForbidden && <ErrorState message="加载组织失败。" />}
      {orgs && orgs.length === 0 && (
        <EmptyState title="暂无组织" description="创建或加入组织后即可开始使用。" />
      )}
      {orgs && orgs.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "var(--space-md)" }}>
          {orgs.map((org) => (
            <Link key={org.id} href={`/organizations/${org.id}`} className="card" style={{ textDecoration: "none" }}>
              <h3 style={{ marginBottom: "var(--space-xs)" }}>{org.name}</h3>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)", marginBottom: "var(--space-sm)" }}>
                类型：{orgTypeLabel(org.type)}
              </p>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                {org.member_count} 名成员
              </p>
              <span style={{ display: "inline-block", marginTop: "var(--space-sm)" }}>
                <StatusBadge label={org.visibility} variant="info" />
              </span>
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

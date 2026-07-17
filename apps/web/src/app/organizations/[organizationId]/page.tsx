"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  addMember,
  getOrganization,
  joinOrganization,
  leaveOrganization,
  listMembers,
  removeMember,
  updateMemberRole,
  type Organization,
  type OrganizationMember,
} from "@/lib/organizations";

export default function OrganizationDetailPage() {
  const params = useParams();
  const orgId = params.organizationId as string;

  const [org, setOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showAddForm, setShowAddForm] = useState(false);
  const [addUserId, setAddUserId] = useState("");
  const [addRole, setAddRole] = useState("MEMBER");
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [orgResult, membersResult] = await Promise.all([
        getOrganization(orgId),
        listMembers(orgId).catch(() => ({ success: false } as const)),
      ]);
      if (orgResult.success && orgResult.data) {
        setOrg(orgResult.data);
      } else {
        setError(orgResult.error?.message ?? "加载组织失败");
      }
      if (membersResult.success && "data" in membersResult && membersResult.data) {
        setMembers(membersResult.data.members);
      }
    } catch {
      setError("网络错误");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    const result = await addMember(orgId, addUserId, addRole);
    if (result.success) {
      setShowAddForm(false);
      setAddUserId("");
      setAddRole("MEMBER");
      void fetchData();
    } else {
      setActionError(result.error?.message ?? "添加成员失败");
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    setActionError(null);
    const result = await updateMemberRole(orgId, userId, newRole);
    if (!result.success) {
      setActionError(result.error?.message ?? "修改角色失败");
    } else {
      void fetchData();
    }
  };

  const handleRemoveMember = async (userId: string) => {
    setActionError(null);
    try {
      await removeMember(orgId, userId);
      void fetchData();
    } catch {
      setActionError("移除成员失败");
    }
  };

  const handleJoin = async () => {
    setActionError(null);
    const result = await joinOrganization(orgId);
    if (!result.success) {
      setActionError(result.error?.message ?? "加入失败");
    } else {
      void fetchData();
    }
  };

  const handleLeave = async () => {
    setActionError(null);
    try {
      await leaveOrganization(orgId);
      void fetchData();
    } catch {
      setActionError("退出失败");
    }
  };

  if (loading) return <main style={{ padding: 24 }}><p>加载中...</p></main>;
  if (error) return <main style={{ padding: 24 }}><p style={{ color: "red" }}>{error}</p></main>;
  if (!org) return <main style={{ padding: 24 }}><p>组织不存在</p></main>;

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: "0 0 8px 0" }}>{org.name}</h1>
        <div style={{ color: "#666", fontSize: 14 }}>
          {org.type} · {org.visibility} · {org.join_policy} · {org.status}
        </div>
        {org.description && <p style={{ marginTop: 8 }}>{org.description}</p>}
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        <button onClick={handleJoin} style={{ padding: "6px 12px", cursor: "pointer" }}>加入</button>
        <button onClick={handleLeave} style={{ padding: "6px 12px", cursor: "pointer" }}>退出</button>
        <button onClick={() => setShowAddForm(!showAddForm)} style={{ padding: "6px 12px", cursor: "pointer" }}>
          {showAddForm ? "取消" : "添加成员"}
        </button>
      </div>

      {actionError && <p style={{ color: "red", marginBottom: 12 }}>{actionError}</p>}

      {showAddForm && (
        <form onSubmit={handleAddMember} style={{ marginBottom: 24, padding: 16, border: "1px solid #e0e0e0", borderRadius: 8 }}>
          <div style={{ display: "flex", gap: 12, alignItems: "end" }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", marginBottom: 4 }}>用户 ID</label>
              <input
                type="text"
                value={addUserId}
                onChange={(e) => setAddUserId(e.target.value)}
                required
                style={{ width: "100%", padding: 8, boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 4 }}>角色</label>
              <select value={addRole} onChange={(e) => setAddRole(e.target.value)} style={{ padding: 8 }}>
                <option value="MEMBER">成员</option>
                <option value="ADMIN">管理员</option>
                <option value="GUEST">访客</option>
              </select>
            </div>
            <button type="submit" style={{ padding: "8px 16px", cursor: "pointer" }}>添加</button>
          </div>
        </form>
      )}

      <h2 style={{ fontSize: 18, marginBottom: 12 }}>成员 ({members.length})</h2>
      {members.length === 0 ? (
        <p style={{ color: "#666" }}>暂无成员</p>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {members.map((m) => (
            <div
              key={m.user_id}
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 12, border: "1px solid #e0e0e0", borderRadius: 6 }}
            >
              <div>
                <strong>{m.display_name}</strong>
                <span style={{ marginLeft: 8, color: "#666", fontSize: 14 }}>{m.role} · {m.status}</span>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <select
                  value={m.role}
                  onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                  style={{ padding: 4 }}
                >
                  <option value="MEMBER">成员</option>
                  <option value="ADMIN">管理员</option>
                  <option value="GUEST">访客</option>
                  <option value="OWNER">所有者</option>
                </select>
                <button
                  onClick={() => handleRemoveMember(m.user_id)}
                  style={{ padding: "4px 8px", cursor: "pointer", color: "red" }}
                >
                  移除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}

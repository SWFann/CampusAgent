"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  createOrganization,
  listOrganizations,
  type OrganizationListItem,
} from "@/lib/organizations";

export default function OrganizationsPage() {
  const [orgs, setOrgs] = useState<OrganizationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  const [formData, setFormData] = useState({
    name: "",
    type: "CLUB",
    visibility: "PUBLIC",
    join_policy: "OPEN",
    description: "",
  });
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const fetchOrgs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listOrganizations();
      if (result.success && result.data) {
        setOrgs(result.data.organizations);
      } else {
        setError(result.error?.message ?? "加载组织列表失败");
      }
    } catch {
      setError("网络错误");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchOrgs();
  }, [fetchOrgs]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);
    try {
      const result = await createOrganization({
        name: formData.name,
        type: formData.type,
        visibility: formData.visibility,
        join_policy: formData.join_policy,
        description: formData.description || undefined,
      });
      if (result.success) {
        setShowCreateForm(false);
        setFormData({
          name: "",
          type: "CLUB",
          visibility: "PUBLIC",
          join_policy: "OPEN",
          description: "",
        });
        void fetchOrgs();
      } else {
        setCreateError(result.error?.message ?? "创建组织失败");
      }
    } catch {
      setCreateError("网络错误");
    } finally {
      setCreating(false);
    }
  };

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>组织</h1>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          style={{ padding: "8px 16px", cursor: "pointer" }}
        >
          {showCreateForm ? "取消" : "创建组织"}
        </button>
      </div>

      {showCreateForm && (
        <form onSubmit={handleCreate} style={{ marginBottom: 24, padding: 16, border: "1px solid #e0e0e0", borderRadius: 8 }}>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", marginBottom: 4 }}>名称 *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              maxLength={120}
              style={{ width: "100%", padding: 8, boxSizing: "border-box" }}
            />
          </div>
          <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", marginBottom: 4 }}>类型</label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                style={{ width: "100%", padding: 8 }}
              >
                <option value="SCHOOL">学校</option>
                <option value="COLLEGE">学院</option>
                <option value="DEPARTMENT">系</option>
                <option value="CLASS">班级</option>
                <option value="DORM">宿舍</option>
                <option value="CLUB">社团</option>
                <option value="COURSE">课程</option>
                <option value="TEAM">团队</option>
                <option value="OTHER">其他</option>
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", marginBottom: 4 }}>可见性</label>
              <select
                value={formData.visibility}
                onChange={(e) => setFormData({ ...formData, visibility: e.target.value })}
                style={{ width: "100%", padding: 8 }}
              >
                <option value="PUBLIC">公开</option>
                <option value="MEMBERS_ONLY">仅成员</option>
                <option value="PRIVATE">私密</option>
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", marginBottom: 4 }}>加入策略</label>
              <select
                value={formData.join_policy}
                onChange={(e) => setFormData({ ...formData, join_policy: e.target.value })}
                style={{ width: "100%", padding: 8 }}
              >
                <option value="OPEN">开放</option>
                <option value="APPROVAL">审批</option>
                <option value="INVITE_ONLY">仅邀请</option>
                <option value="CLOSED">关闭</option>
              </select>
            </div>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", marginBottom: 4 }}>描述</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              maxLength={500}
              rows={3}
              style={{ width: "100%", padding: 8, boxSizing: "border-box" }}
            />
          </div>
          {createError && <p style={{ color: "red", marginBottom: 8 }}>{createError}</p>}
          <button type="submit" disabled={creating} style={{ padding: "8px 16px", cursor: "pointer" }}>
            {creating ? "创建中..." : "创建"}
          </button>
        </form>
      )}

      {loading && <p>加载中...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}
      {!loading && !error && orgs.length === 0 && <p>暂无组织</p>}
      {!loading && !error && orgs.length > 0 && (
        <div style={{ display: "grid", gap: 12 }}>
          {orgs.map((org) => (
            <Link
              key={org.id}
              href={`/organizations/${org.id}`}
              style={{ display: "block", padding: 16, border: "1px solid #e0e0e0", borderRadius: 8, textDecoration: "none", color: "inherit" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong>{org.name}</strong>
                  <span style={{ marginLeft: 8, color: "#666", fontSize: 14 }}>{org.type}</span>
                </div>
                <div style={{ fontSize: 14, color: "#666" }}>
                  {org.member_count} 成员 · {org.visibility}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}

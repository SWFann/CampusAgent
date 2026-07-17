"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  getRecommended,
  searchDirectory,
  type DirectoryOrganizationResult,
  type DirectoryRecommendedItem,
  type DirectoryUserResult,
} from "@/lib/directory";

export default function DirectoryPage() {
  const [query, setQuery] = useState("");
  const [searchType, setSearchType] = useState("all");
  const [users, setUsers] = useState<DirectoryUserResult[]>([]);
  const [organizations, setOrganizations] = useState<DirectoryOrganizationResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const [recommendations, setRecommendations] = useState<DirectoryRecommendedItem[]>([]);
  const [recLoading, setRecLoading] = useState(true);

  const fetchRecommendations = useCallback(async () => {
    setRecLoading(true);
    try {
      const result = await getRecommended();
      if (result.success && result.data) {
        setRecommendations(result.data.recommendations);
      }
    } catch {
      // Silent fail for recommendations
    } finally {
      setRecLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchRecommendations();
  }, [fetchRecommendations]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim().length < 2) return;
    setSearching(true);
    setSearchError(null);
    setHasSearched(true);
    try {
      const result = await searchDirectory(query, searchType);
      if (result.success && result.data) {
        setUsers(result.data.users);
        setOrganizations(result.data.organizations);
      } else {
        setSearchError(result.error?.message ?? "搜索失败");
      }
    } catch {
      setSearchError("网络错误");
    } finally {
      setSearching(false);
    }
  };

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px" }}>
      <h1 style={{ marginBottom: 24 }}>校园目录</h1>

      <form onSubmit={handleSearch} style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索用户或组织（至少 2 个字符）"
            style={{ flex: 1, padding: 8, boxSizing: "border-box" }}
          />
          <select value={searchType} onChange={(e) => setSearchType(e.target.value)} style={{ padding: 8 }}>
            <option value="all">全部</option>
            <option value="users">用户</option>
            <option value="organizations">组织</option>
          </select>
          <button type="submit" disabled={searching} style={{ padding: "8px 16px", cursor: "pointer" }}>
            {searching ? "搜索中..." : "搜索"}
          </button>
        </div>
      </form>

      {searchError && <p style={{ color: "red", marginBottom: 16 }}>{searchError}</p>}

      {hasSearched && !searching && !searchError && users.length === 0 && organizations.length === 0 && (
        <p style={{ color: "#666", marginBottom: 24 }}>无搜索结果</p>
      )}

      {users.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, marginBottom: 12 }}>用户 ({users.length})</h2>
          <div style={{ display: "grid", gap: 8 }}>
            {users.map((u) => (
              <div key={u.id} style={{ padding: 12, border: "1px solid #e0e0e0", borderRadius: 6 }}>
                <strong>{u.display_name}</strong>
                <span style={{ marginLeft: 8, color: "#666", fontSize: 14 }}>{u.profile_visibility}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {organizations.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, marginBottom: 12 }}>组织 ({organizations.length})</h2>
          <div style={{ display: "grid", gap: 8 }}>
            {organizations.map((o) => (
              <Link
                key={o.id}
                href={`/organizations/${o.id}`}
                style={{ display: "block", padding: 12, border: "1px solid #e0e0e0", borderRadius: 6, textDecoration: "none", color: "inherit" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong>{o.name}</strong>
                  <span style={{ color: "#666", fontSize: 14 }}>{o.type} · {o.member_count} 成员</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {!hasSearched && (
        <div>
          <h2 style={{ fontSize: 18, marginBottom: 12 }}>推荐组织</h2>
          {recLoading && <p>加载中...</p>}
          {!recLoading && recommendations.length === 0 && <p style={{ color: "#666" }}>暂无推荐</p>}
          {!recLoading && recommendations.length > 0 && (
            <div style={{ display: "grid", gap: 8 }}>
              {recommendations.map((r) => (
                <Link
                  key={r.id}
                  href={`/organizations/${r.id}`}
                  style={{ display: "block", padding: 12, border: "1px solid #e0e0e0", borderRadius: 6, textDecoration: "none", color: "inherit" }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <strong>{r.name}</strong>
                    <span style={{ color: "#999", fontSize: 12 }}>{r.reason}</span>
                  </div>
                  <span style={{ color: "#666", fontSize: 14 }}>{r.type}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </main>
  );
}

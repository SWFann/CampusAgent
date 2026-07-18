"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  listMyAuditLogs,
  type AuditLogRead,
} from "@/lib/audit";
import { formatDate } from "@/lib/utils";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLogRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listMyAuditLogs(100);
      if (result.success && result.data) {
        setLogs(result.data.audit_logs);
      } else {
        setError(result.error?.message ?? "加载访问记录失败");
      }
    } catch {
      setError("网络错误");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchLogs();
  }, [fetchLogs]);

  const getActionLabel = (action: string): string => {
    const labels: Record<string, string> = {
      memory_read: "记忆读取",
      memory_write: "记忆写入",
      memory_delete: "记忆删除",
      consent_grant: "授权授予",
      consent_revoke: "授权撤销",
      agent_config_update: "智能体配置更新",
      agent_run: "智能体运行",
    };
    return labels[action] ?? action;
  };

  const getResultColor = (result: string): string => {
    switch (result) {
      case "SUCCESS": return "#d1fae5";
      case "DENIED": return "#fee2e2";
      case "ERROR": return "#fef3c7";
      default: return "#f3f4f6";
    }
  };

  const getResultTextColor = (result: string): string => {
    switch (result) {
      case "SUCCESS": return "#065f46";
      case "DENIED": return "#991b1b";
      case "ERROR": return "#92400e";
      default: return "#374151";
    }
  };

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "24px 16px" }}>
      <h1 style={{ marginBottom: 16 }}>访问记录</h1>

      <div style={{ marginBottom: 16, padding: 12, background: "#f0f9ff", borderRadius: 6, fontSize: 14, color: "#075985" }}>
        📋 以下为您账户的敏感操作审计记录。记录仅包含元数据，不含记忆正文或私有内容。
      </div>

      {error && <p style={{ color: "red", marginBottom: 16 }}>{error}</p>}

      {loading ? (
        <p>加载中...</p>
      ) : logs.length === 0 ? (
        <p style={{ color: "#666" }}>暂无访问记录。</p>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {logs.map((log) => (
            <div
              key={log.id}
              style={{ padding: 12, border: "1px solid #e0e0e0", borderRadius: 6, background: "#fff" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <strong style={{ fontSize: 14 }}>{getActionLabel(log.action)}</strong>
                  <span
                    style={{
                      fontSize: 12,
                      padding: "2px 8px",
                      borderRadius: 12,
                      background: getResultColor(log.result),
                      color: getResultTextColor(log.result),
                    }}
                  >
                    {log.result}
                  </span>
                </div>
                {log.created_at && (
                  <span style={{ color: "#999", fontSize: 12 }}>{formatDate(log.created_at)}</span>
                )}
              </div>
              <div style={{ fontSize: 13, color: "#666" }}>
                {log.resource_type && <span>资源: {log.resource_type}</span>}
                {log.resource_id && <span> / {log.resource_id.slice(0, 8)}...</span>}
                {log.purpose && <span> | 用途: {log.purpose}</span>}
                {log.request_id && <span> | 请求 ID：{log.request_id.slice(0, 8)}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: 24, display: "flex", gap: 16 }}>
        <Link href="/memories" style={{ color: "#3b82f6", fontSize: 14, textDecoration: "none" }}>
          ← 记忆管理
        </Link>
        <Link href="/agents" style={{ color: "#3b82f6", fontSize: 14, textDecoration: "none" }}>
          智能体配置 →
        </Link>
      </div>
    </main>
  );
}

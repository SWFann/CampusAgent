/**
 * Audit API client for CampusAgent.
 *
 * Privacy:
 * - Audit logs never contain content, prompt, or memory plaintext.
 * - All requests use HttpOnly cookies for authentication.
 */

const API_ORIGIN = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
const API_BASE = `${API_ORIGIN}/api/v1`;

interface ApiResult<T> {
  success: boolean;
  data?: T;
  error?: { code: string; message: string; details?: Record<string, unknown> };
  request_id?: string;
}

export interface AuditLogRead {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  purpose: string | null;
  result: string;
  request_id: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string | null;
}

export interface AuditLogListResponse {
  audit_logs: AuditLogRead[];
  total: number;
}

/** List audit logs for the current user only. No content/plaintext. */
export async function listMyAuditLogs(
  limit: number = 50
): Promise<ApiResult<AuditLogListResponse>> {
  const resp = await fetch(`${API_BASE}/audit/me?limit=${limit}`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

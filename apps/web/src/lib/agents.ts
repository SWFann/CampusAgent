/**
 * Agent API client for CampusAgent.
 *
 * All requests use `credentials: 'include'` to send HttpOnly cookies.
 * Write requests (POST/PATCH/DELETE) automatically include the X-CSRF-Token
 * header via the csrf helper.
 *
 * Privacy:
 * - private_config_encrypted is never stored in localStorage/sessionStorage.
 * - Agent responses only contain has_private_config flag, not the value.
 */

import { getWriteHeaders } from "./csrf";

const API_ORIGIN = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
const API_BASE = `${API_ORIGIN}/api/v1`;

interface ApiResult<T> {
  success: boolean;
  data?: T;
  error?: { code: string; message: string; details?: Record<string, unknown> };
  request_id?: string;
}

export interface AgentRead {
  id: string;
  owner_user_id: string;
  type: string;
  name: string;
  avatar_url: string | null;
  public_persona: string | null;
  delegation_level: string;
  status: string;
  has_private_config: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface AgentListResponse {
  agents: AgentRead[];
  total: number;
}

/** Get the current user's personal agent. */
export async function getMyAgent(): Promise<ApiResult<AgentRead>> {
  const resp = await fetch(`${API_BASE}/agents/me`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

/** Get an agent by ID. Owner sees full info; admin sees metadata only. */
export async function getAgent(agentId: string): Promise<ApiResult<AgentRead>> {
  const resp = await fetch(`${API_BASE}/agents/${agentId}`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

/** List all agents owned by the current user. */
export async function listMyAgents(): Promise<ApiResult<AgentListResponse>> {
  const resp = await fetch(`${API_BASE}/agents`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

/** Update an agent. Only the owner can update. */
export async function updateAgent(
  agentId: string,
  payload: {
    name?: string;
    avatar_url?: string;
    public_persona?: string;
    delegation_level?: string;
    private_config_encrypted?: string;
  }
): Promise<ApiResult<AgentRead>> {
  const resp = await fetch(`${API_BASE}/agents/${agentId}`, {
    method: "PATCH",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return resp.json();
}

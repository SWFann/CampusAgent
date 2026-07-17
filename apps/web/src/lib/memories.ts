/**
 * Memory API client for CampusAgent.
 *
 * Privacy:
 * - Memory content is never stored in localStorage/sessionStorage.
 * - All requests use HttpOnly cookies for authentication.
 * - Write requests include CSRF token.
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

export interface MemoryRead {
  id: string;
  owner_user_id: string;
  agent_id: string | null;
  category: string;
  sensitivity_level: string;
  source: string;
  content: string | null;
  content_hash: string;
  encryption_key_version: number;
  expires_at: string | null;
  deleted_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MemoryListResponse {
  memories: MemoryRead[];
  total: number;
}

export interface ConsentRead {
  id: string;
  grantor_user_id: string;
  grantee_agent_id: string;
  purpose: string;
  scope: Record<string, unknown> | null;
  status: string;
  granted_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
}

export interface ConsentListResponse {
  consents: ConsentRead[];
  total: number;
}

/** Create a new memory item. */
export async function createMemory(payload: {
  content: string;
  category: string;
  sensitivity_level?: string;
  source?: string;
  agent_id?: string;
  expires_at?: string;
}): Promise<ApiResult<MemoryRead>> {
  const resp = await fetch(`${API_BASE}/memories`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return resp.json();
}

/** List memories for the current user. */
export async function listMemories(
  category?: string
): Promise<ApiResult<MemoryListResponse>> {
  const params = category ? `?category=${encodeURIComponent(category)}` : "";
  const resp = await fetch(`${API_BASE}/memories${params}`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

/** Get a memory by ID. */
export async function getMemory(
  memoryId: string
): Promise<ApiResult<MemoryRead>> {
  const resp = await fetch(`${API_BASE}/memories/${memoryId}`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

/** Update a memory. Owner-only. */
export async function updateMemory(
  memoryId: string,
  payload: {
    content?: string;
    category?: string;
    sensitivity_level?: string;
    expires_at?: string;
  }
): Promise<ApiResult<MemoryRead>> {
  const resp = await fetch(`${API_BASE}/memories/${memoryId}`, {
    method: "PATCH",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return resp.json();
}

/** Soft-delete a memory. Owner-only. */
export async function deleteMemory(
  memoryId: string
): Promise<ApiResult<null>> {
  const resp = await fetch(`${API_BASE}/memories/${memoryId}`, {
    method: "DELETE",
    headers: getWriteHeaders(),
    credentials: "include",
  });
  return resp.json();
}

/** Grant consent for an agent to access memories. */
export async function grantConsent(payload: {
  agent_id: string;
  purpose: string;
  scope?: Record<string, unknown>;
  expires_at?: string;
}): Promise<ApiResult<ConsentRead>> {
  const resp = await fetch(`${API_BASE}/memories/consents`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return resp.json();
}

/** List consent records for the current user. */
export async function listConsents(): Promise<ApiResult<ConsentListResponse>> {
  const resp = await fetch(`${API_BASE}/memories/consents`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

/** Revoke consent. Takes effect immediately. */
export async function revokeConsent(
  consentId: string
): Promise<ApiResult<null>> {
  const resp = await fetch(`${API_BASE}/memories/consents/${consentId}`, {
    method: "DELETE",
    headers: getWriteHeaders(),
    credentials: "include",
  });
  return resp.json();
}

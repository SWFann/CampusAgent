/**
 * Organization API helpers for CampusAgent.
 *
 * All requests use `credentials: 'include'` to send HttpOnly cookies.
 * Write requests (POST/PATCH/DELETE) include the X-CSRF-Token header.
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

export interface Organization {
  id: string;
  name: string;
  slug?: string;
  type: string;
  parent_id?: string;
  description?: string;
  visibility: string;
  join_policy: string;
  status: string;
  capacity?: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface OrganizationListItem {
  id: string;
  name: string;
  type: string;
  visibility: string;
  status: string;
  member_count: number;
}

export interface OrganizationMember {
  user_id: string;
  display_name: string;
  avatar_url?: string;
  global_role?: string;
  role: string;
  status: string;
  joined_at?: string;
  created_at: string;
}

/** List organizations visible to the caller. */
export async function listOrganizations(
  page: number = 1,
  pageSize: number = 20
): Promise<ApiResult<{ organizations: OrganizationListItem[]; total: number; page: number; page_size: number }>> {
  const resp = await fetch(`${API_BASE}/organizations?page=${page}&page_size=${pageSize}`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

/** Get a single organization. */
export async function getOrganization(id: string): Promise<ApiResult<Organization>> {
  const resp = await fetch(`${API_BASE}/organizations/${id}`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

/** Create a new organization. */
export async function createOrganization(payload: {
  name: string;
  type: string;
  slug?: string;
  parent_id?: string;
  description?: string;
  visibility?: string;
  join_policy?: string;
  capacity?: number;
}): Promise<ApiResult<Organization>> {
  const resp = await fetch(`${API_BASE}/organizations`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return resp.json();
}

/** Update an organization. */
export async function updateOrganization(
  id: string,
  payload: Partial<{
    name: string;
    description: string;
    visibility: string;
    join_policy: string;
    capacity: number;
  }>
): Promise<ApiResult<Organization>> {
  const resp = await fetch(`${API_BASE}/organizations/${id}`, {
    method: "PATCH",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return resp.json();
}

/** Soft-delete an organization. */
export async function deleteOrganization(id: string): Promise<void> {
  await fetch(`${API_BASE}/organizations/${id}`, {
    method: "DELETE",
    headers: getWriteHeaders(),
    credentials: "include",
  });
}

/** List members of an organization. */
export async function listMembers(
  orgId: string
): Promise<ApiResult<{ members: OrganizationMember[]; total: number }>> {
  const resp = await fetch(`${API_BASE}/organizations/${orgId}/members`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

/** Add a member to an organization. */
export async function addMember(
  orgId: string,
  userId: string,
  role: string = "MEMBER"
): Promise<ApiResult<OrganizationMember>> {
  const resp = await fetch(`${API_BASE}/organizations/${orgId}/members`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify({ user_id: userId, role }),
  });
  return resp.json();
}

/** Update a member's role. */
export async function updateMemberRole(
  orgId: string,
  userId: string,
  role: string
): Promise<ApiResult<OrganizationMember>> {
  const resp = await fetch(`${API_BASE}/organizations/${orgId}/members/${userId}`, {
    method: "PATCH",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify({ role }),
  });
  return resp.json();
}

/** Remove a member from an organization. */
export async function removeMember(orgId: string, userId: string): Promise<void> {
  await fetch(`${API_BASE}/organizations/${orgId}/members/${userId}`, {
    method: "DELETE",
    headers: getWriteHeaders(),
    credentials: "include",
  });
}

/** Join an organization via self-service. */
export async function joinOrganization(
  orgId: string
): Promise<ApiResult<{ organization_id: string; user_id: string; role: string; status: string }>> {
  const resp = await fetch(`${API_BASE}/organizations/${orgId}/join`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
  });
  return resp.json();
}

/** Leave an organization. */
export async function leaveOrganization(orgId: string): Promise<void> {
  await fetch(`${API_BASE}/organizations/${orgId}/leave`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
  });
}

import { getWriteHeaders } from "./csrf";

const API_ORIGIN = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
const API_BASE = `${API_ORIGIN}/api/v1`;

interface ApiResult<T> {
  success: boolean;
  data?: T;
  error?: { code: string; message: string; details?: Record<string, unknown> };
  request_id?: string;
}

export interface ContactUser {
  id: string;
  display_name: string;
  avatar_url: string | null;
}

export interface ContactItem {
  user: ContactUser;
  relationship_id: string;
  status: string;
  requested_at: string;
  responded_at: string | null;
}

export interface ContactRequestItem {
  id: string;
  requester: ContactUser;
  addressee: ContactUser;
  status: string;
  requested_at: string;
}

export interface ContactListResponse {
  contacts: ContactItem[];
  total: number;
}

export interface ContactRequestsResponse {
  incoming: ContactRequestItem[];
  outgoing: ContactRequestItem[];
}

export async function listContacts(): Promise<ApiResult<ContactListResponse>> {
  const resp = await fetch(`${API_BASE}/contacts`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

export async function listContactRequests(): Promise<ApiResult<ContactRequestsResponse>> {
  const resp = await fetch(`${API_BASE}/contacts/requests`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

export async function createContactRequest(
  targetUserId: string,
): Promise<ApiResult<ContactRequestItem>> {
  const resp = await fetch(`${API_BASE}/contacts/requests`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify({ target_user_id: targetUserId }),
  });
  return resp.json();
}

export async function acceptContactRequest(
  requestId: string,
): Promise<ApiResult<ContactRequestItem>> {
  const resp = await fetch(`${API_BASE}/contacts/requests/${requestId}/accept`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
  });
  return resp.json();
}

export async function rejectContactRequest(
  requestId: string,
): Promise<ApiResult<ContactRequestItem>> {
  const resp = await fetch(`${API_BASE}/contacts/requests/${requestId}/reject`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
  });
  return resp.json();
}

export async function deleteContact(userId: string): Promise<void> {
  await fetch(`${API_BASE}/contacts/${userId}`, {
    method: "DELETE",
    headers: getWriteHeaders(),
    credentials: "include",
  });
}

/**
 * API client for CampusAgent.
 *
 * All requests use `credentials: 'include'` to send HttpOnly cookies.
 * Write requests (POST/PATCH/DELETE) automatically include the X-CSRF-Token
 * header via the csrf helper.
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

/** Register a new user. */
export async function register(payload: {
  email: string;
  password: string;
  display_name: string;
  student_no: string;
  phone_number?: string;
  organization_ids?: string[];
}): Promise<ApiResult<{ id: string; email: string; display_name: string; global_role: string }>> {
  const resp = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return resp.json();
}

/** Login a user. */
export async function login(payload: {
  email: string;
  password: string;
}): Promise<ApiResult<{ id: string; email: string; display_name: string; global_role: string }>> {
  const resp = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return resp.json();
}

/** Get current user info. */
export async function getMe(): Promise<ApiResult<{ id: string; email: string; display_name: string; global_role: string }>> {
  const resp = await fetch(`${API_BASE}/auth/me`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

/** Logout. */
export async function logout(): Promise<void> {
  await fetch(`${API_BASE}/auth/logout`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
  });
}

/** Refresh tokens. */
export async function refresh(): Promise<ApiResult<{ id: string; email: string; session_version: number }>> {
  const resp = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
  });
  return resp.json();
}

/** Update user profile. */
export async function updateProfile(
  userId: string,
  payload: { display_name?: string; bio?: string; avatar_url?: string }
): Promise<ApiResult<unknown>> {
  const resp = await fetch(`${API_BASE}/users/${userId}`, {
    method: "PATCH",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return resp.json();
}

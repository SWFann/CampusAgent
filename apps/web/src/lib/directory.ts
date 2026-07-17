/**
 * Directory API helpers for CampusAgent.
 *
 * All requests use `credentials: 'include'` to send HttpOnly cookies.
 * Read-only endpoints (search, tree, recommended) do not require CSRF.
 */

const API_ORIGIN = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
const API_BASE = `${API_ORIGIN}/api/v1`;

interface ApiResult<T> {
  success: boolean;
  data?: T;
  error?: { code: string; message: string; details?: Record<string, unknown> };
  request_id?: string;
}

export interface DirectoryUserResult {
  id: string;
  display_name: string;
  avatar_url?: string;
  profile_visibility: string;
}

export interface DirectoryOrganizationResult {
  id: string;
  name: string;
  type: string;
  visibility: string;
  status: string;
  member_count: number;
}

export interface DirectorySearchResponse {
  users: DirectoryUserResult[];
  organizations: DirectoryOrganizationResult[];
  total: number;
  query: string;
  search_type: string;
}

export interface DirectoryTreeNode {
  id: string;
  name: string;
  type: string;
  visibility: string;
  status: string;
  parent_id?: string;
  children: DirectoryTreeNode[];
}

export interface DirectoryTreeResponse {
  nodes: DirectoryTreeNode[];
  max_depth: number;
}

export interface DirectoryRecommendedItem {
  id: string;
  name: string;
  type: string;
  visibility: string;
  reason: string;
}

export interface DirectoryRecommendedResponse {
  recommendations: DirectoryRecommendedItem[];
  total: number;
}

/** Search the directory for users and/or organizations. */
export async function searchDirectory(
  query: string,
  type: string = "all",
  limit: number = 20,
  offset: number = 0
): Promise<ApiResult<DirectorySearchResponse>> {
  const params = new URLSearchParams({
    q: query,
    type,
    limit: String(limit),
    offset: String(offset),
  });
  const resp = await fetch(`${API_BASE}/directory/search?${params}`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

/** Get the organization tree. */
export async function getDirectoryTree(
  rootOrgId?: string,
  maxDepth: number = 3
): Promise<ApiResult<DirectoryTreeResponse>> {
  const params = new URLSearchParams({ max_depth: String(maxDepth) });
  if (rootOrgId) params.set("root_organization_id", rootOrgId);
  const resp = await fetch(`${API_BASE}/directory/tree?${params}`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

/** Get recommended organizations. */
export async function getRecommended(
  limit: number = 10
): Promise<ApiResult<DirectoryRecommendedResponse>> {
  const resp = await fetch(`${API_BASE}/directory/recommended?limit=${limit}`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

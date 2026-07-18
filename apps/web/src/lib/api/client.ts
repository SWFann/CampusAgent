/**
 * Unified API client for CampusAgent.
 *
 * All requests use `credentials: "include"` to send HttpOnly cookies.
 * Write requests (POST/PATCH/DELETE) automatically include the X-CSRF-Token
 * header via the csrf helper.
 *
 * The client parses the P2 API Envelope and throws `ApiClientError` for
 * non-success responses. Error objects never contain the original request
 * body or other sensitive fields.
 */

import { getCsrfToken } from "../csrf";
import type { ApiResponse, ApiErrorCode, ApiSuccess } from "./types";
import { ApiClientError } from "./types";

const API_ORIGIN = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
const API_BASE = `${API_ORIGIN}/api/v1`;

/** Sensitive field names that must never appear in error details. */
const SENSITIVE_FIELDS = [
  "password",
  "token",
  "refresh_token",
  "access_token",
  "api_key",
  "secret",
  "prompt",
  "notes",
  "preferences",
  "message_body",
  "memory_content",
];

/** Check if a string looks like it could be a sensitive field name. */
function isSensitiveField(key: string): boolean {
  const lower = key.toLowerCase();
  return SENSITIVE_FIELDS.some((s) => lower.includes(s));
}

/** Sanitize error details to remove any sensitive fields. */
export function sanitizeDetails(
  details: Record<string, unknown> | undefined,
): Record<string, unknown> | null {
  if (!details || typeof details !== "object") return null;
  const sanitized: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(details)) {
    if (isSensitiveField(key)) continue;
    if (typeof value === "string" && value.length > 200) {
      sanitized[key] = value.slice(0, 200) + "...";
    } else {
      sanitized[key] = value;
    }
  }
  return sanitized;
}

/** Map HTTP status code to stable error code. */
function statusToErrorCode(status: number): ApiErrorCode {
  switch (status) {
    case 401:
      return "UNAUTHORIZED";
    case 403:
      return "FORBIDDEN";
    case 404:
      return "NOT_FOUND";
    case 409:
      return "CONFLICT";
    case 422:
      return "VALIDATION_ERROR";
    case 429:
      return "RATE_LIMITED";
    case 500:
    case 502:
    case 503:
      return "INTERNAL_ERROR";
    default:
      return "UNKNOWN";
  }
}

/** Build headers for a GET request. */
function buildGetHeaders(): Record<string, string> {
  return { Accept: "application/json" };
}

/** Build headers for a write request (POST/PATCH/DELETE). */
function buildWriteHeaders(): Record<string, string> {
  const csrfToken = getCsrfToken();
  return {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
  };
}

/** Parse the API response and throw on error. */
async function parseResponse<T>(resp: Response): Promise<T> {
  const status = resp.status;

  // Handle non-JSON responses (e.g. 204 No Content).
  if (status === 204) {
    return undefined as T;
  }

  let body: ApiResponse<T>;
  try {
    body = (await resp.json()) as ApiResponse<T>;
  } catch {
    throw new ApiClientError(
      statusToErrorCode(status),
      "Received an invalid response from the server.",
      status,
      null,
    );
  }

  // Success envelope.
  if (body.success) {
    return (body as ApiSuccess<T>).data;
  }

  // Error envelope.
  const errorCode = body.error?.code ?? statusToErrorCode(status);
  const errorMessage = body.error?.message ?? "An unexpected error occurred.";
  const requestId = body.request_id ?? null;
  const details = sanitizeDetails(body.error?.details);

  throw new ApiClientError(
    errorCode as ApiErrorCode,
    errorMessage,
    status,
    requestId,
    details,
  );
}

/** Perform a GET request. */
export async function apiGet<T>(
  path: string,
  params?: Record<string, string | string[] | undefined>,
): Promise<T> {
  let url = `${API_BASE}${path}`;
  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined) continue;
      if (Array.isArray(value)) {
        for (const v of value) {
          searchParams.append(key, v);
        }
      } else {
        searchParams.set(key, value);
      }
    }
    const qs = searchParams.toString();
    if (qs) {
      url += `?${qs}`;
    }
  }

  const resp = await fetch(url, {
    method: "GET",
    headers: buildGetHeaders(),
    credentials: "include",
  });

  return parseResponse<T>(resp);
}

/** Perform a POST request. */
export async function apiPost<T>(
  path: string,
  body?: unknown,
): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: buildWriteHeaders(),
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  return parseResponse<T>(resp);
}

/** Perform a PATCH request. */
export async function apiPatch<T>(
  path: string,
  body?: unknown,
): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: buildWriteHeaders(),
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  return parseResponse<T>(resp);
}

/** Perform a DELETE request. */
export async function apiDelete<T = void>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: buildWriteHeaders(),
    credentials: "include",
  });

  return parseResponse<T>(resp);
}

/** Check if an error is an ApiClientError. */
export function isApiError(err: unknown): err is ApiClientError {
  if (err == null || typeof err !== "object") return false;
  const e = err as Record<string, unknown>;
  return e.name === "ApiClientError" || ("code" in e && "statusCode" in e);
}

/** Check if an error is an authentication error (401). */
export function isAuthError(err: unknown): boolean {
  return isApiError(err) && err.code === "UNAUTHORIZED";
}

/** Check if an error is a permission error (403). */
export function isForbiddenError(err: unknown): boolean {
  return isApiError(err) && err.code === "FORBIDDEN";
}

export { ApiClientError };
export type { ApiResponse, ApiErrorCode, ApiSuccess };

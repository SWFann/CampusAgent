/**
 * Shared API types for CampusAgent frontend.
 *
 * These types mirror the backend API envelope defined in P2.
 */

/** Success envelope returned by the API. */
export interface ApiSuccess<T> {
  success: true;
  data: T;
  request_id?: string;
}

/** Error envelope returned by the API. */
export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  request_id?: string;
}

/** Union type for all API responses. */
export type ApiResponse<T> = ApiSuccess<T> | ApiError;

/** Stable error codes used by the frontend. */
export type ApiErrorCode =
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "CONFLICT"
  | "VALIDATION_ERROR"
  | "RATE_LIMITED"
  | "INTERNAL_ERROR"
  | "UNKNOWN";

/** Typed error thrown by the API client. */
export class ApiClientError extends Error {
  readonly code: ApiErrorCode;
  readonly statusCode: number;
  readonly requestId: string | null;
  readonly details: Record<string, unknown> | null;

  constructor(
    code: ApiErrorCode,
    message: string,
    statusCode: number,
    requestId: string | null = null,
    details: Record<string, unknown> | null = null,
  ) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.statusCode = statusCode;
    this.requestId = requestId;
    this.details = details;
  }
}

/** User type returned by auth endpoints. */
export interface User {
  id: string;
  email: string;
  display_name: string;
  global_role: string;
  bio?: string;
  avatar_url?: string;
}

/** Organization summary. */
export interface OrganizationSummary {
  id: string;
  name: string;
  org_type: string;
  member_count?: number;
  role?: string;
}

/** Conversation summary. */
export interface ConversationSummary {
  id: string;
  title: string;
  conversation_type: string;
  last_message_preview?: string;
  last_message_at?: string;
  unread_count?: number;
}

/** Agent summary. */
export interface AgentSummary {
  id: string;
  name: string;
  agent_type: string;
  delegation_level: string;
  is_active: boolean;
}

/** Memory item summary. */
export interface MemorySummary {
  id: string;
  category: string;
  sensitivity_level: string;
  source: string;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

/** Scene summary. */
export interface SceneSummary {
  id: string;
  scene_key: string;
  status: string;
  title: string;
  participant_count: number;
  created_at: string;
}

/** Scene candidate. */
export interface SceneCandidate {
  candidate_key: string;
  display_name: string;
  public_metadata: Record<string, unknown>;
  rank: number;
  aggregate_score: number;
  public_reasons: string[];
}

/** Audit log entry (metadata only, no payload). */
export interface AuditLogEntry {
  id: string;
  actor_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  purpose: string | null;
  result: string;
  request_id: string | null;
  created_at: string;
}

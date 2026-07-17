/**
 * Conversations API helpers for CampusAgent.
 *
 * All requests use `credentials: 'include'` to send HttpOnly cookies.
 * Write requests (POST/PATCH/DELETE) include the X-CSRF-Token header.
 *
 * Privacy: No token, session, or private preference data is stored
 * or sent in any request body.
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

// ---------------------------------------------------------------------------
// Type definitions — aligned with backend schemas
// ---------------------------------------------------------------------------

export type ConversationType = "PRIVATE" | "GROUP" | "ORG_GROUP" | "SCENE";
export type ConversationStatus = "ACTIVE" | "ARCHIVED" | "DELETED";
export type ParticipantType = "USER" | "AGENT";
export type ConversationRole = "OWNER" | "ADMIN" | "MEMBER" | "GUEST";
export type ParticipantStatus = "ACTIVE" | "LEFT" | "REMOVED";
export type MessageType = "TEXT" | "IMAGE" | "FILE" | "SYSTEM" | "AGENT_PUBLIC" | "SCENE_CARD" | "VOTE" | "PROPOSAL" | "RESULT" | "PRIVACY_NOTICE";
export type MessageStatus = "ACTIVE" | "DELETED";
export type SenderType = "USER" | "AGENT" | "SYSTEM";

export interface Conversation {
  id: string;
  type: ConversationType;
  title: string | null;
  organization_id: string | null;
  created_by: string;
  status: ConversationStatus;
  created_at: string;
  updated_at: string;
}

export interface ConversationListItem {
  id: string;
  type: ConversationType;
  title: string | null;
  organization_id: string | null;
  status: ConversationStatus;
  last_message_at: string | null;
  participant_count: number;
}

export interface ConversationListResponse {
  conversations: ConversationListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface Participant {
  id: string;
  conversation_id: string;
  participant_type: ParticipantType;
  participant_user_id: string | null;
  display_name: string | null;
  avatar_url: string | null;
  role: ConversationRole;
  status: ParticipantStatus;
  joined_at: string;
  left_at: string | null;
}

export interface ParticipantListResponse {
  participants: Participant[];
  total: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_type: SenderType;
  sender_user_id: string | null;
  sender_agent_id: string | null;
  message_type: MessageType;
  content: string | null;
  status: MessageStatus;
  sequence: number;
  created_at: string;
  deleted_at: string | null;
}

export interface MessageListResponse {
  messages: Message[];
  total: number;
  page: number;
  page_size: number;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/** Create or reuse a private conversation with another user. */
export async function createPrivateConversation(
  targetUserId: string
): Promise<ApiResult<Conversation>> {
  const resp = await fetch(`${API_BASE}/conversations/private`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify({ target_user_id: targetUserId }),
  });
  return resp.json();
}

/** Create a group conversation. */
export async function createGroupConversation(payload: {
  title?: string;
  participant_user_ids?: string[];
  organization_id?: string;
}): Promise<ApiResult<Conversation>> {
  const resp = await fetch(`${API_BASE}/conversations`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return resp.json();
}

/** List conversations for the authenticated user. */
export async function listConversations(
  page: number = 1,
  pageSize: number = 20
): Promise<ApiResult<ConversationListResponse>> {
  const resp = await fetch(
    `${API_BASE}/conversations?page=${page}&page_size=${pageSize}`,
    { method: "GET", credentials: "include" }
  );
  return resp.json();
}

/** Get a single conversation by ID. */
export async function getConversation(
  conversationId: string
): Promise<ApiResult<Conversation>> {
  const resp = await fetch(`${API_BASE}/conversations/${conversationId}`, {
    method: "GET",
    credentials: "include",
  });
  return resp.json();
}

/** List participants in a conversation. */
export async function listParticipants(
  conversationId: string
): Promise<ApiResult<ParticipantListResponse>> {
  const resp = await fetch(
    `${API_BASE}/conversations/${conversationId}/participants`,
    { method: "GET", credentials: "include" }
  );
  return resp.json();
}

/** Add a participant to a conversation. */
export async function addParticipant(
  conversationId: string,
  userId: string,
  role: string = "MEMBER"
): Promise<ApiResult<Participant>> {
  const resp = await fetch(
    `${API_BASE}/conversations/${conversationId}/participants`,
    {
      method: "POST",
      headers: getWriteHeaders(),
      credentials: "include",
      body: JSON.stringify({ user_id: userId, role }),
    }
  );
  return resp.json();
}

/** Remove a participant from a conversation. */
export async function removeParticipant(
  conversationId: string,
  userId: string
): Promise<void> {
  await fetch(
    `${API_BASE}/conversations/${conversationId}/participants/${userId}`,
    {
      method: "DELETE",
      headers: getWriteHeaders(),
      credentials: "include",
    }
  );
}

/** Send a message to a conversation. */
export async function sendMessage(
  conversationId: string,
  payload: {
    content: string;
    message_type?: string;
    idempotency_key?: string;
  }
): Promise<ApiResult<Message>> {
  const resp = await fetch(
    `${API_BASE}/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: getWriteHeaders(),
      credentials: "include",
      body: JSON.stringify(payload),
    }
  );
  return resp.json();
}

/** List messages in a conversation with pagination. */
export async function listMessages(
  conversationId: string,
  page: number = 1,
  pageSize: number = 50
): Promise<ApiResult<MessageListResponse>> {
  const resp = await fetch(
    `${API_BASE}/conversations/${conversationId}/messages?page=${page}&page_size=${pageSize}`,
    { method: "GET", credentials: "include" }
  );
  return resp.json();
}

/** Soft-delete a message. */
export async function deleteMessage(
  conversationId: string,
  messageId: string
): Promise<void> {
  await fetch(
    `${API_BASE}/conversations/${conversationId}/messages/${messageId}`,
    {
      method: "DELETE",
      headers: getWriteHeaders(),
      credentials: "include",
    }
  );
}

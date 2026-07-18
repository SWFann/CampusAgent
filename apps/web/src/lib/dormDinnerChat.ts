import { getWriteHeaders } from "./csrf";

const API_ORIGIN = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
const API_BASE = `${API_ORIGIN}/api/v1`;

interface ApiResult<T> {
  success: boolean;
  data?: T;
  error?: { code: string; message: string; details?: Record<string, unknown> };
  request_id?: string;
}

export interface DormDinnerCandidate {
  id: string;
  candidate_key: string;
  display_name: string;
  aggregate_score: number;
  public_reason: string | null;
  rank: number | null;
  public_metadata?: {
    address?: string;
    price_hint?: string;
    business_hours_hint?: string;
    risk_notice?: string;
    sources?: Array<{ title: string; url: string; retrieved_at: string }>;
  } | null;
}

export interface DormDinnerDebateTurn {
  round: number;
  speaker: string;
  content: string;
  search_summary?: string;
  source_urls?: string[];
}

export interface DormDinnerChatStatus {
  scene_id: string | null;
  conversation_id: string;
  phase: string;
  status: string;
  participant_count: number;
  joined_count: number;
  skipped_count: number;
  submitted_count: number;
  ready_for_debate: boolean;
  my_participation: string | null;
  my_submitted: boolean;
  max_rounds: number;
  current_round: number;
  debate_turns: DormDinnerDebateTurn[];
  candidates: DormDinnerCandidate[];
  votes: Array<{ candidate_id: string; user_id: string; vote_value: string }>;
  result: { selected_candidate_id: string | null; public_summary: string | null } | null;
  scene_version: number;
  city: string;
  origin: string;
  topic: string;
  vote_deadline: string | null;
  negotiations: Array<{ number: number; round_count: number; coordinator_summary: string }>;
  public_error: string | null;
  next_negotiation_requests: number;
  display_mode: "anonymous" | "named";
  capabilities: { can_manage: boolean; can_start_debate: boolean; can_close: boolean };
}

async function parseJson<T>(resp: Response): Promise<ApiResult<T>> {
  return resp.json();
}

export async function getDormDinnerChatStatus(
  conversationId: string,
): Promise<ApiResult<DormDinnerChatStatus>> {
  const resp = await fetch(`${API_BASE}/scenes/conversations/${conversationId}/dorm_dinner`, {
    credentials: "include",
  });
  return parseJson(resp);
}

export async function startDormDinnerChat(
  conversationId: string,
  input: { maxRounds: number; city: string; origin: string; topic: string; voteDeadline?: string },
): Promise<ApiResult<DormDinnerChatStatus>> {
  const resp = await fetch(`${API_BASE}/scenes/conversations/${conversationId}/dorm_dinner`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify({
      max_rounds: input.maxRounds,
      city: input.city,
      origin: input.origin,
      topic: input.topic,
      vote_deadline: input.voteDeadline || null,
    }),
  });
  return parseJson(resp);
}

export async function closeDormDinnerVote(conversationId: string): Promise<ApiResult<DormDinnerChatStatus>> {
  const resp = await fetch(`${API_BASE}/scenes/conversations/${conversationId}/dorm_dinner/votes/close`, {
    method: "POST", headers: getWriteHeaders(), credentials: "include",
  });
  return parseJson(resp);
}

export async function requestNextDormDinnerNegotiation(conversationId: string): Promise<ApiResult<DormDinnerChatStatus>> {
  const resp = await fetch(`${API_BASE}/scenes/conversations/${conversationId}/dorm_dinner/next-negotiation`, {
    method: "POST", headers: getWriteHeaders(), credentials: "include",
  });
  return parseJson(resp);
}

export async function endDormDinner(conversationId: string): Promise<ApiResult<DormDinnerChatStatus>> {
  const resp = await fetch(`${API_BASE}/scenes/conversations/${conversationId}/dorm_dinner/end`, {
    method: "POST", headers: getWriteHeaders(), credentials: "include",
  });
  return parseJson(resp);
}

export async function setDormDinnerParticipation(
  conversationId: string,
  participate: boolean,
): Promise<ApiResult<DormDinnerChatStatus>> {
  const resp = await fetch(`${API_BASE}/scenes/conversations/${conversationId}/dorm_dinner/participation`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify({ participate }),
  });
  return parseJson(resp);
}

export async function submitDormDinnerPreferences(
  conversationId: string,
  preferences: Record<string, unknown>,
): Promise<ApiResult<DormDinnerChatStatus>> {
  const resp = await fetch(`${API_BASE}/scenes/conversations/${conversationId}/dorm_dinner/preferences`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify({ preferences }),
  });
  return parseJson(resp);
}

export async function startDormDinnerDebate(
  conversationId: string,
  maxRounds: number,
): Promise<ApiResult<DormDinnerChatStatus>> {
  const resp = await fetch(`${API_BASE}/scenes/conversations/${conversationId}/dorm_dinner/debate/start`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify({ max_rounds: maxRounds }),
  });
  return parseJson(resp);
}

export async function voteDormDinnerCandidate(
  conversationId: string,
  candidateKey: string,
): Promise<ApiResult<DormDinnerChatStatus>> {
  const resp = await fetch(`${API_BASE}/scenes/conversations/${conversationId}/dorm_dinner/votes`, {
    method: "POST",
    headers: getWriteHeaders(),
    credentials: "include",
    body: JSON.stringify({ candidate_key: candidateKey }),
  });
  return parseJson(resp);
}

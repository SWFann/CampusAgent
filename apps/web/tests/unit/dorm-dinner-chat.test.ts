import {
  canActOnDormDinner,
  isDormDinnerClosed,
  type DormDinnerChatStatus,
} from "@/lib/dormDinnerChat";

function status(overrides: Partial<DormDinnerChatStatus>): DormDinnerChatStatus {
  return {
    scene_id: "scene-1",
    conversation_id: "conversation-1",
    phase: "VOTING",
    status: "VOTING",
    participant_count: 3,
    joined_count: 2,
    skipped_count: 0,
    submitted_count: 2,
    ready_for_debate: true,
    my_participation: "ACCEPTED",
    my_submitted: true,
    max_rounds: 3,
    current_round: 3,
    debate_turns: [],
    candidates: [],
    votes: [],
    result: null,
    scene_version: 1,
    city: "广州",
    origin: "暨南大学",
    topic: "宿舍聚餐",
    vote_deadline: null,
    negotiations: [],
    public_error: null,
    next_negotiation_requests: 0,
    display_mode: "anonymous",
    capabilities: { can_manage: true, can_start_debate: true, can_close: true },
    ...overrides,
  };
}

describe("dorm dinner chat state helpers", () => {
  it("treats closed and completed scenes as closed", () => {
    expect(isDormDinnerClosed(status({ status: "VOTING_CLOSED", phase: "VOTING_CLOSED" }))).toBe(true);
    expect(isDormDinnerClosed(status({ status: "COMPLETED", phase: "COMPLETED" }))).toBe(true);
  });

  it("disables active controls once voting is closed", () => {
    expect(canActOnDormDinner(status({ status: "VOTING_CLOSED", phase: "VOTING_CLOSED" }))).toBe(false);
  });
});

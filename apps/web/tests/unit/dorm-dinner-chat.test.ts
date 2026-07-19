import {
  canActOnDormDinner,
  groupDormDinnerDebateTurns,
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

  it("groups hosted multi-agent debate transcript by phase and round", () => {
    const grouped = groupDormDinnerDebateTurns([
      { phase: "opening", round: 0, speaker: "主持人Agent", content: "开场" },
      {
        phase: "proposal",
        round: 0,
        speaker: "Alice Agent",
        content: "提案",
        proposals: [{ display_name: "校外川菜馆", candidate_key: "sichuan" }],
      },
      { phase: "debate", round: 1, speaker: "Alice Agent", content: "支持川菜馆" },
      { phase: "debate", round: 1, speaker: "Bob Agent", content: "提醒距离" },
      { phase: "host_summary", round: 1, speaker: "主持人Agent", content: "本轮小结" },
      { phase: "coordinator_summary", round: 2, speaker: "最终协调Agent", content: "最终汇总" },
    ]);

    expect(grouped.opening?.content).toBe("开场");
    expect(grouped.proposals[0].proposals?.[0].display_name).toBe("校外川菜馆");
    expect(grouped.rounds[0].round).toBe(1);
    expect(grouped.rounds[0].turns).toHaveLength(2);
    expect(grouped.rounds[0].hostSummary?.content).toBe("本轮小结");
    expect(grouped.coordinatorSummary?.speaker).toBe("最终协调Agent");
  });
});

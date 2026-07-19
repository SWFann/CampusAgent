# Dorm Dinner Multi-Agent Debate Design

## Goal

Turn the dorm dinner vote from a one-shot recommendation summary into a visible hosted multi-agent debate for demo reporting.

The demo version intentionally shows each participant agent's preference reasoning and debate process. It does not hide private preferences in the debate transcript.

## User Experience

When the initiator starts intelligent debate:

1. A host agent opens the debate and states the topic, participant agents, and round count.
2. Each participant agent searches from its own preference angle and proposes multiple restaurant candidates with source URLs.
3. Participant agents debate for the configured number of rounds, up to 10.
4. In each round, agents support, challenge, or revise restaurant options.
5. The host agent gives a short round summary.
6. A final coordinator agent synthesizes the transcript and produces the final candidate cards for voting.

The chat and the vote modal both show the transcript. The modal shows a detailed debate area grouped by round and speaker.

## Backend Design

`StepFunDinnerProvider.negotiate` will request a structured debate transcript instead of only flat agent summaries.

The JSON result will include:

- `opening`: host opening statement.
- `agent_proposals`: each participant agent's searched proposals.
- `rounds`: debate rounds with speaker turns and host summaries.
- `coordinator_summary`: final synthesis.
- `candidates`: grounded final vote candidates.

Every final candidate must still reference at least one URL from real search evidence. Search evidence remains the anti-fake-recommendation boundary.

`chat_dorm_dinner.run_debate` will persist the transcript in `public_context_json.debate_turns` and publish public chat messages for:

- host opening,
- participant proposals,
- debate turns,
- host round summaries,
- final coordinator summary.

For this demo version, raw preference capsules may be included in the model prompt and visible transcript. Secrets such as API keys, auth tokens, passwords, and system configuration must never be shown.

## Search Strategy

The provider will still call StepFun search, but the prompt will require the model to assign evidence to each agent proposal. To avoid only selecting campus canteens, the search query should include nearby restaurants and student gathering language, not only campus/internal dining.

The model may only recommend restaurants supported by returned evidence URLs. If evidence is weak, the UI should show an explicit risk notice instead of inventing details.

## Frontend Design

The dorm dinner modal will add a more detailed debate transcript view:

- proposal phase,
- debate rounds,
- host summaries,
- final coordinator summary.

Existing compact text remains acceptable in chat messages, but the modal should make the roles and rounds easy to scan.

## Error Handling

If StepFun search fails, show a search-specific error.

If StepFun chat completion fails or returns invalid JSON, show a model-summary-specific error.

If the model returns candidates without source URLs from evidence, reject those candidates and show a groundedness error.

## Tests

Add or update tests for:

- parser accepts structured debate output,
- final candidates must still cite evidence URLs,
- chat debate status exposes hosted debate turns,
- frontend type helpers can represent proposal, debate, host summary, and coordinator summary turns.

## Out of Scope

This design does not implement token-by-token streaming. It implements round-level visible debate messages and modal transcript rendering.

This design does not add a background job system. The initiator request can remain synchronous for now, guarded by the existing 60-second timeout.

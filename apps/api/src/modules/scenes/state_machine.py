"""Scene state machine — frozen transitions per SCENE_STATE_MACHINE.md.

Legal flow:
    DRAFT → INVITING → COLLECTING_PRIVATE_INPUT → GENERATING_CANDIDATES
          → VOTING → CONFIRMING → COMPLETED

Terminal flows:
    * → CANCELLED
    * → EXPIRED
    * → FAILED

Privacy: the state machine never carries private payload data.
"""
from __future__ import annotations

from enum import StrEnum
from typing import NamedTuple


class SceneState(StrEnum):
    DRAFT = "DRAFT"
    INVITING = "INVITING"
    COLLECTING_PRIVATE_INPUT = "COLLECTING_PRIVATE_INPUT"
    GENERATING_CANDIDATES = "GENERATING_CANDIDATES"
    VOTING = "VOTING"
    CONFIRMING = "CONFIRMING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class Transition(NamedTuple):
    """A legal state transition."""

    from_state: SceneState
    to_state: SceneState
    action: str


# All legal transitions (from SCENE_STATE_MACHINE.md §3.1).
LEGAL_TRANSITIONS: frozenset[Transition] = frozenset(
    {
        # Normal flow
        Transition(SceneState.DRAFT, SceneState.INVITING, "publish"),
        Transition(SceneState.INVITING, SceneState.COLLECTING_PRIVATE_INPUT, "start_collecting"),
        Transition(
            SceneState.COLLECTING_PRIVATE_INPUT,
            SceneState.GENERATING_CANDIDATES,
            "start_processing",
        ),
        Transition(
            SceneState.GENERATING_CANDIDATES, SceneState.VOTING, "candidates_ready"
        ),
        Transition(SceneState.VOTING, SceneState.CONFIRMING, "voting_complete"),
        Transition(SceneState.CONFIRMING, SceneState.COMPLETED, "confirm"),
        # Cancel from any non-terminal state
        Transition(SceneState.DRAFT, SceneState.CANCELLED, "cancel"),
        Transition(SceneState.INVITING, SceneState.CANCELLED, "cancel"),
        Transition(
            SceneState.COLLECTING_PRIVATE_INPUT, SceneState.CANCELLED, "cancel"
        ),
        Transition(SceneState.GENERATING_CANDIDATES, SceneState.CANCELLED, "cancel"),
        Transition(SceneState.VOTING, SceneState.CANCELLED, "cancel"),
        Transition(SceneState.CONFIRMING, SceneState.CANCELLED, "cancel"),
        # Fail from processing
        Transition(
            SceneState.GENERATING_CANDIDATES, SceneState.FAILED, "processing_failed"
        ),
        # Expire from any non-terminal state
        Transition(SceneState.DRAFT, SceneState.EXPIRED, "expire"),
        Transition(SceneState.INVITING, SceneState.EXPIRED, "expire"),
        Transition(
            SceneState.COLLECTING_PRIVATE_INPUT, SceneState.EXPIRED, "expire"
        ),
        Transition(SceneState.GENERATING_CANDIDATES, SceneState.EXPIRED, "expire"),
        Transition(SceneState.VOTING, SceneState.EXPIRED, "expire"),
        Transition(SceneState.CONFIRMING, SceneState.EXPIRED, "expire"),
    }
)

TERMINAL_STATES: frozenset[SceneState] = frozenset(
    {SceneState.COMPLETED, SceneState.CANCELLED, SceneState.EXPIRED, SceneState.FAILED}
)


class SceneStateMachine:
    """Static state machine — checks transition legality without carrying data."""

    @classmethod
    def can_transition(cls, from_state: SceneState, to_state: SceneState) -> bool:
        """Check whether a transition is legal."""
        if from_state in TERMINAL_STATES:
            return False
        return any(
            t.from_state == from_state and t.to_state == to_state
            for t in LEGAL_TRANSITIONS
        )

    @classmethod
    def can_action(cls, from_state: SceneState, action: str) -> bool:
        """Check whether an action is legal from a given state."""
        if from_state in TERMINAL_STATES:
            return False
        return any(
            t.from_state == from_state and t.action == action
            for t in LEGAL_TRANSITIONS
        )

    @classmethod
    def get_target_state(
        cls, from_state: SceneState, action: str
    ) -> SceneState | None:
        """Return the target state for an action, or None if illegal."""
        if from_state in TERMINAL_STATES:
            return None
        for t in LEGAL_TRANSITIONS:
            if t.from_state == from_state and t.action == action:
                return t.to_state
        return None

    @classmethod
    def is_terminal(cls, state: SceneState) -> bool:
        """Check if a state is terminal (no further transitions)."""
        return state in TERMINAL_STATES

    @classmethod
    def is_active(cls, state: SceneState) -> bool:
        """Check if a state is active (non-terminal)."""
        return state not in TERMINAL_STATES

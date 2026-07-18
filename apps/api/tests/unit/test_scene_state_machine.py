"""P8-05: Scene state machine tests.

Tests:
- Legal forward transitions succeed.
- Illegal transitions fail.
- Terminal states cannot transition.
- Cancel/expire from any non-terminal state.
- Action-based lookup works.
"""
from __future__ import annotations

from src.modules.scenes.state_machine import (
    LEGAL_TRANSITIONS,
    TERMINAL_STATES,
    SceneState,
    SceneStateMachine,
)


class TestSceneStateMachine:
    """Test the scene state machine."""

    def test_legal_forward_transitions(self) -> None:
        """The normal flow DRAFT → ... → COMPLETED must be legal."""
        assert SceneStateMachine.can_transition(
            SceneState.DRAFT, SceneState.INVITING
        )
        assert SceneStateMachine.can_transition(
            SceneState.INVITING, SceneState.COLLECTING_PRIVATE_INPUT
        )
        assert SceneStateMachine.can_transition(
            SceneState.COLLECTING_PRIVATE_INPUT, SceneState.GENERATING_CANDIDATES
        )
        assert SceneStateMachine.can_transition(
            SceneState.GENERATING_CANDIDATES, SceneState.VOTING
        )
        assert SceneStateMachine.can_transition(
            SceneState.VOTING, SceneState.CONFIRMING
        )
        assert SceneStateMachine.can_transition(
            SceneState.CONFIRMING, SceneState.COMPLETED
        )

    def test_illegal_skip_transitions(self) -> None:
        """Skipping a state must be illegal."""
        assert not SceneStateMachine.can_transition(
            SceneState.DRAFT, SceneState.VOTING
        )
        assert not SceneStateMachine.can_transition(
            SceneState.DRAFT, SceneState.COMPLETED
        )
        assert not SceneStateMachine.can_transition(
            SceneState.INVITING, SceneState.VOTING
        )
        assert not SceneStateMachine.can_transition(
            SceneState.COLLECTING_PRIVATE_INPUT, SceneState.CONFIRMING
        )

    def test_terminal_states_cannot_transition(self) -> None:
        """Terminal states cannot transition to anything."""
        for state in TERMINAL_STATES:
            for target in SceneState:
                assert not SceneStateMachine.can_transition(state, target), (
                    f"{state.value} should not transition to {target.value}"
                )

    def test_cancel_from_any_non_terminal(self) -> None:
        """Cancel must be legal from every non-terminal state."""
        non_terminal = set(SceneState) - TERMINAL_STATES
        for state in non_terminal:
            assert SceneStateMachine.can_action(state, "cancel"), (
                f"cancel should be legal from {state.value}"
            )

    def test_expire_from_any_non_terminal(self) -> None:
        """Expire must be legal from every non-terminal state."""
        non_terminal = set(SceneState) - TERMINAL_STATES
        for state in non_terminal:
            assert SceneStateMachine.can_action(state, "expire"), (
                f"expire should be legal from {state.value}"
            )

    def test_get_target_state(self) -> None:
        """get_target_state returns the correct target for an action."""
        assert (
            SceneStateMachine.get_target_state(SceneState.DRAFT, "publish")
            == SceneState.INVITING
        )
        assert (
            SceneStateMachine.get_target_state(SceneState.DRAFT, "cancel")
            == SceneState.CANCELLED
        )
        assert (
            SceneStateMachine.get_target_state(SceneState.COMPLETED, "publish")
            is None
        )

    def test_get_target_state_illegal(self) -> None:
        """get_target_state returns None for illegal actions."""
        assert (
            SceneStateMachine.get_target_state(SceneState.DRAFT, "confirm")
            is None
        )
        assert (
            SceneStateMachine.get_target_state(SceneState.VOTING, "publish")
            is None
        )

    def test_is_terminal(self) -> None:
        """is_terminal correctly identifies terminal states."""
        assert SceneStateMachine.is_terminal(SceneState.COMPLETED)
        assert SceneStateMachine.is_terminal(SceneState.CANCELLED)
        assert SceneStateMachine.is_terminal(SceneState.EXPIRED)
        assert SceneStateMachine.is_terminal(SceneState.FAILED)
        assert not SceneStateMachine.is_terminal(SceneState.DRAFT)
        assert not SceneStateMachine.is_terminal(SceneState.VOTING)

    def test_is_active(self) -> None:
        """is_active correctly identifies non-terminal states."""
        assert SceneStateMachine.is_active(SceneState.DRAFT)
        assert SceneStateMachine.is_active(SceneState.VOTING)
        assert not SceneStateMachine.is_active(SceneState.COMPLETED)
        assert not SceneStateMachine.is_active(SceneState.CANCELLED)

    def test_all_transitions_have_valid_states(self) -> None:
        """Every transition in LEGAL_TRANSITIONS uses valid SceneState values."""
        for t in LEGAL_TRANSITIONS:
            assert isinstance(t.from_state, SceneState)
            assert isinstance(t.to_state, SceneState)
            assert t.action  # action must be non-empty

    def test_fail_only_from_generating(self) -> None:
        """FAILED is only reachable from GENERATING_CANDIDATES."""
        non_terminal = set(SceneState) - TERMINAL_STATES - {SceneState.GENERATING_CANDIDATES}
        for state in non_terminal:
            assert not SceneStateMachine.can_transition(state, SceneState.FAILED), (
                f"FAILED should not be reachable from {state.value}"
            )
        assert SceneStateMachine.can_transition(
            SceneState.GENERATING_CANDIDATES, SceneState.FAILED
        )

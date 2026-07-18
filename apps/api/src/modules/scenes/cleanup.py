"""Scene Cleanup Service — purges private data after scene completion.

Requirements (P8 guide §16):
- Immediate cleanup: called by the coordinator after generation completes.
- 24h fallback: a periodic job cleans up expired submissions.
- Repeated execution is safe (idempotent).
- After cleanup, the API cannot read private payloads.

Privacy:
- Cleanup clears encrypted_payload, capsule_json, and sets deleted_at.
- The cleanup event only carries counts — never private data.
"""
from __future__ import annotations

import logging
import secrets
from uuid import UUID

from sqlalchemy.orm import Session

from ...db.time import utc_now
from ...events.bus import default_event_bus
from .events import ScenePrivateDataCleaned
from .plugin_protocol import SceneServiceFacade
from .registry import get_scene_registry
from .repository import PrivateSubmissionRepository, SceneInstanceRepository

logger = logging.getLogger("campus_agent.scenes.cleanup")


def _generate_event_id() -> str:
    return secrets.token_hex(16)


def cleanup_private_data(
    instance_id: UUID,
    session: Session,
    *,
    facade: SceneServiceFacade | None = None,
) -> int:
    """Immediately purge all private submission data for a scene instance.

    This is called by the coordinator after candidate generation, and
    also by the cancel/expire/fail handlers.

    Args:
        instance_id: The scene instance to clean up.
        session: DB session.
        facade: Optional facade for plugin-specific cleanup.

    Returns:
        Number of submissions purged.
    """
    sub_repo = PrivateSubmissionRepository(session)
    count = sub_repo.hard_delete_payload(instance_id)
    session.commit()

    # Publish cleanup event (only count, no private data).
    default_event_bus.publish(
        ScenePrivateDataCleaned(
            event_id=_generate_event_id(),
            scene_instance_id=instance_id,
            submission_count=count,
            occurred_at=utc_now(),
        )
    )

    logger.info(
        "scene.cleanup.private_data",
        extra={"instance_id": str(instance_id), "purged_count": count},
    )

    # Call plugin-specific cleanup if facade is available.
    if facade is not None:
        try:
            instance_repo = SceneInstanceRepository(session)
            instance = instance_repo.get_by_id(instance_id)
            if instance is not None:
                registry = get_scene_registry()
                plugin = registry.get(
                    instance.definition.scene_key,
                    instance.definition.version,
                )
                plugin.cleanup_private_data(instance_id, facade)
        except Exception as exc:
            logger.warning(
                "scene.cleanup.plugin_specific_failed",
                extra={"instance_id": str(instance_id), "error": str(exc)},
            )

    return count


def cleanup_expired_submissions(session: Session, *, limit: int = 100) -> int:
    """Periodic cleanup of expired private submissions (24h fallback).

    This is a safety net — the coordinator should have already cleaned
    up submissions after generation. This catches any that were missed
    due to crashes or timeouts.

    Returns:
        Total number of submissions purged.
    """
    sub_repo = PrivateSubmissionRepository(session)
    expired = sub_repo.list_expired(limit=limit)

    total = 0
    for submission in expired:
        submission.encrypted_payload = ""
        submission.capsule_json = None
        submission.deleted_at = utc_now()
        total += 1

    if total > 0:
        session.commit()
        logger.info(
            "scene.cleanup.expired_submissions",
            extra={"purged_count": total},
        )

    return total


def cleanup_instance_on_terminal(
    instance_id: UUID,
    session: Session,
    *,
    facade: SceneServiceFacade | None = None,
) -> int:
    """Cleanup private data when a scene reaches a terminal state.

    Called when a scene is cancelled, expired, or failed — ensures no
    private data lingers after the scene is no longer active.
    """
    return cleanup_private_data(instance_id, session, facade=facade)

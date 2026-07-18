"""Contact service layer."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ...db.time import utc_now
from ...utils.errors import AppError, NotFoundError
from ..users.models import User, UserStatus
from .models import ContactRelationship, ContactStatus


def _user_read(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
    }


def _relationship_read(rel: ContactRelationship, actor: User, session: Session) -> dict[str, Any]:
    other_id = rel.addressee_id if rel.requester_id == actor.id else rel.requester_id
    other = session.get(User, other_id)
    if other is None:
        raise NotFoundError("User")
    return {
        "user": _user_read(other),
        "relationship_id": str(rel.id),
        "status": rel.status,
        "requested_at": rel.requested_at.isoformat(),
        "responded_at": rel.responded_at.isoformat() if rel.responded_at else None,
    }


def _request_read(rel: ContactRelationship, session: Session) -> dict[str, Any]:
    requester = session.get(User, rel.requester_id)
    addressee = session.get(User, rel.addressee_id)
    if requester is None or addressee is None:
        raise NotFoundError("User")
    return {
        "id": str(rel.id),
        "requester": _user_read(requester),
        "addressee": _user_read(addressee),
        "status": rel.status,
        "requested_at": rel.requested_at.isoformat(),
    }


def _find_between(user_a: UUID, user_b: UUID, session: Session) -> ContactRelationship | None:
    return (
        session.query(ContactRelationship)
        .filter(
            or_(
                (ContactRelationship.requester_id == user_a)
                & (ContactRelationship.addressee_id == user_b),
                (ContactRelationship.requester_id == user_b)
                & (ContactRelationship.addressee_id == user_a),
            )
        )
        .first()
    )


def list_contacts(actor: User, session: Session) -> dict[str, Any]:
    relationships = (
        session.query(ContactRelationship)
        .filter(
            ContactRelationship.status == ContactStatus.ACCEPTED.value,
            ContactRelationship.deleted_at.is_(None),
            or_(
                ContactRelationship.requester_id == actor.id,
                ContactRelationship.addressee_id == actor.id,
            ),
        )
        .order_by(ContactRelationship.responded_at.desc().nullslast())
        .all()
    )
    contacts = [_relationship_read(rel, actor, session) for rel in relationships]
    return {"contacts": contacts, "total": len(contacts)}


def list_contact_requests(actor: User, session: Session) -> dict[str, Any]:
    incoming = (
        session.query(ContactRelationship)
        .filter(
            ContactRelationship.addressee_id == actor.id,
            ContactRelationship.status == ContactStatus.PENDING.value,
            ContactRelationship.deleted_at.is_(None),
        )
        .order_by(ContactRelationship.requested_at.desc())
        .all()
    )
    outgoing = (
        session.query(ContactRelationship)
        .filter(
            ContactRelationship.requester_id == actor.id,
            ContactRelationship.status == ContactStatus.PENDING.value,
            ContactRelationship.deleted_at.is_(None),
        )
        .order_by(ContactRelationship.requested_at.desc())
        .all()
    )
    return {
        "incoming": [_request_read(rel, session) for rel in incoming],
        "outgoing": [_request_read(rel, session) for rel in outgoing],
    }


def create_contact_request(actor: User, target_user_id: UUID, session: Session) -> dict[str, Any]:
    if target_user_id == actor.id:
        raise AppError(
            code="CONTACT_SELF_NOT_ALLOWED",
            message="不能添加自己为好友",
            status_code=400,
        )

    target = session.get(User, target_user_id)
    if target is None or target.status != UserStatus.ACTIVE.value:
        raise NotFoundError("User")

    existing = _find_between(actor.id, target_user_id, session)
    if existing is not None:
        if existing.status in {ContactStatus.DELETED.value, ContactStatus.REJECTED.value}:
            existing.requester_id = actor.id
            existing.addressee_id = target_user_id
            existing.status = ContactStatus.PENDING.value
            existing.requested_at = utc_now()
            existing.responded_at = None
            existing.deleted_at = None
        else:
            session.commit()
            return _request_read(existing, session)
        session.commit()
        session.refresh(existing)
        return _request_read(existing, session)

    relationship = ContactRelationship(
        requester_id=actor.id,
        addressee_id=target_user_id,
        status=ContactStatus.PENDING.value,
    )
    session.add(relationship)
    session.commit()
    session.refresh(relationship)
    return _request_read(relationship, session)


def accept_contact_request(actor: User, request_id: UUID, session: Session) -> dict[str, Any]:
    relationship = session.get(ContactRelationship, request_id)
    if relationship is None or relationship.addressee_id != actor.id:
        raise NotFoundError("Contact request")
    if relationship.status != ContactStatus.PENDING.value:
        return _request_read(relationship, session)
    relationship.status = ContactStatus.ACCEPTED.value
    relationship.responded_at = utc_now()
    session.commit()
    session.refresh(relationship)
    return _request_read(relationship, session)


def reject_contact_request(actor: User, request_id: UUID, session: Session) -> dict[str, Any]:
    relationship = session.get(ContactRelationship, request_id)
    if relationship is None or relationship.addressee_id != actor.id:
        raise NotFoundError("Contact request")
    if relationship.status == ContactStatus.PENDING.value:
        relationship.status = ContactStatus.REJECTED.value
        relationship.responded_at = utc_now()
        session.commit()
        session.refresh(relationship)
    return _request_read(relationship, session)


def delete_contact(actor: User, user_id: UUID, session: Session) -> None:
    relationship = _find_between(actor.id, user_id, session)
    if relationship is None or relationship.status != ContactStatus.ACCEPTED.value:
        raise NotFoundError("Contact")
    relationship.status = ContactStatus.DELETED.value
    relationship.deleted_at = utc_now()
    session.commit()

"""
Declarative base for SQLAlchemy ORM models.

All future business models should inherit from ``Base``.
P2-03 does NOT create any business tables — this base is prepared
for P2-04 (Alembic) and subsequent feature modules.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all CampusAgent ORM models."""

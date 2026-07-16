"""Tests for BaseRepository and UnitOfWork (P2-11)."""

from __future__ import annotations

import pytest
from sqlalchemy import Column, String, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.base import Base
from src.db.repositories import BaseRepository, UnitOfWork
from src.events.bus import DomainEvent, EventBus


class _TestModel(Base):
    __tablename__ = "test_p2_11_model"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)


class _TestEvent(DomainEvent):
    def __init__(self, msg: str) -> None:
        self.msg = msg


class _CaptureHandler:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def handle(self, event: DomainEvent) -> None:
        self.events.append(event)


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


class TestBaseRepository:
    def test_add_and_get(self, session_factory) -> None:
        with session_factory() as session:
            repo = BaseRepository(session, _TestModel)
            entity = _TestModel(id="u1", name="Alice")
            repo.add(entity)
            session.commit()
            session.expunge_all()

            fetched = repo.get_by_id("u1")
            assert fetched is not None
            assert fetched.name == "Alice"

    def test_list(self, session_factory) -> None:
        with session_factory() as session:
            repo = BaseRepository(session, _TestModel)
            repo.add(_TestModel(id="u1", name="A"))
            repo.add(_TestModel(id="u2", name="B"))
            session.commit()
            session.expunge_all()

            items = repo.list()
            assert len(items) == 2

    def test_delete(self, session_factory) -> None:
        with session_factory() as session:
            repo = BaseRepository(session, _TestModel)
            entity = _TestModel(id="u1", name="Alice")
            repo.add(entity)
            session.commit()
            session.expunge_all()

            fetched = repo.get_by_id("u1")
            assert fetched is not None
            repo.delete(fetched)
            session.commit()
            session.expunge_all()

            assert repo.get_by_id("u1") is None


class TestUnitOfWork:
    def test_commit_on_success(self, session_factory) -> None:
        bus = EventBus()
        handler = _CaptureHandler()
        bus.subscribe(_TestEvent, handler)

        with UnitOfWork(session_factory, bus) as uow:
            session = uow.session
            repo = BaseRepository(session, _TestModel)
            repo.add(_TestModel(id="u1", name="Alice"))
            uow.add_event(_TestEvent("created"))

        # Event was published after commit
        assert len(handler.events) == 1

        with session_factory() as session:
            repo = BaseRepository(session, _TestModel)
            assert repo.get_by_id("u1") is not None

    def test_rollback_on_exception(self, session_factory) -> None:
        bus = EventBus()
        handler = _CaptureHandler()
        bus.subscribe(_TestEvent, handler)

        with pytest.raises(ValueError, match="test error"), \
                UnitOfWork(session_factory, bus) as uow:
            session = uow.session
            repo = BaseRepository(session, _TestModel)
            repo.add(_TestModel(id="u1", name="Alice"))
            uow.add_event(_TestEvent("should-not-publish"))
            raise ValueError("test error")

        # Event NOT published because of rollback
        assert len(handler.events) == 0

        with session_factory() as session:
            repo = BaseRepository(session, _TestModel)
            assert repo.get_by_id("u1") is None

    def test_session_raises_outside_context(self, session_factory) -> None:
        uow = UnitOfWork(session_factory)
        with pytest.raises(RuntimeError, match="not initialised"):
            _ = uow.session

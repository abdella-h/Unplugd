import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import FastAPI

os.environ.setdefault("SECRET_KEY", "test-secret")

from app.api.endpoints import router
from app.core.security import ALGORITHM, SECRET_KEY


def make_token(role="admin", dc_id=None, username="admin"):
    payload = {
        "sub": username,
        "role": role,
        "dc_id": dc_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, SECRET_KEY, ALGORITHM)


def global_admin_headers():
    return {"Authorization": f"Bearer {make_token(role='admin', dc_id=None)}"}


def dc_admin_headers(dc_id=1):
    return {"Authorization": f"Bearer {make_token(role='admin', dc_id=dc_id)}"}


def operator_headers(dc_id=1):
    return {
        "Authorization": f"Bearer {make_token(role='operator', dc_id=dc_id, username='operator')}"
    }


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def app():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.core.database import Base, get_db
    from app.core.store import persist_state_changed_event  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db
    app.state._test_session_factory = TestSession  # type: ignore[attr-defined]
    yield app
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(app):
    factory = app.state._test_session_factory  # type: ignore[attr-defined]
    db = factory()
    try:
        yield db
    finally:
        db.close()

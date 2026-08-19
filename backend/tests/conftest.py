"""Shared pytest fixtures: isolated in-memory database and authenticated clients."""

from collections.abc import Generator, Iterator
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import get_db
from app.factories.feature_flag_factory import FeatureFlagFactory
from app.factories.kyc_factory import KycReviewFactory
from app.factories.refund_factory import RefundFactory
from app.main import create_app
from app.models import Base, FeatureFlag, KycReview, Refund, User
from app.models.base import utcnow
from app.models.enums import DocumentType, RefundReason, Role
from app.routers.auth import login_rate_limiter
from app.schemas.feature_flag import FeatureFlagCreate
from app.schemas.kyc import KycReviewCreate
from app.schemas.refund import RefundCreate
from app.utils.security import hash_password

TEST_PASSWORD = "demo123"


@pytest.fixture(autouse=True)
def reset_login_rate_limiter() -> Iterator[None]:
    """Keep the process-wide login limiter from leaking between tests."""
    login_rate_limiter.clear()
    yield
    login_rate_limiter.clear()


@pytest.fixture(name="settings")
def settings_fixture() -> Settings:
    return Settings(
        environment="test",
        database_url="sqlite://",
        jwt_secret_key="test-secret",
        debug=False,
    )


@pytest.fixture(name="session_factory")
def session_factory_fixture() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(name="db")
def db_fixture(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture(name="users")
def users_fixture(db: Session) -> dict[Role, User]:
    created = {
        Role.ADMIN: User(
            email="admin@fintech.com",
            full_name="Admin User",
            hashed_password=hash_password(TEST_PASSWORD),
            role=Role.ADMIN,
        ),
        Role.REVIEWER: User(
            email="reviewer@fintech.com",
            full_name="Reviewer User",
            hashed_password=hash_password(TEST_PASSWORD),
            role=Role.REVIEWER,
        ),
        Role.VIEWER: User(
            email="viewer@fintech.com",
            full_name="Viewer User",
            hashed_password=hash_password(TEST_PASSWORD),
            role=Role.VIEWER,
        ),
    }
    db.add_all(list(created.values()))
    db.commit()
    return created


@pytest.fixture(name="app")
def app_fixture(
    settings: Settings,
    session_factory: sessionmaker[Session],
    users: dict[Role, User],
) -> FastAPI:
    application = create_app(settings)

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    return application


@pytest.fixture(name="client")
def client_fixture(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient, email: str) -> TestClient:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture(name="admin_client")
def admin_client_fixture(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield _login(test_client, "admin@fintech.com")


@pytest.fixture(name="reviewer_client")
def reviewer_client_fixture(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield _login(test_client, "reviewer@fintech.com")


@pytest.fixture(name="viewer_client")
def viewer_client_fixture(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield _login(test_client, "viewer@fintech.com")


@pytest.fixture(name="kyc_review")
def kyc_review_fixture(db: Session) -> KycReview:
    review = KycReviewFactory.build(
        KycReviewCreate(
            customer_name="Test Customer",
            customer_email="test.customer@example.com",
            customer_country="US",
            risk_score=42,
            risk_summary="Standard onboarding checks completed.",
            primary_document_type=DocumentType.PASSPORT,
        )
    )
    review.documents.append(
        KycReviewFactory.build_document(
            document_type=DocumentType.PASSPORT, file_name="passport.pdf", verified=True
        )
    )
    db.add(review)
    db.commit()
    return review


@pytest.fixture(name="refund")
def refund_fixture(db: Session) -> Refund:
    record = RefundFactory.build(
        RefundCreate(
            customer_name="Test Customer",
            customer_email="test.customer@example.com",
            transaction_reference="TXN-9001",
            amount=Decimal("125.50"),
            reason=RefundReason.DUPLICATE_CHARGE,
            reason_detail="Charged twice for the same subscription renewal.",
            requested_at=utcnow() - timedelta(days=2),
        )
    )
    db.add(record)
    db.commit()
    return record


@pytest.fixture(name="feature_flag")
def feature_flag_fixture(db: Session, users: dict[Role, User]) -> FeatureFlag:
    flag = FeatureFlagFactory.build(
        FeatureFlagCreate(
            name="Instant transfers",
            description="Enable instant payouts for verified accounts.",
        )
    )
    flag.modified_by_id = users[Role.ADMIN].id
    db.add(flag)
    db.commit()
    return flag

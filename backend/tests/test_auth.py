"""Authentication and role-based access control tests."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import Role
from app.models.user import User
from app.routers.auth import login_rate_limiter
from app.utils.security import create_access_token, create_refresh_token
from tests.conftest import TEST_PASSWORD


def test_login_returns_token_and_profile(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@fintech.com", "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "admin"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] > 0


def test_refresh_returns_a_new_token_pair(client: TestClient) -> None:
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@fintech.com", "password": TEST_PASSWORD},
    ).json()

    response = client.post("/api/auth/refresh", json={"refresh_token": login["refresh_token"]})

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "admin@fintech.com"
    assert body["access_token"]
    assert body["refresh_token"]

    profile = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert profile.status_code == 200


def test_refresh_rejects_an_access_token(client: TestClient) -> None:
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@fintech.com", "password": TEST_PASSWORD},
    ).json()

    response = client.post("/api/auth/refresh", json={"refresh_token": login["access_token"]})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"


def test_refresh_token_is_not_accepted_as_a_bearer_credential(
    client: TestClient,
) -> None:
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@fintech.com", "password": TEST_PASSWORD},
    ).json()

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {login['refresh_token']}"},
    )

    assert response.status_code == 401


def test_refresh_rejects_an_expired_token(client: TestClient, users: dict[Role, User]) -> None:
    admin = users[Role.ADMIN]
    expired = create_refresh_token(
        admin.email,
        role=admin.role.value,
        user_id=admin.id,
        expires_delta=timedelta(minutes=-1),
    )

    response = client.post("/api/auth/refresh", json={"refresh_token": expired})

    assert response.status_code == 401


def test_refresh_rejects_a_deactivated_user(
    client: TestClient, db: Session, users: dict[Role, User]
) -> None:
    viewer = users[Role.VIEWER]
    token = create_refresh_token(viewer.email, role=viewer.role.value, user_id=viewer.id)
    viewer.is_active = False
    db.commit()

    response = client.post("/api/auth/refresh", json={"refresh_token": token})

    assert response.status_code == 401


def test_access_token_is_not_accepted_at_the_refresh_endpoint_even_when_valid(
    client: TestClient, users: dict[Role, User]
) -> None:
    admin = users[Role.ADMIN]
    token = create_access_token(admin.email, role=admin.role.value, user_id=admin.id)

    assert client.post("/api/auth/refresh", json={"refresh_token": token}).status_code == 401


def test_repeated_failed_logins_are_rate_limited(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(login_rate_limiter, "max_events", 3)

    for _ in range(3):
        failed = client.post(
            "/api/auth/login",
            json={"email": "admin@fintech.com", "password": "wrong-password"},
        )
        assert failed.status_code == 401

    blocked = client.post(
        "/api/auth/login",
        json={"email": "admin@fintech.com", "password": "wrong-password"},
    )

    assert blocked.status_code == 429
    error = blocked.json()["error"]
    assert error["code"] == "rate_limited"
    assert error["details"]["retry_after_seconds"] >= 1

    # The limit is keyed per account, so a different login is unaffected.
    other = client.post(
        "/api/auth/login",
        json={"email": "viewer@fintech.com", "password": TEST_PASSWORD},
    )
    assert other.status_code == 200


def test_successful_login_clears_the_failure_budget(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(login_rate_limiter, "max_events", 3)

    for _ in range(2):
        client.post(
            "/api/auth/login",
            json={"email": "admin@fintech.com", "password": "wrong-password"},
        )
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "admin@fintech.com", "password": TEST_PASSWORD},
        ).status_code
        == 200
    )

    for _ in range(3):
        assert (
            client.post(
                "/api/auth/login",
                json={"email": "admin@fintech.com", "password": "wrong-password"},
            ).status_code
            == 401
        )


def test_login_rejects_wrong_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@fintech.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"


def test_login_rejects_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@fintech.com", "password": TEST_PASSWORD},
    )

    assert response.status_code == 401


def test_me_requires_a_token(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_a_malformed_token(client: TestClient) -> None:
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401


def test_me_returns_the_authenticated_user(reviewer_client: TestClient) -> None:
    response = reviewer_client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "reviewer@fintech.com"


def test_viewer_can_read_every_tool(viewer_client: TestClient) -> None:
    for path in ("/api/kyc/reviews", "/api/refunds", "/api/feature-flags"):
        assert viewer_client.get(path).status_code == 200


def test_viewer_cannot_mutate_any_tool(viewer_client: TestClient) -> None:
    forbidden = [
        viewer_client.post("/api/kyc/reviews/1/approve", json={"reason": "looks fine"}),
        viewer_client.post("/api/refunds/1/approve", json={"reason": "duplicate"}),
        viewer_client.post(
            "/api/feature-flags/1/toggle",
            json={"environment": "production", "enabled": True},
        ),
    ]

    assert [response.status_code for response in forbidden] == [403, 403, 403]
    assert forbidden[0].json()["error"]["code"] == "permission_denied"


def test_reviewer_cannot_administer_feature_flags(reviewer_client: TestClient) -> None:
    response = reviewer_client.post(
        "/api/feature-flags",
        json={"name": "Reviewer flag", "description": "Should be rejected."},
    )

    assert response.status_code == 403


def test_only_admins_can_create_users(
    reviewer_client: TestClient, admin_client: TestClient
) -> None:
    payload = {
        "email": "new.analyst@fintech.com",
        "full_name": "New Analyst",
        "password": "demo1234",
        "role": "viewer",
    }

    assert reviewer_client.post("/api/auth/users", json=payload).status_code == 403
    assert admin_client.post("/api/auth/users", json=payload).status_code == 201

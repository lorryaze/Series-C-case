"""Authentication and role-based access control tests."""

from fastapi.testclient import TestClient

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

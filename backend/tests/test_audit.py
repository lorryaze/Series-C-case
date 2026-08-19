"""Shared audit trail tests: the trail is paginated, read-only and cross-tool."""

from fastapi.testclient import TestClient

from app.models import FeatureFlag, KycReview
from app.models.enums import Role
from app.models.user import User


def _make_entries(admin_client: TestClient, review_id: int, count: int) -> None:
    for index in range(count):
        admin_client.post(
            f"/api/kyc/reviews/{review_id}/notes",
            json={"body": f"Reviewed batch {index}."},
        )


def test_recent_activity_is_paginated(admin_client: TestClient, kyc_review: KycReview) -> None:
    _make_entries(admin_client, kyc_review.id, 5)

    first = admin_client.get("/api/audit", params={"page": 1, "page_size": 2}).json()
    last = admin_client.get("/api/audit", params={"page": 3, "page_size": 2}).json()

    assert first["total"] >= 5
    assert first["page"] == 1
    assert first["page_size"] == 2
    assert first["pages"] == -(-first["total"] // 2)
    assert len(first["items"]) == 2
    assert last["page"] == 3


def test_recent_activity_can_be_filtered_by_entity_type(
    admin_client: TestClient, kyc_review: KycReview, feature_flag: FeatureFlag
) -> None:
    _make_entries(admin_client, kyc_review.id, 2)
    admin_client.post(
        f"/api/feature-flags/{feature_flag.id}/toggle",
        json={"environment": "production", "enabled": True},
    )

    flags_only = admin_client.get("/api/audit", params={"entity_type": "feature_flag"}).json()

    assert flags_only["total"] >= 1
    assert {entry["entity_type"] for entry in flags_only["items"]} == {"feature_flag"}


def test_entity_trail_is_paginated_newest_first(
    admin_client: TestClient, kyc_review: KycReview
) -> None:
    _make_entries(admin_client, kyc_review.id, 3)

    page = admin_client.get(
        f"/api/audit/kyc_review/{kyc_review.id}", params={"page_size": 2}
    ).json()

    assert page["total"] == 3
    assert page["pages"] == 2
    timestamps = [entry["created_at"] for entry in page["items"]]
    assert timestamps == sorted(timestamps, reverse=True)


def test_pagination_bounds_are_validated(
    admin_client: TestClient, kyc_review: KycReview
) -> None:
    assert admin_client.get("/api/audit", params={"page": 0}).status_code == 422
    assert admin_client.get("/api/audit", params={"page_size": 0}).status_code == 422
    assert admin_client.get("/api/audit", params={"page_size": 201}).status_code == 422


def test_every_role_can_read_the_trail(
    viewer_client: TestClient, users: dict[Role, User]
) -> None:
    assert users[Role.VIEWER].role is Role.VIEWER
    assert viewer_client.get("/api/audit").status_code == 200

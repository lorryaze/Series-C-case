"""KYC review queue tests: CRUD, filtering, decisions and the audit trail."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import KycReview, User
from app.models.enums import Role

NEW_CASE = {
    "customer_name": "Nadia Okafor",
    "customer_email": "nadia.okafor@example.com",
    "customer_country": "GB",
    "risk_score": 68,
    "risk_summary": "Adverse media match requires manual verification.",
    "primary_document_type": "passport",
}


def test_create_review_derives_reference_and_risk_level(reviewer_client: TestClient) -> None:
    response = reviewer_client.post("/api/kyc/reviews", json=NEW_CASE)

    assert response.status_code == 201
    body = response.json()
    assert body["case_reference"].startswith("KYC-")
    assert body["risk_level"] == "high"
    assert body["status"] == "pending"
    assert body["assigned_reviewer"] is None


def test_create_review_validates_the_risk_score(reviewer_client: TestClient) -> None:
    response = reviewer_client.post("/api/kyc/reviews", json={**NEW_CASE, "risk_score": 140})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_error"


def test_list_reviews_is_paginated(reviewer_client: TestClient, kyc_review: KycReview) -> None:
    response = reviewer_client.get("/api/kyc/reviews", params={"page_size": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["case_reference"] == kyc_review.case_reference


def test_queue_counts_track_status_changes(
    reviewer_client: TestClient, kyc_review: KycReview
) -> None:
    before = reviewer_client.get("/api/kyc/reviews/counts").json()
    assert before == {
        "pending": 1,
        "in_review": 0,
        "approved": 0,
        "rejected": 0,
        "escalated": 0,
        "total": 1,
    }

    reviewer_client.post(
        f"/api/kyc/reviews/{kyc_review.id}/approve",
        json={"reason": "Documents verified against the issuing authority."},
    )

    after = reviewer_client.get("/api/kyc/reviews/counts").json()
    assert after["approved"] == 1
    assert after["pending"] == 0


def test_filters_narrow_the_queue(reviewer_client: TestClient, kyc_review: KycReview) -> None:
    assert (
        reviewer_client.get("/api/kyc/reviews", params={"status": "approved"}).json()["total"]
        == 0
    )
    assert (
        reviewer_client.get(
            "/api/kyc/reviews", params={"risk_level": kyc_review.risk_level.value}
        ).json()["total"]
        == 1
    )
    assert (
        reviewer_client.get("/api/kyc/reviews", params={"search": "Test Customer"}).json()[
            "total"
        ]
        == 1
    )
    assert (
        reviewer_client.get("/api/kyc/reviews", params={"unassigned": True}).json()["total"]
        == 1
    )


def test_detail_view_includes_documents(
    reviewer_client: TestClient, kyc_review: KycReview
) -> None:
    response = reviewer_client.get(f"/api/kyc/reviews/{kyc_review.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["risk_summary"]
    assert [document["document_type"] for document in body["documents"]] == ["passport"]


def test_detail_view_404s_for_unknown_cases(reviewer_client: TestClient) -> None:
    response = reviewer_client.get("/api/kyc/reviews/4242")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_reject_requires_a_reason(reviewer_client: TestClient, kyc_review: KycReview) -> None:
    missing = reviewer_client.post(f"/api/kyc/reviews/{kyc_review.id}/reject", json={})
    assert missing.status_code == 422

    rejected = reviewer_client.post(
        f"/api/kyc/reviews/{kyc_review.id}/reject",
        json={"reason": "Identity document expired and no replacement supplied."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["decided_at"] is not None


def test_decisions_are_not_allowed_twice(
    reviewer_client: TestClient, kyc_review: KycReview
) -> None:
    payload = {"reason": "Verified against two independent sources."}
    assert (
        reviewer_client.post(
            f"/api/kyc/reviews/{kyc_review.id}/approve", json=payload
        ).status_code
        == 200
    )

    conflict = reviewer_client.post(f"/api/kyc/reviews/{kyc_review.id}/approve", json=payload)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "conflict"


def test_escalate_moves_the_case_out_of_the_queue(
    reviewer_client: TestClient, kyc_review: KycReview
) -> None:
    response = reviewer_client.post(
        f"/api/kyc/reviews/{kyc_review.id}/escalate",
        json={"reason": "Possible sanctions exposure; needs compliance lead."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "escalated"


def test_assign_puts_the_case_in_review(
    reviewer_client: TestClient, kyc_review: KycReview, users: dict[Role, User]
) -> None:
    response = reviewer_client.post(
        f"/api/kyc/reviews/{kyc_review.id}/assign",
        json={"reviewer_id": users[Role.REVIEWER].id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assigned_reviewer"]["email"] == "reviewer@fintech.com"
    assert body["status"] == "in_review"


def test_assign_rejects_users_who_cannot_review(
    reviewer_client: TestClient, kyc_review: KycReview, users: dict[Role, User]
) -> None:
    response = reviewer_client.post(
        f"/api/kyc/reviews/{kyc_review.id}/assign",
        json={"reviewer_id": users[Role.VIEWER].id},
    )

    assert response.status_code == 422


def test_bulk_assign_updates_every_selected_case(
    reviewer_client: TestClient,
    db: Session,
    kyc_review: KycReview,
    users: dict[Role, User],
) -> None:
    second = reviewer_client.post("/api/kyc/reviews", json=NEW_CASE).json()

    response = reviewer_client.post(
        "/api/kyc/reviews/bulk-assign",
        json={
            "review_ids": [kyc_review.id, second["id"]],
            "reviewer_id": users[Role.ADMIN].id,
        },
    )

    assert response.status_code == 200
    assert response.json()["assigned"] == 2
    db.expire_all()
    assigned = db.query(KycReview).filter(KycReview.assigned_reviewer_id.isnot(None)).count()
    assert assigned == 2


def test_notes_are_recorded_with_their_author(
    reviewer_client: TestClient, kyc_review: KycReview
) -> None:
    response = reviewer_client.post(
        f"/api/kyc/reviews/{kyc_review.id}/notes",
        json={"body": "Requested a proof of address dated within 90 days."},
    )

    assert response.status_code == 201
    assert response.json()["author"]["email"] == "reviewer@fintech.com"

    detail = reviewer_client.get(f"/api/kyc/reviews/{kyc_review.id}").json()
    assert len(detail["notes"]) == 1


def test_audit_trail_captures_previous_and_new_values(
    reviewer_client: TestClient, kyc_review: KycReview, users: dict[Role, User]
) -> None:
    reviewer_client.post(
        f"/api/kyc/reviews/{kyc_review.id}/assign",
        json={"reviewer_id": users[Role.REVIEWER].id},
    )
    reviewer_client.post(
        f"/api/kyc/reviews/{kyc_review.id}/approve",
        json={"reason": "All checks cleared."},
    )

    entries = reviewer_client.get(f"/api/kyc/reviews/{kyc_review.id}/audit").json()["entries"]
    actions = {entry["action"] for entry in entries}
    assert {"assigned", "status_changed"} <= actions

    decision = next(entry for entry in entries if entry["field"] == "status")
    assert decision["previous_value"] == "in_review"
    assert decision["new_value"] == "approved"
    assert decision["reason"] == "All checks cleared."
    assert decision["actor_email"] == "reviewer@fintech.com"

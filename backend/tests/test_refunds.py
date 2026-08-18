"""Refunds dashboard tests: metrics, filters and the approval workflow."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models import Refund

NEW_REFUND = {
    "customer_name": "Marcus Villalobos",
    "customer_email": "marcus.villalobos@example.com",
    "transaction_reference": "TXN-77120",
    "amount": "420.00",
    "reason": "fraud",
    "reason_detail": "Card reported stolen before the charge settled.",
}


def test_create_refund_starts_pending_with_a_reference(reviewer_client: TestClient) -> None:
    response = reviewer_client.post("/api/refunds", json=NEW_REFUND)

    assert response.status_code == 201
    body = response.json()
    assert body["refund_reference"].startswith("RF-")
    assert body["status"] == "pending"
    assert body["processed_at"] is None
    assert body["currency"] == "USD"


def test_create_refund_rejects_a_non_positive_amount(reviewer_client: TestClient) -> None:
    response = reviewer_client.post("/api/refunds", json={**NEW_REFUND, "amount": "0"})

    assert response.status_code == 422


def test_summary_cards_aggregate_counts_and_amounts(
    reviewer_client: TestClient, refund: Refund
) -> None:
    reviewer_client.post("/api/refunds", json=NEW_REFUND)
    reviewer_client.post(
        f"/api/refunds/{refund.id}/approve", json={"reason": "Duplicate charge confirmed."}
    )

    summary = reviewer_client.get("/api/refunds/summary").json()
    assert summary["total_count"] == 2
    assert summary["approved_count"] == 1
    assert summary["pending_count"] == 1
    assert float(summary["approved_amount"]) == 125.50
    assert summary["average_processing_hours"] is not None


def test_trend_returns_one_dense_point_per_day(reviewer_client: TestClient) -> None:
    points = reviewer_client.get("/api/refunds/trend", params={"days": 30}).json()

    assert len(points) == 30
    assert points[-1]["day"] == date.today().isoformat()
    assert points[0]["day"] == (date.today() - timedelta(days=29)).isoformat()


def test_filters_narrow_the_refunds_table(reviewer_client: TestClient, refund: Refund) -> None:
    assert (
        reviewer_client.get("/api/refunds", params={"status": "approved"}).json()["total"] == 0
    )
    assert (
        reviewer_client.get("/api/refunds", params={"reason": "duplicate_charge"}).json()[
            "total"
        ]
        == 1
    )
    assert (
        reviewer_client.get("/api/refunds", params={"min_amount": "200"}).json()["total"] == 0
    )
    assert (
        reviewer_client.get(
            "/api/refunds", params={"min_amount": "100", "max_amount": "200"}
        ).json()["total"]
        == 1
    )
    assert (
        reviewer_client.get("/api/refunds", params={"search": refund.refund_reference}).json()[
            "total"
        ]
        == 1
    )


def test_detail_view_includes_history_and_approval_chain(
    reviewer_client: TestClient, refund: Refund
) -> None:
    reviewer_client.post(
        f"/api/refunds/{refund.id}/approve", json={"reason": "Duplicate charge confirmed."}
    )

    body = reviewer_client.get(f"/api/refunds/{refund.id}").json()
    assert body["transaction_reference"] == "TXN-9001"
    assert body["processed_by"]["email"] == "reviewer@fintech.com"
    assert body["processing_hours"] is not None
    assert [entry["field"] for entry in body["approval_chain"]] == ["status"]
    assert body["approval_chain"][0]["new_value"] == "approved"


def test_reject_requires_a_reason(reviewer_client: TestClient, refund: Refund) -> None:
    assert reviewer_client.post(f"/api/refunds/{refund.id}/reject", json={}).status_code == 422

    rejected = reviewer_client.post(
        f"/api/refunds/{refund.id}/reject",
        json={"reason": "Original charge was authorised by the cardholder."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["decision_reason"]


def test_request_more_info_keeps_the_refund_open(
    reviewer_client: TestClient, refund: Refund
) -> None:
    response = reviewer_client.post(
        f"/api/refunds/{refund.id}/request-info",
        json={"reason": "Need the merchant statement covering the disputed period."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "info_requested"
    assert response.json()["processed_at"] is None

    approved = reviewer_client.post(
        f"/api/refunds/{refund.id}/approve", json={"reason": "Statement received."}
    )
    assert approved.status_code == 200


def test_a_settled_refund_cannot_be_decided_again(
    reviewer_client: TestClient, refund: Refund
) -> None:
    payload = {"reason": "Duplicate charge confirmed."}
    assert (
        reviewer_client.post(f"/api/refunds/{refund.id}/approve", json=payload).status_code
        == 200
    )

    conflict = reviewer_client.post(f"/api/refunds/{refund.id}/reject", json=payload)
    assert conflict.status_code == 409


def test_unknown_refunds_return_404(reviewer_client: TestClient) -> None:
    assert reviewer_client.get("/api/refunds/9999").status_code == 404

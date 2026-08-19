"""Feature flag admin tests: creation, toggling, rollout and history."""

from fastapi.testclient import TestClient

from app.models import FeatureFlag


def _environment(flag: dict[str, object], name: str) -> dict[str, object]:
    environments: list[dict[str, object]] = flag["environments"]  # type: ignore[assignment]
    return next(state for state in environments if state["environment"] == name)


def test_create_flag_derives_the_key_and_all_environments(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/api/feature-flags",
        json={
            "name": "Enable Instant Transfers",
            "description": "Route eligible payouts through the instant rail.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["key"] == "enable_instant_transfers"
    assert {state["environment"] for state in body["environments"]} == {
        "production",
        "staging",
        "development",
    }
    assert all(state["enabled"] is False for state in body["environments"])
    assert body["modified_by"]["email"] == "admin@fintech.com"


def test_create_flag_defaults_can_enable_every_environment(admin_client: TestClient) -> None:
    body = admin_client.post(
        "/api/feature-flags",
        json={
            "name": "Dark mode",
            "description": "Ship the dark theme.",
            "default_enabled": True,
        },
    ).json()

    assert all(state["enabled"] for state in body["environments"])
    assert all(state["rollout_percentage"] == 100 for state in body["environments"])


def test_duplicate_keys_are_rejected(
    admin_client: TestClient, feature_flag: FeatureFlag
) -> None:
    response = admin_client.post(
        "/api/feature-flags",
        json={"name": feature_flag.name, "description": "Duplicate of an existing flag."},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_toggle_flips_a_single_environment(
    admin_client: TestClient, feature_flag: FeatureFlag
) -> None:
    body = admin_client.post(
        f"/api/feature-flags/{feature_flag.id}/toggle",
        json={"environment": "production", "enabled": True},
    ).json()

    assert _environment(body, "production")["enabled"] is True
    assert _environment(body, "staging")["enabled"] is False


def test_toggle_stamps_the_parent_flag_as_modified(
    admin_client: TestClient, feature_flag: FeatureFlag
) -> None:
    created = admin_client.get(f"/api/feature-flags/{feature_flag.id}").json()
    toggled = admin_client.post(
        f"/api/feature-flags/{feature_flag.id}/toggle",
        json={"environment": "production", "enabled": True},
    ).json()

    assert toggled["updated_at"] >= created["updated_at"]
    assert toggled["modified_by"]["email"] == "admin@fintech.com"


def test_rollout_percentage_can_be_set_per_environment(
    admin_client: TestClient, feature_flag: FeatureFlag
) -> None:
    body = admin_client.patch(
        f"/api/feature-flags/{feature_flag.id}/environments/staging",
        json={"enabled": True, "rollout_percentage": 25},
    ).json()

    assert _environment(body, "staging") == {
        "environment": "staging",
        "enabled": True,
        "rollout_percentage": 25,
    }
    assert _environment(body, "production")["rollout_percentage"] == 0


def test_rollout_percentage_is_bounded(
    admin_client: TestClient, feature_flag: FeatureFlag
) -> None:
    for invalid in (-1, 101):
        response = admin_client.patch(
            f"/api/feature-flags/{feature_flag.id}/environments/production",
            json={"rollout_percentage": invalid},
        )
        assert response.status_code == 422


def test_flag_metadata_can_be_edited(
    admin_client: TestClient, feature_flag: FeatureFlag
) -> None:
    body = admin_client.patch(
        f"/api/feature-flags/{feature_flag.id}",
        json={"description": "Instant payouts for accounts with a verified ledger."},
    ).json()

    assert body["description"] == "Instant payouts for accounts with a verified ledger."
    assert body["key"] == feature_flag.key


def test_list_supports_search_and_environment_filters(
    admin_client: TestClient, feature_flag: FeatureFlag
) -> None:
    admin_client.post(
        f"/api/feature-flags/{feature_flag.id}/toggle",
        json={"environment": "production", "enabled": True},
    )

    assert (
        admin_client.get("/api/feature-flags", params={"search": "instant"}).json()["total"]
        == 1
    )
    assert (
        admin_client.get("/api/feature-flags", params={"search": "nothing-matches"}).json()[
            "total"
        ]
        == 0
    )
    assert (
        admin_client.get(
            "/api/feature-flags", params={"environment": "production", "enabled": True}
        ).json()["total"]
        == 1
    )
    assert (
        admin_client.get(
            "/api/feature-flags", params={"environment": "staging", "enabled": True}
        ).json()["total"]
        == 0
    )


def test_history_records_who_changed_what(
    admin_client: TestClient, feature_flag: FeatureFlag
) -> None:
    admin_client.post(
        f"/api/feature-flags/{feature_flag.id}/toggle",
        json={"environment": "production", "enabled": True},
    )
    admin_client.patch(
        f"/api/feature-flags/{feature_flag.id}/environments/production",
        json={"rollout_percentage": 50},
    )

    entries = admin_client.get(f"/api/feature-flags/{feature_flag.id}/history").json()["items"]
    fields = [entry["field"] for entry in entries]
    assert "production.enabled" in fields
    assert "production.rollout_percentage" in fields

    rollout = next(
        entry for entry in entries if entry["field"] == "production.rollout_percentage"
    )
    assert rollout["previous_value"] == "0"
    assert rollout["new_value"] == "50"
    assert rollout["actor_email"] == "admin@fintech.com"


def test_unknown_flags_return_404(admin_client: TestClient) -> None:
    assert admin_client.get("/api/feature-flags/9999").status_code == 404


def test_history_is_paginated(admin_client: TestClient, feature_flag: FeatureFlag) -> None:
    for percentage in (10, 20, 30):
        admin_client.patch(
            f"/api/feature-flags/{feature_flag.id}/environments/production",
            json={"rollout_percentage": percentage},
        )

    first = admin_client.get(
        f"/api/feature-flags/{feature_flag.id}/history",
        params={"page": 1, "page_size": 2},
    ).json()
    second = admin_client.get(
        f"/api/feature-flags/{feature_flag.id}/history",
        params={"page": 2, "page_size": 2},
    ).json()

    assert first["total"] == 3
    assert first["pages"] == 2
    assert len(first["items"]) == 2
    assert len(second["items"]) == 1
    assert {entry["id"] for entry in first["items"]}.isdisjoint(
        entry["id"] for entry in second["items"]
    )


def test_history_rejects_out_of_range_pagination(
    admin_client: TestClient, feature_flag: FeatureFlag
) -> None:
    base = f"/api/feature-flags/{feature_flag.id}/history"

    assert admin_client.get(base, params={"page": 0}).status_code == 422
    assert admin_client.get(base, params={"page_size": 500}).status_code == 422


def test_admin_can_delete_a_flag_and_the_deletion_is_audited(
    admin_client: TestClient, feature_flag: FeatureFlag
) -> None:
    flag_id = feature_flag.id

    response = admin_client.delete(f"/api/feature-flags/{flag_id}")

    assert response.status_code == 200
    assert feature_flag.key in response.json()["message"]
    assert admin_client.get(f"/api/feature-flags/{flag_id}").status_code == 404

    trail = admin_client.get(f"/api/audit/feature_flag/{flag_id}").json()
    assert "deleted" in {entry["action"] for entry in trail["items"]}


def test_deleting_an_unknown_flag_returns_404(admin_client: TestClient) -> None:
    assert admin_client.delete("/api/feature-flags/9999").status_code == 404


def test_non_admins_cannot_delete_flags(
    reviewer_client: TestClient, viewer_client: TestClient, feature_flag: FeatureFlag
) -> None:
    assert reviewer_client.delete(f"/api/feature-flags/{feature_flag.id}").status_code == 403
    assert viewer_client.delete(f"/api/feature-flags/{feature_flag.id}").status_code == 403

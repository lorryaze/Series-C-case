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

    entries = admin_client.get(f"/api/feature-flags/{feature_flag.id}/history").json()[
        "entries"
    ]
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

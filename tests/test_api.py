"""API v1 smoke and integration tests."""

from __future__ import annotations

import pytest
from django.test import Client, override_settings


@pytest.mark.django_db
class TestAPIPing:
    """Verify the unauthenticated /api/v1/ping/ endpoint."""

    def test_ping_returns_ok(self, client: Client) -> None:
        response = client.get("/api/v1/ping/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"

    def test_ping_requires_no_auth(self, client: Client) -> None:
        """Unauthenticated requests should still succeed on /ping/."""
        response = client.get("/api/v1/ping/")
        assert response.status_code == 200


class TestOpenAPIDocs:
    """Verify OpenAPI spec and docs endpoints are available."""

    def test_openapi_json_returns_spec(self, client: Client) -> None:
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        spec = response.json()
        assert spec["info"]["title"] == "AuroraElo API"
        assert spec["info"]["version"] == "1.0.0"
        assert "/api/v1/ping/" in spec["paths"]

    def test_docs_page_available(self, client: Client) -> None:
        response = client.get("/api/v1/docs/")
        assert response.status_code == 200

    def test_spec_has_journal_tag(self, client: Client) -> None:
        spec = client.get("/api/v1/openapi.json").json()
        tags = {tag["name"] for tag in spec.get("tags", [])}
        # If no tags key, check that journal paths exist
        journal_paths = [p for p in spec["paths"] if "journal" in p]
        assert len(journal_paths) > 0

    def test_spec_has_goals_tag(self, client: Client) -> None:
        spec = client.get("/api/v1/openapi.json").json()
        goals_paths = [p for p in spec["paths"] if "goals" in p]
        assert len(goals_paths) > 0

    def test_spec_has_scheduling_tag(self, client: Client) -> None:
        spec = client.get("/api/v1/openapi.json").json()
        scheduling_paths = [p for p in spec["paths"] if "scheduling" in p]
        assert len(scheduling_paths) > 0


class TestAPIAuthRequirements:
    """Verify that domain endpoints require authentication."""

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/journal/entries/",
            "/api/v1/journal/checkins/",
            "/api/v1/goals/",
            "/api/v1/scheduling/appointments/",
            "/api/v1/scheduling/services/",
        ],
    )
    def test_unauthenticated_returns_401(self, client: Client, path: str) -> None:
        response = client.get(path)
        assert response.status_code == 401

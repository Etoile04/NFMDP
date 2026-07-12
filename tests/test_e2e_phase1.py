"""E2E Phase 1 Verification: Seed data → API CRUD → Health check.

Verifies the Phase 1 pipeline against a running backend:
  1. Health check returns 200
  2. /api/v1/materials returns seeded literature materials
  3. /api/v1/properties returns property measurements
  4. /api/v1/sources returns data source records
  5. Detail endpoints return individual records
  6. Filtering and pagination work correctly

Run with: pytest tests/test_e2e_phase1.py -v --phase1
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE = os.getenv(
    "NFM_API_BASE",
    "http://localhost:8000",
).rstrip("/")

MIN_MATERIALS = 5
MIN_PROPERTIES = 10
MIN_SOURCES = 5


# ---------------------------------------------------------------------------
# Data Classes (immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResponseTimings:
    """Immutable latency measurements for an endpoint."""

    endpoint: str
    count: int
    min_ms: float
    max_ms: float
    mean_ms: float
    p95_ms: float


@dataclass(frozen=True)
class EndpointVerification:
    """Immutable result of verifying a single endpoint."""

    endpoint: str
    status_code: int
    item_count: int
    total_records: int
    response_time_ms: float
    passed: bool


# ---------------------------------------------------------------------------
# HTTP Client
# ---------------------------------------------------------------------------


class APIClient:
    """Minimal HTTP client for the NFM API."""

    def __init__(self, base_url: str = API_BASE) -> None:
        self._base_url = base_url

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], float]:
        """Send GET request, return (response_json, response_time_ms)."""
        url = self._base_url + path
        if params:
            qs = "&".join(
                f"{k}={v}" for k, v in params.items() if v is not None
            )
            if qs:
                url += f"?{qs}"

        req = Request(url, method="GET")
        start = time.monotonic()
        try:
            with urlopen(req, timeout=30) as resp:
                elapsed_ms = (time.monotonic() - start) * 1000
                body = json.loads(resp.read().decode("utf-8"))
                return body, elapsed_ms
        except HTTPError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GET {path} → {exc.code}: {error_body}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Cannot connect to API at {url}: {exc.reason}"
            ) from exc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def api_client() -> APIClient:
    """Shared API client for all Phase 1 E2E tests."""
    return APIClient()


@pytest.fixture(scope="session")
def health_status(api_client: APIClient) -> dict[str, str]:
    """Verify API is reachable and healthy."""
    body, _ = api_client.get("/health")
    return body


@pytest.fixture(scope="session")
def first_material_id(api_client: APIClient) -> str:
    """Fetch the first material ID for detail endpoint tests."""
    body, _ = api_client.get("/api/v1/materials", {"limit": "1"})
    items = body.get("items", [])
    if not items:
        pytest.skip("No materials in database — seed data not loaded")
    return items[0]["id"]


@pytest.fixture(scope="session")
def first_source_id(api_client: APIClient) -> str:
    """Fetch the first source ID for detail endpoint tests."""
    body, _ = api_client.get("/api/v1/sources", {"limit": "1"})
    items = body.get("items", [])
    if not items:
        pytest.skip("No sources in database — seed data not loaded")
    return items[0]["id"]


@pytest.fixture(scope="session")
def first_property_id(api_client: APIClient) -> str:
    """Fetch the first property ID for detail endpoint tests."""
    body, _ = api_client.get("/api/v1/properties", {"limit": "1"})
    items = body.get("items", [])
    if not items:
        pytest.skip("No properties in database — seed data not loaded")
    return items[0]["id"]


# ---------------------------------------------------------------------------
# Step 1: Health Check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    """Verify the API is reachable and returns healthy status."""

    @pytest.mark.phase1
    def test_health_returns_ok(self, health_status: dict[str, str]) -> None:
        """Health endpoint returns status ok."""
        assert health_status.get("status") == "ok"


# ---------------------------------------------------------------------------
# Step 2: List Endpoints Return Seeded Data
# ---------------------------------------------------------------------------


class TestListEndpoints:
    """Verify all v1 list endpoints return seeded Phase 1 data."""

    @pytest.mark.phase1
    def test_list_materials_returns_data(
        self, api_client: APIClient,
    ) -> EndpointVerification:
        """GET /api/v1/materials returns >= MIN_MATERIALS records."""
        body, elapsed = api_client.get("/api/v1/materials")
        total = body.get("total", 0)
        items = body.get("items", [])
        assert total >= MIN_MATERIALS, (
            f"Expected >= {MIN_MATERIALS} materials, got {total}"
        )
        assert len(items) > 0, "Items array is empty"
        assert "id" in items[0], "Material records missing 'id' field"
        assert "name" in items[0], "Material records missing 'name' field"

        return EndpointVerification(
            endpoint="/api/v1/materials",
            status_code=200,
            item_count=len(items),
            total_records=total,
            response_time_ms=elapsed,
            passed=True,
        )

    @pytest.mark.phase1
    def test_list_sources_returns_data(
        self, api_client: APIClient,
    ) -> EndpointVerification:
        """GET /api/v1/sources returns >= MIN_SOURCES records."""
        body, elapsed = api_client.get("/api/v1/sources")
        total = body.get("total", 0)
        items = body.get("items", [])
        assert total >= MIN_SOURCES, (
            f"Expected >= {MIN_SOURCES} sources, got {total}"
        )
        assert len(items) > 0, "Items array is empty"
        assert "id" in items[0], "Source records missing 'id' field"
        assert "title" in items[0], "Source records missing 'title' field"

        return EndpointVerification(
            endpoint="/api/v1/sources",
            status_code=200,
            item_count=len(items),
            total_records=total,
            response_time_ms=elapsed,
            passed=True,
        )

    @pytest.mark.phase1
    def test_list_properties_returns_data(
        self, api_client: APIClient,
    ) -> EndpointVerification:
        """GET /api/v1/properties returns >= MIN_PROPERTIES records."""
        body, elapsed = api_client.get("/api/v1/properties")
        total = body.get("total", 0)
        items = body.get("items", [])
        assert total >= MIN_PROPERTIES, (
            f"Expected >= {MIN_PROPERTIES} properties, got {total}"
        )
        assert len(items) > 0, "Items array is empty"
        assert "id" in items[0], "Property records missing 'id' field"
        assert "value_type" in items[0], "Property records missing 'value_type'"

        return EndpointVerification(
            endpoint="/api/v1/properties",
            status_code=200,
            item_count=len(items),
            total_records=total,
            response_time_ms=elapsed,
            passed=True,
        )


# ---------------------------------------------------------------------------
# Step 3: Detail Endpoints
# ---------------------------------------------------------------------------


class TestDetailEndpoints:
    """Verify detail endpoints return individual records by ID."""

    @pytest.mark.phase1
    def test_get_material_by_id(
        self, api_client: APIClient, first_material_id: str,
    ) -> None:
        """GET /api/v1/materials/{id} returns a single material."""
        body, _ = api_client.get(f"/api/v1/materials/{first_material_id}")
        assert body["id"] == first_material_id
        assert "name" in body

    @pytest.mark.phase1
    def test_get_source_by_id(
        self, api_client: APIClient, first_source_id: str,
    ) -> None:
        """GET /api/v1/sources/{id} returns a single source."""
        body, _ = api_client.get(f"/api/v1/sources/{first_source_id}")
        assert body["id"] == first_source_id
        assert "title" in body

    @pytest.mark.phase1
    def test_get_property_by_id(
        self, api_client: APIClient, first_property_id: str,
    ) -> None:
        """GET /api/v1/properties/{id} returns a single property measurement."""
        body, _ = api_client.get(f"/api/v1/properties/{first_property_id}")
        assert body["id"] == first_property_id
        assert "value_type" in body

    @pytest.mark.phase1
    def test_get_nonexistent_material_returns_404(
        self, api_client: APIClient,
    ) -> None:
        """GET /api/v1/materials/{bad_id} returns 404."""
        with pytest.raises(RuntimeError, match="404"):
            api_client.get(
                "/api/v1/materials/00000000-0000-0000-0000-000000000000"
            )


# ---------------------------------------------------------------------------
# Step 4: Pagination and Filtering
# ---------------------------------------------------------------------------


class TestPaginationAndFiltering:
    """Verify pagination parameters and filtering work correctly."""

    @pytest.mark.phase1
    def test_materials_pagination_page2(
        self, api_client: APIClient,
    ) -> None:
        """Second page of materials differs from first page."""
        body1, _ = api_client.get(
            "/api/v1/materials", {"limit": "2", "page": "1"},
        )
        body2, _ = api_client.get(
            "/api/v1/materials", {"limit": "2", "page": "2"},
        )

        ids_page1 = {item["id"] for item in body1["items"]}
        ids_page2 = {item["id"] for item in body2["items"]}

        assert ids_page1 != ids_page2, (
            "Page 2 should contain different materials than page 1"
        )

    @pytest.mark.phase1
    def test_materials_limit_respected(
        self, api_client: APIClient,
    ) -> None:
        """Limit parameter controls returned item count."""
        body, _ = api_client.get("/api/v1/materials", {"limit": "3"})
        assert len(body["items"]) <= 3

    @pytest.mark.phase1
    def test_properties_filter_by_material(
        self, api_client: APIClient, first_material_id: str,
    ) -> None:
        """Filtering properties by material_id returns correct subset."""
        body, _ = api_client.get(
            "/api/v1/properties",
            {"material_id": first_material_id},
        )
        for item in body.get("items", []):
            assert item.get("material_id") == first_material_id, (
                f"Property {item['id']} has wrong material_id"
            )

    @pytest.mark.phase1
    def test_paginated_response_envelope(
        self, api_client: APIClient,
    ) -> None:
        """All list responses use consistent PaginatedResponse envelope."""
        for endpoint in [
            "/api/v1/materials",
            "/api/v1/sources",
            "/api/v1/properties",
        ]:
            body, _ = api_client.get(endpoint)
            assert "items" in body, f"{endpoint} missing 'items'"
            assert "total" in body, f"{endpoint} missing 'total'"
            assert "page" in body, f"{endpoint} missing 'page'"
            assert "limit" in body, f"{endpoint} missing 'limit'"
            assert isinstance(body["items"], list), (
                f"{endpoint} items is not a list"
            )
            assert isinstance(body["total"], int), (
                f"{endpoint} total is not an int"
            )


# ---------------------------------------------------------------------------
# Step 5: Full Pipeline Verification Summary
# ---------------------------------------------------------------------------


class TestFullPipelineSummary:
    """Aggregate verification of the complete Phase 1 pipeline."""

    @pytest.mark.phase1
    def test_pipeline_seed_data_loaded(
        self, api_client: APIClient,
    ) -> dict[str, bool]:
        """Verify all three data domains have seeded records."""
        endpoints_status: dict[str, bool] = {}

        materials_body, _ = api_client.get("/api/v1/materials")
        endpoints_status["materials"] = (
            materials_body.get("total", 0) >= MIN_MATERIALS
        )

        sources_body, _ = api_client.get("/api/v1/sources")
        endpoints_status["sources"] = (
            sources_body.get("total", 0) >= MIN_SOURCES
        )

        properties_body, _ = api_client.get("/api/v1/properties")
        endpoints_status["properties"] = (
            properties_body.get("total", 0) >= MIN_PROPERTIES
        )

        all_loaded = all(endpoints_status.values())
        assert all_loaded, f"Seed data incomplete: {endpoints_status}"

        return endpoints_status

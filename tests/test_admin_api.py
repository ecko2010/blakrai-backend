"""
Test Admin API — authentication, endpoint responses.
Uses FastAPI TestClient (sync wrapper around httpx.AsyncClient).
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a TestClient for the FastAPI app."""
    from main import app
    return TestClient(app, raise_server_exceptions=False)


API_KEY = "test-admin-key-123"
HEADERS = {"X-API-Key": API_KEY}
BAD_HEADERS = {"X-API-Key": "wrong-key"}


class TestAdminAuth:
    """All /api/ endpoints should require valid API key."""

    def test_no_key_returns_403(self, client):
        resp = client.get("/api/overview")
        assert resp.status_code == 403

    def test_wrong_key_returns_403(self, client):
        resp = client.get("/api/overview", headers=BAD_HEADERS)
        assert resp.status_code == 403

    def test_valid_key_succeeds(self, client):
        resp = client.get("/api/config", headers=HEADERS)
        assert resp.status_code == 200


class TestOverview:
    def test_overview_structure(self, client):
        resp = client.get("/api/overview", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "signals" in data
        assert "revenue" in data
        assert "dry_run" in data


class TestSignalsAPI:
    def test_list_signals(self, client):
        resp = client.get("/api/signals", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_list_signals_with_filter(self, client):
        resp = client.get("/api/signals?status=active&limit=10", headers=HEADERS)
        assert resp.status_code == 200

    def test_invalid_status_returns_400(self, client):
        resp = client.get("/api/signals?status=invalid_status", headers=HEADERS)
        assert resp.status_code == 400

    def test_signal_not_found(self, client):
        resp = client.get("/api/signals/999999", headers=HEADERS)
        assert resp.status_code == 404


class TestUsersAPI:
    def test_list_users(self, client):
        resp = client.get("/api/users", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data

    def test_user_not_found(self, client):
        resp = client.get("/api/users/999999", headers=HEADERS)
        assert resp.status_code == 404


class TestPaymentsAPI:
    def test_list_payments(self, client):
        resp = client.get("/api/payments", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data


class TestLearningAPI:
    def test_learning_progress(self, client):
        resp = client.get("/api/learning", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "feedback" in data
        assert "recent_lessons" in data


class TestCoinsAPI:
    def test_coins_used(self, client):
        resp = client.get("/api/coins", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "coins" in data
        assert isinstance(data["coins"], list)


class TestConfigAPI:
    def test_config_returns_safe_data(self, client):
        resp = client.get("/api/config", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "environment" in data
        assert "dry_run" in data
        assert "pricing" in data
        # Should NOT contain secret keys
        assert "DEEPSEEK_API_KEY" not in str(data)
        assert "OPENAI_API_KEY" not in str(data)
        assert "NOWPAYMENTS_IPN_SECRET" not in str(data)


class TestDryRunToggle:
    def test_toggle_dry_run(self, client):
        # Enable
        resp = client.post("/api/settings/dry-run?enable=true", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["dry_run"] is True

        # Disable
        resp = client.post("/api/settings/dry-run?enable=false", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["dry_run"] is False


class TestLogsAPI:
    def test_logs_endpoint(self, client):
        resp = client.get("/api/logs", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

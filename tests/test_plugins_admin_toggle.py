from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware.auth import get_current_admin
from src.api.routes import plugins_admin
from src.modules.plugin_loader import PluginLoader


class _PaymentsLicense:
    def has_feature(self, name):
        return name == "payments"


class _FreeLicense:
    def has_feature(self, _name):
        return False


def test_google_play_plugin_can_be_toggled_without_restart(monkeypatch, tmp_path):
    monkeypatch.setenv("FLIREXA_PLUGIN_STATE_FILE", str(tmp_path / "plugin-state.json"))
    monkeypatch.setenv("GOOGLE_PLAY_BILLING_ENABLED", "0")
    monkeypatch.setattr(plugins_admin, "get_license_manager", lambda: _PaymentsLicense())

    app = FastAPI()
    app.include_router(plugins_admin.router)
    app.dependency_overrides[get_current_admin] = lambda: {"username": "admin"}
    plugin_root = Path(__file__).resolve().parents[1] / "plugins"
    loader = PluginLoader(plugin_root)
    loader.discover_and_load(license_manager=_PaymentsLicense(), fastapi_app=app)
    app.state.plugin_loader = loader

    client = TestClient(app)
    installed = client.get("/api/v1/plugins/installed")
    assert installed.status_code == 200
    google_play = next(item for item in installed.json() if item["name"] == "google-play-billing")
    assert google_play["operator_toggleable"] is True
    assert google_play["enabled"] is False
    assert google_play["configured"] is False

    enabled = client.patch(
        "/api/v1/plugins/google-play-billing/state",
        json={"enabled": True},
    )
    assert enabled.status_code == 200
    assert enabled.json()["restart_required"] is False

    installed = client.get("/api/v1/plugins/installed").json()
    google_play = next(item for item in installed if item["name"] == "google-play-billing")
    assert google_play["enabled"] is True
    assert google_play["effective_enabled"] is False

    disabled = client.patch(
        "/api/v1/plugins/google-play-billing/state",
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False


def test_google_play_plugin_cannot_be_enabled_without_payment_entitlement(monkeypatch, tmp_path):
    monkeypatch.setenv("FLIREXA_PLUGIN_STATE_FILE", str(tmp_path / "plugin-state.json"))
    monkeypatch.setattr(plugins_admin, "get_license_manager", lambda: _FreeLicense())

    app = FastAPI()
    app.include_router(plugins_admin.router)
    app.dependency_overrides[get_current_admin] = lambda: {"username": "admin"}
    plugin_root = Path(__file__).resolve().parents[1] / "plugins"
    loader = PluginLoader(plugin_root)
    loader.discover_and_load(license_manager=_FreeLicense(), fastapi_app=app)
    app.state.plugin_loader = loader

    response = TestClient(app).patch(
        "/api/v1/plugins/google-play-billing/state",
        json={"enabled": True},
    )
    assert response.status_code == 403

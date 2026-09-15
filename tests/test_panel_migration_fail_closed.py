from __future__ import annotations

import pytest

from src.modules import panel_migration


class _SSH:
    def close(self):
        return None


def _secrets(token: str) -> dict:
    return {
        "cfg": {"host": "203.0.113.40", "port": 22, "user": "root"},
        "vendor": {"secret": "vendor-secret"},
        "source": {"license_key": "source-key"},
    }[token]


@pytest.mark.parametrize("status", ["cutting_over", "recovery_required"])
def test_new_migration_is_blocked_during_unfinished_handoff(monkeypatch, status):
    monkeypatch.setattr(panel_migration, "_load", lambda: {"status": status})
    with pytest.raises(RuntimeError, match="already active"):
        panel_migration.start({"host": "203.0.113.40", "port": 22})


def test_unknown_authority_after_source_freeze_stays_fail_closed(monkeypatch, tmp_path):
    state = {
        "status": "ready",
        "sealed": "cfg",
        "vendor_secret": "vendor",
        "vendor_session_id": "session-1",
        "target_instance_id": "target-instance",
        "steps": [],
    }
    service_actions: list[str] = []
    env_updates: list[dict[str, str]] = []

    monkeypatch.setenv("LICENSE_KEY", "source-key")
    monkeypatch.setattr(panel_migration, "_load", lambda: state)
    monkeypatch.setattr(panel_migration, "_save", lambda value: None)
    monkeypatch.setattr(panel_migration, "_open", _secrets)
    monkeypatch.setattr(panel_migration, "_seal", lambda value: "source")
    monkeypatch.setattr(panel_migration, "SSH", lambda cfg: _SSH())
    monkeypatch.setattr(panel_migration, "_local_maintenance", lambda enabled: None)
    monkeypatch.setattr(
        panel_migration, "_services", lambda action, include_api=False: service_actions.append(action)
    )
    monkeypatch.setattr(
        panel_migration, "_create_verified_backup",
        lambda label: {"archive_path": str(tmp_path / "snapshot.tar.gz")},
    )
    monkeypatch.setattr(panel_migration, "_create_web_bundle", lambda: None)
    monkeypatch.setattr(panel_migration, "_transfer_and_restore_snapshot", lambda *a, **k: None)
    monkeypatch.setattr(panel_migration, "_restore_web_bundle", lambda *a, **k: None)
    monkeypatch.setattr(panel_migration, "_remote_env", lambda *a, **k: None)
    monkeypatch.setattr(panel_migration, "_restart_remote_api_fenced", lambda *a, **k: None)
    monkeypatch.setattr(panel_migration, "_remote_services", lambda *a, **k: None)
    monkeypatch.setattr(panel_migration, "_local_env", lambda values: env_updates.append(values))
    monkeypatch.setattr(panel_migration, "_restart_local_api_detached", lambda: None)
    monkeypatch.setattr(
        panel_migration, "_vendor",
        lambda path, payload: (_ for _ in ()).throw(RuntimeError("authority unavailable")),
    )

    with pytest.raises(RuntimeError, match="authority unavailable"):
        panel_migration.cutover()

    assert state["status"] == "recovery_required"
    assert state["authority_status"] == "unknown"
    assert {"FLIREXA_MIGRATION_STANDBY": "1", "LICENSE_KEY": ""} in env_updates
    assert service_actions == ["stop"]


def test_recovery_can_cancel_prepared_authority_and_restore_source(monkeypatch):
    state = {
        "status": "recovery_required",
        "sealed": "cfg",
        "vendor_secret": "vendor",
        "source_license_secret": "source",
        "vendor_session_id": "session-1",
        "steps": [],
    }
    calls: list[str] = []

    monkeypatch.setattr(panel_migration, "_load", lambda: state)
    monkeypatch.setattr(panel_migration, "_save", lambda value: None)
    monkeypatch.setattr(panel_migration, "_open", _secrets)
    monkeypatch.setattr(
        panel_migration,
        "_vendor",
        lambda path, payload: calls.append(path) or {"status": "prepared" if path == "status" else "cancelled"},
    )
    monkeypatch.setattr(
        panel_migration, "SSH", lambda cfg: (_ for _ in ()).throw(RuntimeError("target offline"))
    )
    monkeypatch.setattr(panel_migration, "_local_env", lambda values: calls.append("local_env"))
    monkeypatch.setattr(panel_migration, "_local_maintenance", lambda enabled: calls.append("maintenance"))
    monkeypatch.setattr(panel_migration, "_services", lambda action: calls.append(action))
    monkeypatch.setattr(panel_migration, "_restart_local_api_detached", lambda: None)

    result = panel_migration.rollback()

    assert result["status"] == "rolled_back"
    assert calls == ["status", "cancel", "local_env", "maintenance", "restart"]
    assert "sealed" not in state
    assert "vendor_secret" not in state
    assert "source_license_secret" not in state

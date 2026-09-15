"""Contracts for trial-expiry UX and effective entitlement synchronization."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.api.routes.system import _effective_license_status
from src.modules.license.manager import LicenseInfo, LicenseManager, LicenseType


def _enterprise_status(*, expires_at=None, is_trial=False, trial_days=None):
    return {
        "server_id": "test-server",
        "license_type": "enterprise",
        "type": "enterprise",
        "plan": "enterprise",
        "billing_type": "lifetime" if not is_trial else "trial",
        "enforcement": "lifetime_protected" if not is_trial else "subscription",
        "is_valid": True,
        "is_trial": is_trial,
        "trial_duration_days": trial_days,
        "max_clients": 999999,
        "max_servers": 999999,
        "features": ["wireguard", "white_label", "manager_rbac"],
        "expires_at": expires_at,
        "days_remaining": None,
        "grace_period": False,
        "message": "License validated: enterprise",
    }


def test_manager_exposes_seven_day_enterprise_trial_metadata():
    issued_at = datetime.now(timezone.utc)
    manager = LicenseManager(None)
    manager._license_info = LicenseInfo(
        type=LicenseType.ENTERPRISE,
        max_clients=999999,
        max_servers=999999,
        features=["wireguard", "white_label"],
        issued_at=issued_at,
        expires_at=issued_at + timedelta(days=7),
        billing_type="trial",
        license_type="subscription",
    )

    status = manager.get_status()

    assert status["is_trial"] is True
    assert status["trial_duration_days"] == 7
    assert status["plan"] == "enterprise"


def test_revoked_paid_entitlement_returns_effective_community_surface():
    status = _effective_license_status(
        _enterprise_status(),
        online_blocked=True,
        online_reason="License revoked",
        has_license_key=True,
    )

    assert status["is_blocked"] is True
    assert status["entitlement_state"] == "blocked"
    assert status["license_type"] == "free"
    assert status["type"] == "free"
    assert status["plan"] == "free"
    assert status["max_clients"] == 20
    assert status["max_servers"] == 1
    assert set(status["features"]) == {"wireguard", "amneziawg", "telegram_bots"}
    assert status["signed_license_type"] == "enterprise"
    assert "white_label" in status["signed_features"]
    assert status["blocked_reason"] == "License revoked"


def test_cached_seven_day_trial_downgrades_immediately_after_expiry():
    expired_at = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    status = _effective_license_status(
        _enterprise_status(expires_at=expired_at, is_trial=True, trial_days=7),
        online_blocked=False,
        has_license_key=True,
    )

    assert status["is_blocked"] is True
    assert status["type"] == "free"
    assert status["is_trial"] is False
    assert status["signed_is_trial"] is True
    assert status["signed_trial_duration_days"] == 7


def test_lifetime_keeps_paid_surface_while_offline_lease_is_valid():
    original = _enterprise_status()
    status = _effective_license_status(
        original,
        online_blocked=False,
        has_license_key=True,
    )

    assert status["is_blocked"] is False
    assert status["type"] == "enterprise"
    assert status["enforcement"] == "lifetime_protected"
    assert "white_label" in status["features"]


def test_plain_community_install_is_not_mistaken_for_a_revoked_license():
    status = _effective_license_status(
        {
            "license_type": "free",
            "type": "free",
            "plan": "free",
            "features": ["wireguard", "amneziawg", "telegram_bots"],
            "message": "No license key — running in FREE mode",
        },
        online_blocked=False,
        has_license_key=False,
    )

    assert status["is_blocked"] is False
    assert status["entitlement_state"] == "active"


def test_trial_modal_and_live_license_refresh_are_wired_into_design2():
    root = Path(__file__).resolve().parents[1]
    app = (root / "src/web/frontend/src/App.vue").read_text(encoding="utf-8")
    api = (root / "src/web/frontend/src/api/index.js").read_text(encoding="utf-8")
    shell = (root / "src/web/frontend/src/design2/shell/D2Shell.vue").read_text(encoding="utf-8")
    settings = (root / "src/web/frontend/src/design2/screens/D2Settings.vue").read_text(encoding="utf-8")
    modal = (root / "src/web/frontend/src/design2/shell/D2TrialExpiryModal.vue").read_text(encoding="utf-8")

    assert "<D2TrialExpiryModal />" in app
    assert "window.setInterval(refreshLicense, 60 * 1000)" in app
    assert "flirexa:license-invalidated" in app
    assert "flirexa:license-invalidated" in api
    assert "licensePayload?.license_blocked" in api
    assert "LICENSE_RECOVERY_NAV" in shell
    assert "license.blocked" in shell
    assert "!licenseStore.blocked || ['license', 'updates'].includes(s.key)" in settings
    assert "license.trialDurationDays === 7" in modal
    assert "daysLeft.value <= 3" in modal
    assert "https://flirexa.biz/?billing=lifetime#pricing" in modal
    assert "Remind me tomorrow" in (root / "src/web/frontend/src/i18n/locales/en.js").read_text(encoding="utf-8")
    for language in ("ru", "de", "fr", "es"):
        localized = (root / f"src/web/frontend/src/i18n/design2/{language}.js").read_text(encoding="utf-8")
        assert '"trialExpiry"' in localized


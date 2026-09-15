"""Admin-facing descriptor for the Google Play Billing integration."""

import os

from src.modules.plugin_loader import Plugin
from src.modules.plugin_loader.state import is_plugin_enabled


class GooglePlayBillingPlugin(Plugin):
    def get_features(self):
        return ["payments", "google_play_billing"]

    def get_admin_status(self):
        # Never return credentials, paths, binding secrets, or RTDN tokens.
        from src.modules.subscription.google_play_billing import (
            GooglePlayConfigurationError,
            get_config,
        )

        legacy_default = os.getenv("GOOGLE_PLAY_BILLING_ENABLED", "0").strip().lower() in {
            "1", "true", "yes", "on",
        }
        operator_enabled = is_plugin_enabled(
            "google-play-billing", default=legacy_default,
        )
        try:
            config = get_config(require_enabled=False)
        except GooglePlayConfigurationError:
            return {
                "operator_enabled": operator_enabled,
                "configured": False,
                "effective_enabled": False,
                "configuration_error": True,
            }
        return {
            "operator_enabled": operator_enabled,
            "configured": bool(getattr(config, "configured", False)),
            "effective_enabled": config.enabled,
            "package_name": config.package_name if getattr(config, "configured", False) else "",
            "product_id": config.product_id if getattr(config, "configured", False) else "",
        }


PLUGIN = GooglePlayBillingPlugin({
    "name": "google-play-billing",
    "version": "1.0.0",
    "display_name": "Google Play Billing",
    "requires_license_feature": "payments",
})

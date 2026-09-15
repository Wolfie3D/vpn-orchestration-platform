"""Compatibility stub for a Flirexa commercial component.

The implementation is delivered only with the `payments` entitlement.
"""

FLIREXA_COMMERCIAL_STUB = True
REQUIRED_FEATURE = "payments"
_UPGRADE_HINT = (
    "This component requires the payments commercial entitlement. "
    "See https://flirexa.biz/#pricing for available plans."
)


from dataclasses import dataclass, field
import hashlib

class GooglePlayConfigurationError(RuntimeError):
    pass

class GooglePlayVerificationError(ValueError):
    pass

@dataclass(frozen=True)
class PlayConfig:
    enabled: bool = False
    package_name: str = 'us.aiii.back2home'
    product_id: str = 'unlimited_access'
    base_plans: dict = field(default_factory=dict)

def get_config(*, require_enabled=False):
    if require_enabled:
        raise GooglePlayConfigurationError(_UPGRADE_HINT)
    return PlayConfig()

def obfuscated_account_id(*args, **kwargs):
    raise GooglePlayConfigurationError(_UPGRADE_HINT)

def token_hash(purchase_token: str) -> str:
    return hashlib.sha256(purchase_token.encode('utf-8')).hexdigest()

async def verify_purchase(*args, **kwargs):
    raise GooglePlayConfigurationError(_UPGRADE_HINT)

def apply_verified_subscription(*args, **kwargs):
    raise GooglePlayConfigurationError(_UPGRADE_HINT)

async def acknowledge_purchase(*args, **kwargs):
    raise GooglePlayConfigurationError(_UPGRADE_HINT)

async def verify_pubsub_identity(*args, **kwargs):
    raise GooglePlayConfigurationError(_UPGRADE_HINT)

def decode_rtdn(*args, **kwargs):
    raise GooglePlayConfigurationError(_UPGRADE_HINT)

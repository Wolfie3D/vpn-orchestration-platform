"""Compatibility stub for a Flirexa commercial component.

The implementation is delivered only with the `server_migration` entitlement.
"""

FLIREXA_COMMERCIAL_STUB = True
REQUIRED_FEATURE = "server_migration"
_UPGRADE_HINT = (
    "This component requires the server_migration commercial entitlement. "
    "See https://flirexa.biz/#pricing for available plans."
)


def preflight(*args, **kwargs):
    raise RuntimeError(_UPGRADE_HINT)

def start(*args, **kwargs):
    raise RuntimeError(_UPGRADE_HINT)

def cutover(*args, **kwargs):
    raise RuntimeError(_UPGRADE_HINT)

def rollback(*args, **kwargs):
    raise RuntimeError(_UPGRADE_HINT)

def finalise(*args, **kwargs):
    raise RuntimeError(_UPGRADE_HINT)

def cancel(*args, **kwargs):
    raise RuntimeError(_UPGRADE_HINT)

def status() -> dict:
    return {'status': 'unavailable', 'steps': []}

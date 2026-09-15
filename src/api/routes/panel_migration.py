"""Compatibility stub for a Flirexa commercial component.

The implementation is delivered only with the `server_migration` entitlement.
"""

FLIREXA_COMMERCIAL_STUB = True
REQUIRED_FEATURE = "server_migration"
_UPGRADE_HINT = (
    "This component requires the server_migration commercial entitlement. "
    "See https://flirexa.biz/#pricing for available plans."
)


from fastapi import APIRouter

router = APIRouter()

"""Persistent operator switches for built-in Flirexa plugins.

The signed licence decides whether a plugin may run.  This small state store
adds a second, operator-controlled switch without editing ``.env`` and without
deleting the plugin or its data.  Callers must still enforce the licence gate.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from src.utils.runtime_paths import get_install_root


_LOCK = threading.RLock()
_STATE_FILE_ENV = "FLIREXA_PLUGIN_STATE_FILE"


def plugin_state_path() -> Path:
    override = os.getenv(_STATE_FILE_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return get_install_root() / "data" / "plugin_states.json"


def _read_states() -> dict[str, bool]:
    path = plugin_state_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(name): enabled for name, enabled in raw.items() if isinstance(enabled, bool)}


def is_plugin_enabled(name: str, *, default: bool = True) -> bool:
    """Return the persisted operator choice, or ``default`` when unset."""

    with _LOCK:
        return _read_states().get(name, default)


def set_plugin_enabled(name: str, enabled: bool) -> None:
    """Persist one switch atomically with owner-only permissions."""

    with _LOCK:
        states = _read_states()
        states[name] = bool(enabled)
        path = plugin_state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp")
        tmp.write_text(
            json.dumps(states, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)

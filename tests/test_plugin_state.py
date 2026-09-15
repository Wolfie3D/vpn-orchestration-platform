import json

from src.modules.plugin_loader.state import is_plugin_enabled, set_plugin_enabled


def test_plugin_state_uses_default_until_operator_persists_choice(monkeypatch, tmp_path):
    state_file = tmp_path / "plugin_states.json"
    monkeypatch.setenv("FLIREXA_PLUGIN_STATE_FILE", str(state_file))

    assert is_plugin_enabled("google-play-billing", default=False) is False
    assert is_plugin_enabled("google-play-billing", default=True) is True

    set_plugin_enabled("google-play-billing", True)
    assert is_plugin_enabled("google-play-billing", default=False) is True
    assert json.loads(state_file.read_text(encoding="utf-8")) == {
        "google-play-billing": True,
    }
    assert state_file.stat().st_mode & 0o777 == 0o600

    set_plugin_enabled("google-play-billing", False)
    assert is_plugin_enabled("google-play-billing", default=True) is False


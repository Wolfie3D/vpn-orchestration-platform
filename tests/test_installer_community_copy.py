"""Buyer-facing installer language must match the Community contract."""

from pathlib import Path


def test_installer_calls_the_unactivated_mode_community_edition():
    installer = Path("install.sh").read_text(encoding="utf-8")

    assert "install Community Edition" in installer
    assert "Running Community Edition (no activation needed)" in installer
    assert "Tier:${NC} Community Edition" in installer
    assert "up to 20 clients" in installer
    assert "one local VPN server total" in installer
    assert "7-Day Enterprise Trial or a purchased Starter, Business, or Enterprise plan" in installer

    assert "up to 80 clients" not in installer
    assert "install in FREE tier" not in installer
    assert "Running on FREE tier" not in installer


def test_installer_does_not_present_the_customer_portal_as_a_community_feature():
    installer = Path("install.sh").read_text(encoding="utf-8")
    community_summary = installer.split('echo -e "  ${BOLD}Tier:${NC} Community Edition', 1)[1]
    community_summary = community_summary.split('echo "  Management Commands:"', 1)[0]

    assert "Client self-service portal" not in community_summary
    assert "managed locations" in community_summary
    assert "Basic client management" in community_summary

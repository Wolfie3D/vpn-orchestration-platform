#!/usr/bin/env python3
"""Generate the canonical Flirexa sitemap and reciprocal language clusters."""

from pathlib import Path
from xml.sax.saxutils import escape


ORIGIN = "https://flirexa.biz"
LANGUAGES = ("en", "ru", "uk", "de", "fr", "es")
LAST_MODIFIED = "2026-09-08"
LOCALIZED_ROUTES = (
    "/",
    "/news.html",
    "/start-vpn-business/",
    "/white-label-vpn-platform/",
    "/pricing/",
    "/installation/",
    "/multi-server-vpn-management/",
    "/vpn-client-portal-billing/",
    "/security-reliability/",
    "/migrate-vpn-service/",
    "/protocols/",
    "/protocols/wireguard/",
    "/protocols/amneziawg/",
    "/protocols/hysteria2/",
    "/protocols/tuic/",
    "/protocols/vless-reality/",
    "/solutions/msp-vpn-platform/",
    "/solutions/hosting-provider-vpn-platform/",
    "/solutions/corporate-vpn-management/",
    "/guides/vpn-business-cost/",
    "/guides/vpn-server-capacity/",
)
SINGLE_LANGUAGE_ROUTES = ("/privacy.html", "/terms.html", "/demo/")


def localized_url(route: str, language: str) -> str:
    base = f"{ORIGIN}{route}"
    return base if language == "en" else f"{base}?lang={language}"


def url_entry(location: str, route: str | None = None) -> list[str]:
    lines = ["  <url>", f"    <loc>{escape(location)}</loc>", f"    <lastmod>{LAST_MODIFIED}</lastmod>"]
    if route is not None:
        alternates = (("x-default", localized_url(route, "en")),) + tuple(
            (language, localized_url(route, language)) for language in LANGUAGES
        )
        lines.extend(
            f'    <xhtml:link rel="alternate" hreflang="{language}" href="{escape(href)}"/>'
            for language, href in alternates
        )
    lines.append("  </url>")
    return lines


def render() -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for route in LOCALIZED_ROUTES:
        for language in LANGUAGES:
            lines.extend(url_entry(localized_url(route, language), route))
    for route in SINGLE_LANGUAGE_ROUTES:
        lines.extend(url_entry(f"{ORIGIN}{route}"))
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "landing" / "sitemap.xml"
    target.write_text(render(), encoding="utf-8")

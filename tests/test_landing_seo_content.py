from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import json
import re


LANDING = Path("landing")
SEO_ROUTES = {
    "/start-vpn-business/",
    "/white-label-vpn-platform/",
    "/multi-server-vpn-management/",
    "/vpn-client-portal-billing/",
    "/security-reliability/",
    "/migrate-vpn-service/",
    "/installation/",
    "/pricing/",
    "/demo/",
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
}

PROTOCOL_DETAIL_ROUTES = {
    "/protocols/wireguard/",
    "/protocols/amneziawg/",
    "/protocols/hysteria2/",
    "/protocols/tuic/",
    "/protocols/vless-reality/",
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title_parts = []
        self.descriptions = []
        self.canonicals = []
        self.robots = []
        self.h1_count = 0
        self.heading_tag = None
        self.heading_parts = []
        self.headings = []
        self.links = []
        self.resources = []
        self.open_graph = {}

    @property
    def title(self):
        return "".join(self.title_parts).strip()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.heading_tag = tag
            self.heading_parts = []
            if tag == "h1":
                self.h1_count += 1
        elif tag == "meta" and attrs.get("name", "").lower() == "description":
            self.descriptions.append(attrs.get("content", ""))
        elif tag == "meta" and attrs.get("name", "").lower() == "robots":
            self.robots.append(attrs.get("content", ""))
        elif tag == "link" and "canonical" in attrs.get("rel", "").split():
            self.canonicals.append(attrs.get("href", ""))
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        elif tag in ("img", "script") and attrs.get("src"):
            self.resources.append(attrs["src"])
        elif tag == "link" and attrs.get("href") and any(
            value in attrs.get("rel", "").split()
            for value in ("icon", "stylesheet")
        ):
            self.resources.append(attrs["href"])
        elif tag == "meta" and attrs.get("property", "").startswith("og:"):
            self.open_graph[attrs["property"]] = attrs.get("content", "")
            if attrs["property"] == "og:image":
                self.resources.append(attrs.get("content", ""))

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == self.heading_tag:
            heading = "".join(self.heading_parts).strip()
            if heading:
                self.headings.append(heading)
            self.heading_tag = None
            self.heading_parts = []

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.heading_tag:
            self.heading_parts.append(data)


class VisibleCopyParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip_depth = 0
        self.values = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "code", "pre", "svg", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "code", "pre", "svg", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        value = data.strip()
        if value and not self.skip_depth and any(character.isalpha() for character in value):
            self.values.append(value)


def route_file(route):
    return LANDING / route.strip("/") / "index.html"


def parse(path):
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def test_root_uses_the_shared_language_indexing_contract():
    page = (LANDING / "index.html").read_text(encoding="utf-8")
    assert '<link rel="canonical"' not in page
    assert '<script src="/seo-indexing.js?v=20260908-indexing1"></script>' in page

    indexing = (LANDING / "seo-indexing.js").read_text(encoding="utf-8")
    assert "lang === 'en' ? url" in indexing
    assert "rel', 'canonical'" in indexing
    assert "rel', 'alternate'" in indexing
    assert "code: 'x-default'" in indexing


def test_public_marketing_headings_do_not_end_in_periods():
    pages = [LANDING / "index.html", LANDING / "news.html", LANDING / "blog/plugins.html"]
    pages.extend(route_file(route) for route in sorted(SEO_ROUTES))
    for source in pages:
        assert all(
            not heading.rstrip().endswith(".") for heading in parse(source).headings
        ), f"heading ends in a period: {source}"


def test_indexable_seo_pages_have_unique_metadata_and_one_h1():
    titles = set()
    canonicals = set()
    for route in sorted(SEO_ROUTES):
        page = parse(route_file(route))
        assert page.title
        assert len(page.title) <= 70
        assert len(page.descriptions) == 1
        assert 90 <= len(page.descriptions[0]) <= 180
        assert page.h1_count == 1
        assert all(not heading.rstrip().endswith(".") for heading in page.headings)
        expected_canonical = f"https://flirexa.biz{route}"
        if route == "/demo/":
            assert page.canonicals == [expected_canonical]
        else:
            assert page.canonicals == []
            assert "/seo-indexing.js" in {
                urlparse(resource).path for resource in page.resources
            }
        assert page.open_graph.get("og:url") == expected_canonical
        assert page.open_graph.get("og:title")
        assert page.open_graph.get("og:description")
        assert page.open_graph.get("og:image")
        assert page.title not in titles
        assert expected_canonical not in canonicals
        titles.add(page.title)
        canonicals.add(expected_canonical)


def test_protocol_guides_have_a_discoverable_hub_and_compact_detail_pages():
    hub = route_file("/protocols/").read_text(encoding="utf-8")
    assert '<main class="seo-guide-page seo-protocol-page">' in hub
    assert hub.count('class="seo-protocol-card"') == 5
    for route in PROTOCOL_DETAIL_ROUTES:
        assert f'href="{route}"' in hub
        source = route_file(route).read_text(encoding="utf-8")
        assert '<header class="seo-hero">' not in source
        assert '<aside class="seo-cta">' not in source
        assert 'class="seo-protocol-tabs"' in source
        assert 'href="/protocols/"' in source
        for duplicate in (
            "same customer records, plan limits, server inventory, payments, and support workflows",
            "same customer portal, plans, payments, support, and server operations",
            "Compare commercial plans",
            "Compare plans",
        ):
            assert duplicate not in source

    root = (LANDING / "index.html").read_text(encoding="utf-8")
    shared = (LANDING / "seo-pages.js").read_text(encoding="utf-8")
    assert 'href="/protocols/"' in root
    assert "link('/protocols/', t.protocols)" in shared


def test_protocol_guides_have_complete_current_localizations_without_stale_free_copy():
    routes = {"/protocols/", *PROTOCOL_DETAIL_ROUTES}
    for route in routes:
        parser = VisibleCopyParser()
        parser.feed(route_file(route).read_text(encoding="utf-8"))
        route_key = route.strip("/").replace("/", "--")
        for language in ("ru", "uk", "de", "fr", "es"):
            payload = json.loads(
                (LANDING / "i18n-pages" / f"{route_key}.{language}.json").read_text(
                    encoding="utf-8"
                )
            )
            missing = set(parser.values) - set(payload["strings"])
            assert not missing, f"missing {language} translations for {route}: {missing}"
            serialized = json.dumps(payload, ensure_ascii=False)
            assert "FREE" not in serialized
            assert "80 customers" not in serialized
            assert "80 clients" not in serialized
            for corrupted_product_name in (
                "Истерия2",
                "Істерія2",
                "Hystérie2",
                "Histeria2",
                "рентгеновского излучения",
                "rayons X",
                "rayos X",
                "Röntgen",
            ):
                assert corrupted_product_name not in serialized


def test_start_vpn_business_uses_a_compact_two_section_guide_layout():
    source = route_file("/start-vpn-business/").read_text(encoding="utf-8")
    assert '<main class="seo-guide-page">' in source
    assert source.count('class="seo-section seo-guide-section') == 2
    assert '<header class="seo-hero">' not in source
    assert '<aside class="seo-cta">' not in source
    assert '<h1>Practical launch guide</h1>' in source
    assert "Choosing a plan" in source
    assert 'class="seo-table-wrap seo-guide-plan-table' in source
    for removed_copy in (
        "A realistic launch sequence",
        "What one installation solves and what remains yours",
        "Start with the operating boundary you actually need",
        "Do not buy a higher plan merely to avoid planning the service.",
        "What must exist before the first sale",
        "From zero to a working service",
        "Common questions",
        "Before you launch",
    ):
        assert removed_copy not in source
    shared = (LANDING / "seo-pages.js").read_text(encoding="utf-8")
    assert "START_VPN_BUSINESS_TABLE_STRINGS" in shared
    for language in ("ru", "uk", "de", "fr", "es"):
        assert f"{language}: {{" in shared


def test_customer_portal_page_uses_the_compact_self_service_guide_layout():
    source = route_file("/vpn-client-portal-billing/").read_text(encoding="utf-8")
    assert '<main class="seo-guide-page">' in source
    assert source.count('class="seo-section seo-guide-section') == 2
    assert 'data-seo-copy="portalGuideTitle"' in source
    assert '<header class="seo-hero">' not in source
    assert '<aside class="seo-cta">' not in source
    assert '<p class="seo-eyebrow">Payment choices</p>' in source
    assert 'class="seo-table-wrap seo-guide-plan-table' in source
    assert 'class="seo-guide-note">Flirexa integrates the checkout' in source
    for removed_copy in (
        "Fewer manual messages between customer and operator",
        "Use the providers your account and region support",
        "The customer path",
        "Account credit",
        "What customers and operators should expect",
    ):
        assert removed_copy not in source
    shared = (LANDING / "seo-pages.js").read_text(encoding="utf-8")
    assert "PORTAL_GUIDE_COPY" in shared


def test_economics_guide_keeps_only_cost_structure_and_model():
    source = route_file("/guides/vpn-business-cost/").read_text(encoding="utf-8")
    assert '<main class="seo-guide-page seo-economics-page">' in source
    assert source.count('class="seo-section seo-guide-section"') == 2
    assert 'seo-guide-stars-band--3' in source
    assert source.count('class="seo-card-icon"') == 3
    assert 'class="seo-table-wrap seo-guide-plan-table seo-economics-table"' in source
    assert '<header class="seo-hero">' not in source
    assert '<aside class="seo-cta">' not in source
    for removed_copy in (
        "Start narrow",
        "Before accepting a real payment",
        "Questions to answer",
        "How many servers should I buy first?",
    ):
        assert removed_copy not in source


def test_capacity_guide_keeps_measurement_and_load_testing_only():
    source = route_file("/guides/vpn-server-capacity/").read_text(encoding="utf-8")
    assert '<main class="seo-guide-page seo-capacity-page">' in source
    assert source.count('class="seo-section seo-guide-section"') == 3
    assert 'seo-guide-stars-band--4' in source
    assert 'class="seo-capacity-limits-band"' in source
    assert 'class="seo-guide-stars-band seo-guide-stars-band--4 seo-capacity-estimate-band"' in source
    assert source.index('class="seo-capacity-limits-band"') < source.index('seo-guide-stars-band--4')
    assert source.count('class="seo-card-icon"') == 7
    assert 'class="seo-table-wrap seo-guide-plan-table seo-capacity-table"' in source
    assert '<header class="seo-hero">' not in source
    assert '<aside class="seo-cta">' not in source
    for removed_copy in (
        "Signals to watch",
        "Scale up",
        "Common questions",
        "Can Flirexa guarantee a customer count per VPS size?",
    ):
        assert removed_copy not in source

    shared = (LANDING / "seo-pages.js").read_text(encoding="utf-8")
    assert "Предел пропускной способности" in shared
    assert "Одновременная нагрузка" in shared
    assert "Найдите предел до того, как его заметят клиенты" in shared


def test_merged_payment_provider_guidance_uses_shared_icons_and_table_emphasis():
    source = route_file("/vpn-client-portal-billing/").read_text(encoding="utf-8")
    assert 'class="seo-table-wrap seo-guide-plan-table seo-payment-table"' in source
    assert 'class="seo-grid seo-grid--three seo-icon-grid"' in source
    assert source.count('class="seo-card-icon"') == 3


def test_migration_page_uses_the_compact_two_section_guide_layout_and_localized_canary_label():
    source = route_file("/migrate-vpn-service/").read_text(encoding="utf-8")
    assert '<main class="seo-guide-page">' in source
    assert source.count('class="seo-section seo-guide-section"') == 2
    assert '<header class="seo-hero">' not in source
    assert '<aside class="seo-cta">' not in source
    assert 'data-seo-copy="migrationGuideTitle"' in source
    assert 'What Flirexa can help move' in source
    assert 'Move your existing VPN service into Flirexa with no separate migration fee' not in source
    shared = (LANDING / "seo-pages.js").read_text(encoding="utf-8")
    assert 'MIGRATION_GUIDE_COPY' in shared
    for localized_label in (
        'Размер тестовой группы',
        'Розмір тестової групи',
        'Größe der Testgruppe',
        'Taille du groupe pilote',
        'Tamaño del grupo piloto',
    ):
        assert localized_label in shared


def test_multi_server_page_uses_the_compact_three_section_guide_layout():
    source = route_file("/multi-server-vpn-management/").read_text(encoding="utf-8")
    assert '<main class="seo-guide-page">' in source
    assert source.count('class="seo-section seo-guide-section') == 3
    assert '<header class="seo-hero">' not in source
    assert '<aside class="seo-cta">' not in source
    assert '<h1>Adding a location</h1>' in source
    assert '<h2>Central operations</h2>' in source
    assert '<h2>Protocol expansion and server expansion are separate</h2>' in source
    assert 'class="seo-table-wrap seo-guide-plan-table"' in source
    for removed_copy in (
        'Bootstrap the node, then keep operations in the panel',
        'One customer model across the network',
        'Plan boundary',
        'Production discipline',
        'Before adding the first remote node',
    ):
        assert removed_copy not in source
    assert 'MULTI_SERVER_PLAN_TABLE_STRINGS' in (LANDING / "seo-pages.js").read_text(encoding="utf-8")


def test_white_label_page_uses_the_compact_three_section_guide_layout():
    source = route_file("/white-label-vpn-platform/").read_text(encoding="utf-8")
    assert '<main class="seo-guide-page">' in source
    assert source.count('class="seo-section seo-guide-section"') == 4
    assert '<header class="seo-hero">' not in source
    assert '<aside class="seo-cta">' not in source
    assert '<h1>What white-label means here</h1>' in source
    assert '<h2>A coherent customer path</h2>' in source
    assert 'data-seo-copy="whiteLabelNoteLabel"' in source
    assert 'id="client-apps"' in source
    assert 'data-seo-copy="whiteLabelAppsTitle"' in source
    assert 'data-seo-copy="whiteLabelAppsNoteCopy"' in source
    assert 'class="seo-table-wrap seo-guide-plan-table white-label-plan-table"' in source
    for removed_copy in (
        'Built-in control of the surfaces customers actually see',
        'Connect the portal to your website without rebuilding billing',
        'Branding is the line between the plans',
        'Questions operators ask',
        'White-label without vague promises',
    ):
        assert removed_copy not in source
    shared = (LANDING / "seo-pages.js").read_text(encoding="utf-8")
    assert 'WHITE_LABEL_GUIDE_COPY' in shared
    assert 'whiteLabelNoteLabel' in shared


def test_security_page_uses_separate_network_paid_lifetime_and_payment_blocks():
    source = route_file("/security-reliability/").read_text(encoding="utf-8")
    assert '<main class="seo-guide-page">' in source
    assert source.count('class="seo-section seo-guide-section') == 4
    assert source.count('<div class="seo-band">') == 2
    assert '<header class="seo-hero">' not in source
    assert '<aside class="seo-cta">' not in source
    assert '<h1>Network contacts</h1>' in source
    assert 'data-seo-copy="paidLicencesTitle"' in source
    assert 'data-seo-copy="lifetimeLicencesTitle"' in source
    assert 'class="seo-fact-icon' not in source
    assert '<h2>Payments</h2>' in source
    assert 'class="seo-table-wrap seo-guide-plan-table"' in source
    for removed_copy in (
        'An operator should know which connections are part of the product and which can be disabled.',
        'A successful redirect is not a successful payment',
        'Paid and Lifetime licences',
        'Update and recovery',
        'Security claims in plain language',
    ):
        assert removed_copy not in source
    shared = (LANDING / "seo-pages.js").read_text(encoding="utf-8")
    assert 'SECURITY_GUIDE_COPY' in shared
    assert 'Работа Community Edition' in shared


def test_msp_page_uses_compact_separated_sections_without_duplicate_sales_cta():
    source = route_file("/solutions/msp-vpn-platform/").read_text(encoding="utf-8")
    assert '<main class="seo-guide-page seo-msp-page">' in source
    assert source.count('class="seo-section seo-guide-section"') == 3
    assert source.count('<div class="seo-band">') == 0
    assert 'class="seo-guide-stars-band seo-guide-stars-band--1 seo-msp-operating-band"' in source
    assert '<header class="seo-hero">' not in source
    assert '<aside class="seo-cta">' not in source
    assert '<h1 class="seo-visually-hidden">For MSPs and IT service providers</h1>' in source
    assert 'class="seo-msp-intro-card"' in source
    assert 'class="seo-table-wrap seo-guide-plan-table seo-msp-ownership-table"' in source
    assert source.count('class="seo-card-icon"') == 6
    assert source.count("seo-icon-grid") == 1
    assert source.index('class="seo-table-wrap seo-guide-plan-table seo-msp-ownership-table"') < source.index('class="seo-msp-intro-card"')
    assert ".seo-msp-ownership-table .seo-table" not in (LANDING / "seo-pages.css").read_text(encoding="utf-8")
    assert 'Operate customer VPN access without placing every client' not in source
    assert 'Model the managed service before choosing the licence' not in source
    assert 'href="/demo/">Explore Enterprise</a>' in source
    assert 'href="mailto:support@flirexa.biz">Discuss your deployment</a>' in source


def test_hosting_provider_page_keeps_only_the_compact_icon_grid():
    source = route_file("/solutions/hosting-provider-vpn-platform/").read_text(encoding="utf-8")
    css = (LANDING / "seo-pages.css").read_text(encoding="utf-8")
    assert '<main class="seo-guide-page seo-hosting-page">' in source
    assert source.count('class="seo-section seo-guide-section') == 2
    assert '<h1 class="seo-visually-hidden">For hosting providers and ISPs</h1>' in source
    assert 'class="seo-guide-stars-band seo-guide-stars-band--2 seo-provider-intro-band"' in source
    assert 'class="seo-provider-intro-card"' in source
    assert 'class="seo-provider-intro"' in source
    assert 'class="seo-section__head seo-hosting-strengths-head"' in source
    assert 'class="seo-grid seo-icon-grid seo-hosting-strengths-grid"' in source
    assert "Run the VPN servers in your own regions" in source
    assert 'href="/demo/">Inspect the platform</a>' in source
    assert 'href="/pricing/">View Enterprise</a>' in source
    assert ".seo-provider-intro{position:relative;z-index:1;width:100%;margin:0}" in css
    assert "font-size:21px" in css
    assert source.count('class="seo-card-icon"') == 6
    assert source.count("seo-icon-grid") == 1
    assert '<header class="seo-hero">' not in source
    assert '<aside class="seo-cta">' not in source
    for removed_copy in (
        "Add a VPN product without outsourcing the network or customer relationship",
        "Commercial reality",
        "The platform does not solve capacity economics for you",
        "Before launch, calculate egress cost",
        "Evaluate Enterprise against your existing provider stack",
    ):
        assert removed_copy not in source
    for language in ("ru", "uk", "de", "fr", "es"):
        localized = json.loads(
            (LANDING / "i18n-pages" / f"solutions--hosting-provider-vpn-platform.{language}.json").read_text(encoding="utf-8")
        )
        assert localized["strings"].get("For hosting providers and ISPs")


def test_corporate_vpn_page_keeps_three_compact_operating_blocks():
    source = route_file("/solutions/corporate-vpn-management/").read_text(encoding="utf-8")
    css = (LANDING / "seo-pages.css").read_text(encoding="utf-8")

    assert 'class="seo-guide-stars-band seo-guide-stars-band--4 seo-corporate-intro"' in source
    assert '<header class="seo-hero">' not in source
    assert source.count('class="seo-section"') == 2
    assert "Manage branches and remote access without moving the control plane" in source
    assert "Separate site connectivity from end-user subscriptions" not in source
    assert source.count('class="seo-card-icon"') == 3
    assert source.count("seo-icon-grid") == 1
    assert "Operational controls" in source
    assert "Topology is only useful when changes remain auditable" in source
    assert "Before building the topology" not in source
    assert "Map the sites before installing the first gateway" not in source
    assert '<aside class="seo-cta">' not in source
    assert ".seo-corporate-intro h1{" in css and "54px" in css
    assert ".seo-corporate-actions .seo-button{" in css
    assert ".seo-corporate-actions .seo-button:hover" in css


def test_marketing_tables_and_guide_icons_share_the_refined_surface_system():
    seo_css = (LANDING / "seo-pages.css").read_text(encoding="utf-8")
    root_css = (LANDING / "style.v2.css").read_text(encoding="utf-8")

    assert ".seo-table th+th,.seo-table td+td" in seo_css
    assert ".seo-table th:nth-child(even),.seo-table td:nth-child(even)" in seo_css
    assert ".seo-fact-icon" not in seo_css

    for selector in (
        ".flx-product-demo-card-icon",
        ".flx-interface-demo-icon",
        ".flx-usecase-icon",
        ".flx-pricing-plan-icon",
        ".flx-enterprise-trial-icon",
    ):
        assert selector in root_css
    assert "backdrop-filter:blur(12px)" in root_css


def test_selected_guide_cards_use_the_root_use_case_icon_surface():
    seo_css = (LANDING / "seo-pages.css").read_text(encoding="utf-8")
    expected_icons = {
        "/migrate-vpn-service/": (3, 1),
        "/multi-server-vpn-management/": (3, 1),
        "/white-label-vpn-platform/": (9, 2),
        "/security-reliability/": (4, 1),
    }

    for route, (icon_count, grid_count) in expected_icons.items():
        source = route_file(route).read_text(encoding="utf-8")
        assert source.count('class="seo-card-icon"') == icon_count
        assert source.count("seo-icon-grid") == grid_count
    assert "--seo-icon-hover-bg" in seo_css
    assert "backdrop-filter:blur(12px) saturate(1.18)" in seo_css
    assert seo_css.count(".seo-card:nth-child(6n+") >= 4
    assert "rgba(66,151,239,.32)" in seo_css
    assert "rgba(44,178,172,.29)" in seo_css
    assert "rgba(180,91,230,.29)" in seo_css
    assert ".seo-card:hover .seo-card-icon" in seo_css


def test_root_comparison_section_and_its_dead_links_are_removed():
    source = (LANDING / "index.html").read_text(encoding="utf-8")
    script = (LANDING / "app.v2.js").read_text(encoding="utf-8")
    css = (LANDING / "style.v2.css").read_text(encoding="utf-8")

    assert 'id="comparison"' not in source
    assert 'href="#comparison"' not in source
    assert "flx-comparison" not in source
    assert "#comparison" not in script
    assert "flx-comparison" not in css


def test_sitemap_contains_every_indexable_commercial_route():
    tree = ET.parse(LANDING / "sitemap.xml")
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = {node.text for node in tree.findall("s:url/s:loc", ns)}
    entries = tree.findall("s:url", ns)
    assert entries
    assert all(entry.find("s:lastmod", ns) is not None for entry in entries)
    for route in SEO_ROUTES:
        assert f"https://flirexa.biz{route}" in urls
    for retired_url in (
        "https://flirexa.biz/client-apps/",
        "https://flirexa.biz/compare/hiddify/",
        "https://flirexa.biz/compare/3x-ui/",
        "https://flirexa.biz/compare/wg-easy/",
        "https://flirexa.biz/blog/plugins.html",
    ):
        assert retired_url not in urls
    assert "https://flirexa.biz/guides/vpn-payment-providers/" not in urls


def test_sitemap_has_complete_reciprocal_language_clusters():
    tree = ET.parse(LANDING / "sitemap.xml")
    ns = {
        "s": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "x": "http://www.w3.org/1999/xhtml",
    }
    entries = tree.findall("s:url", ns)
    by_location = {entry.find("s:loc", ns).text: entry for entry in entries}
    localized_routes = (SEO_ROUTES - {"/demo/"}) | {
        "/",
        "/news.html",
    }
    languages = ("en", "ru", "uk", "de", "fr", "es")

    for route in localized_routes:
        expected = {
            language: f"https://flirexa.biz{route}"
            + ("" if language == "en" else f"?lang={language}")
            for language in languages
        }
        expected["x-default"] = expected["en"]
        for location in set(expected.values()):
            entry = by_location[location]
            alternates = {
                link.attrib["hreflang"]: link.attrib["href"]
                for link in entry.findall("x:link", ns)
            }
            assert alternates == expected

    assert len(entries) == len(localized_routes) * len(languages) + 3
    sitemap = (LANDING / "sitemap.xml").read_text(encoding="utf-8")
    assert "<priority>" not in sitemap
    assert "<changefreq>" not in sitemap


def test_sitemap_is_reproducible_from_the_guarded_generator():
    from scripts.generate_landing_sitemap import render

    assert (LANDING / "sitemap.xml").read_text(encoding="utf-8") == render()


def test_retired_payment_provider_guide_redirects_to_the_billing_section():
    source = route_file("/guides/vpn-payment-providers/").read_text(encoding="utf-8")
    assert '<meta name="robots" content="noindex,follow">' in source
    assert '<link rel="canonical" href="https://flirexa.biz/vpn-client-portal-billing/">' in source
    assert '/vpn-client-portal-billing/#payment-providers' in source
    assert "window.location.replace(target)" in source


def test_public_nginx_has_canonical_retired_and_consolidated_route_policy():
    source = (Path("deploy/nginx/flirexa-retired-marketing.conf")).read_text(
        encoding="utf-8"
    )
    for route in (
        "3x-ui",
        "hiddify",
        "marzban",
        "wg-easy",
        "customer-stories/back2home",
    ):
        assert route in source
    assert "return 410;" in source
    assert "return 301 /white-label-vpn-platform/#client-apps;" in source
    assert "return 301 /vpn-client-portal-billing/#payment-providers;" in source


def test_internal_root_links_on_seo_pages_resolve_locally():
    for route in sorted(SEO_ROUTES):
        source = route_file(route)
        for href in parse(source).links:
            if not href.startswith("/") or href.startswith("//"):
                continue
            path = urlparse(href).path
            if path in ("", "/"):
                continue
            target = LANDING / path.lstrip("/")
            if path.endswith("/"):
                target /= "index.html"
            assert target.exists(), f"{source} links to missing {href}"


def test_interactive_demo_apps_are_not_search_results():
    for relative in (
        "demo-next/index.html",
        "demo-next-apps/index.html",
        "demo-authentic/admin/index.html",
        "demo-authentic/portal/index.html",
    ):
        robots = " ".join(parse(LANDING / relative).robots).lower()
        assert "noindex" in robots


def test_home_product_demo_cards_open_the_authentic_admin_and_portal_demos_directly():
    source = (LANDING / "index.html").read_text(encoding="utf-8")
    assert 'class="flx-product-demo-card" href="/demo-authentic/admin/"' in source
    assert 'class="flx-product-demo-card" href="/demo-authentic/portal/#/login"' in source


def test_demo_picker_brand_is_not_a_link_or_full_width_click_target():
    source = (LANDING / "demo-next" / "demo.js").read_text(encoding="utf-8")
    overrides = (LANDING / "demo-next" / "demo-overrides.css").read_text(encoding="utf-8")
    assert '<div class="picker-brand">' in source
    assert '<a class="picker-brand"' not in source
    assert '.picker-brand .brand-mark.official' in overrides
    assert 'color: var(--text);' in overrides


def test_removed_guides_hub_has_no_sitemap_entry_or_remaining_internal_links():
    assert not (LANDING / "guides" / "index.html").exists()
    sitemap = (LANDING / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://flirexa.biz/guides/</loc>" not in sitemap

    sources = [LANDING / "index.html", LANDING / "news.html", LANDING / "blog/plugins.html"]
    sources.extend(route_file(route) for route in sorted(SEO_ROUTES))
    sources.extend(
        [
            LANDING / "demo-next" / "demo.js",
            LANDING / "seo-pages.js",
        ]
    )
    for source in sources:
        content = source.read_text(encoding="utf-8")
        assert 'href="/guides/"' not in content, source
        assert "link('/guides/'" not in content, source


def test_indexable_pages_reference_existing_local_assets():
    pages = [
        LANDING / "index.html",
        LANDING / "news.html",
        LANDING / "privacy.html",
        LANDING / "terms.html",
        LANDING / "blog/plugins.html",
    ]
    pages.extend(route_file(route) for route in sorted(SEO_ROUTES))
    for source in pages:
        for resource in parse(source).resources:
            parsed = urlparse(resource)
            if parsed.scheme and parsed.netloc != "flirexa.biz":
                continue
            path = parsed.path
            if not path or path == "/favicon.ico":
                continue
            target = LANDING / path.lstrip("/") if path.startswith("/") else source.parent / path
            assert target.exists(), f"{source} references missing asset {resource}"


def test_structured_data_is_valid_and_contains_no_invented_ratings():
    pages = [LANDING / "index.html"]
    pages.extend(route_file(route) for route in sorted(SEO_ROUTES))
    for source in pages:
        html = source.read_text(encoding="utf-8")
        blocks = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        for block in blocks:
            value = json.loads(block)
            assert "aggregateRating" not in json.dumps(value)


def test_retired_comparison_pages_are_removed_and_client_apps_redirects():
    for relative in (
        "compare/hiddify/index.html",
        "compare/3x-ui/index.html",
        "compare/wg-easy/index.html",
    ):
        assert not (LANDING / relative).exists()

    client_apps = (LANDING / "client-apps/index.html").read_text(encoding="utf-8")
    assert '<meta name="robots" content="noindex,follow">' in client_apps
    assert '<link rel="canonical" href="https://flirexa.biz/white-label-vpn-platform/">' in client_apps
    assert "/white-label-vpn-platform/#client-apps" in client_apps
    assert "window.location.replace(target)" in client_apps


def test_plugin_article_is_kept_out_of_search_until_plugin_release():
    source = (LANDING / "blog/plugins.html").read_text(encoding="utf-8")
    assert '<meta name="robots" content="noindex,follow">' in source


def test_enterprise_migration_promise_remains_on_the_dedicated_sales_surfaces():
    pricing = route_file("/pricing/").read_text(encoding="utf-8")
    migration = route_file("/migrate-vpn-service/").read_text(encoding="utf-8")
    root = (LANDING / "index.html").read_text(encoding="utf-8")

    assert "migration help" in pricing
    assert "Standard migration from an existing VPN service" not in pricing
    assert "no additional Flirexa migration charge" not in pricing
    assert "Migration is included in Enterprise" in migration
    assert "canary" in migration.lower()
    assert 'data-i18n="enterpriseFeat.8"' in root


def test_pricing_uses_compact_sections_and_a_localized_trial_sequence():
    pricing = route_file("/pricing/").read_text(encoding="utf-8")

    assert "Commercial plans" not in pricing
    assert "Three clear ways to operate commercially" not in pricing
    assert "Licensing and support" not in pricing
    assert "A straightforward commercial relationship" not in pricing
    assert 'class="seo-guide-stars-band seo-guide-stars-band--2 seo-pricing-matrix-band"' in pricing
    assert 'class="seo-guide-stars-band seo-guide-stars-band--3 seo-pricing-community-band"' in pricing
    assert 'class="seo-trial-steps"' in pricing
    assert pricing.count('role="listitem"') == 4
    assert 'class="seo-trial-step seo-trial-step--important"' in pricing
    assert 'data-seo-copy="trialStepImportant"' in pricing
    assert 'data-seo-copy="trialLead"' not in pricing
    assert 'class="seo-grid seo-grid--three seo-icon-grid seo-pricing-plan-grid"' in pricing
    assert pricing.count('class="seo-pricing-plan-price"') == 3
    assert pricing.count('class="seo-card-icon"') == 5
    assert 'data-seo-copy="finalTitle"' not in pricing

    css = (LANDING / "seo-pages.css").read_text(encoding="utf-8")
    assert ".seo-pricing-plan-price strong{" in css
    assert ".seo-pricing-plan-card{display:flex;min-width:0;min-height:410px" in css
    assert ".seo-pricing-plan-card .seo-card-icon{width:48px;height:48px" in css
    assert ".seo-trial-step--important{flex-direction:column;gap:8px;border:0;background:transparent;box-shadow:none}" in css
    assert ".seo-trial-step__attention{" in css and "text-shadow:" in css
    assert ".seo-pricing-plan-grid>.seo-pricing-plan-card:nth-child(3) .seo-pricing-plan-price strong{" in css

    for locale in ("ru", "uk", "de", "fr", "es"):
        payload = json.loads((LANDING / "i18n-pages" / f"pricing.{locale}.json").read_text(encoding="utf-8"))
        for key in ("trialStep1", "trialStep2", "trialStep3", "trialStep4", "trialStepImportant"):
            assert payload["copy"].get(key)


def test_news_and_legal_pages_have_current_search_contracts():
    news = (LANDING / "news.html").read_text(encoding="utf-8")
    assert "[object Object]" not in news
    assert "Latest · v1.6" not in news
    assert "Pro and higher" not in news
    assert '<main class="seo-news-page">' in news
    assert 'class="seo-news-flow"' in news
    assert 'class="seo-hero seo-news-hero"' in news
    assert 'class="seo-section seo-news-updates"' in news
    assert 'data-seo-copy="newsHeroTitle">Latest news from Flirexa</h1>' in news
    assert '<p class="seo-eyebrow">Product updates</p>' not in news
    assert news.count('class="seo-news-social"') == 3
    assert 'href="https://t.me/FLIREXA"' in news
    assert 'href="https://github.com/Flirexa/flirexa"' in news
    assert 'href="https://x.com/mark_kaori?s=11"' in news
    assert 'data-social="youtube"' not in news
    assert news.count('class="seo-article-card seo-news-card"') == 3
    for asset in ("portal-billing-light.png", "dashboard.png", "portal-dashboard-light.png"):
        assert f'src="/assets/{asset}"' in news
    assert (LANDING / "assets" / "news-hero-flirexa-v2.png").is_file()
    css = (LANDING / "seo-pages.css").read_text(encoding="utf-8")
    assert "url('/assets/news-hero-flirexa-v2.png')" in css
    assert ".seo-news-hero .seo-hero__inner{" in css and "text-align:left" in css
    assert ".seo-news-hero:after{content:none}" in css
    assert "news-space-stars" not in css
    assert ".seo-news-card{" in css and "background:#f7f8fc" in css
    assert ".seo-news-card__visual{" in css and "border-radius:50%" in css
    assert "seo-news-cta" not in news
    assert "See the current product" not in news
    shared = (LANDING / "seo-pages.js").read_text(encoding="utf-8")
    assert "ru: { newsHeroTitle: 'Главные новости Flirexa' }" in shared
    for name in ("news.html",):
        page = parse(LANDING / name)
        assert page.h1_count == 1
        assert page.canonicals == []
        assert "/seo-indexing.js" in {
            urlparse(resource).path for resource in page.resources
        }
        assert len(page.descriptions) == 1

    for name in ("privacy.html", "terms.html"):
        page = parse(LANDING / name)
        assert len(page.canonicals) == 1
        assert page.canonicals[0] == f"https://flirexa.biz/{name}"
        assert len(page.descriptions) == 1


def test_security_contact_has_a_canonical_public_policy():
    security = (LANDING / ".well-known/security.txt").read_text(encoding="utf-8")
    assert "Contact: mailto:support@flirexa.biz" in security
    assert "Canonical: https://flirexa.biz/.well-known/security.txt" in security
    assert "Policy: https://github.com/Flirexa/flirexa/blob/main/SECURITY.md" in security
    assert "Expires: 2027-08-01T00:00:00Z" in security


def test_organic_entry_pages_keep_first_party_analytics_and_support_access():
    pages = [LANDING / "news.html", LANDING / "blog/plugins.html"]
    pages.extend(
        route_file(route) for route in sorted(SEO_ROUTES) if route != "/demo/"
    )
    for source in pages:
        resources = {urlparse(resource).path for resource in parse(source).resources}
        assert "/seo-pages.js" in resources, (
            f"{source} is missing the organic-page analytics bridge"
        )

    script = (LANDING / "seo-pages.js").read_text(encoding="utf-8")
    for endpoint in (
        "/api/visit",
        "/api/heartbeat",
        "/api/analytics/event",
        "/api/copy-install",
    ):
        assert endpoint in script
    assert "/?support=1" in script

    root_script = (LANDING / "app.v2.js").read_text(encoding="utf-8")
    assert "new URLSearchParams(window.location.search).get('support') === '1'" in root_script
    assert "chat_manual_open" in root_script


def test_new_marketing_pages_offer_same_url_localized_content_without_seo_duplicates():
    pages = [LANDING / "news.html", LANDING / "blog/plugins.html"]
    pages.extend(
        route_file(route) for route in sorted(SEO_ROUTES) if route != "/demo/"
    )
    translation_dir = LANDING / "i18n-pages"
    assert translation_dir.is_dir()

    for source in pages:
        relative = source.relative_to(LANDING).as_posix()
        if relative.endswith("/index.html"):
            key = relative[: -len("/index.html")].replace("/", "--")
        else:
            key = relative.removesuffix(".html").replace("/", "--")
        parser = parse(source)
        for language in ("ru", "uk", "de", "fr", "es"):
            localized = translation_dir / f"{key}.{language}.json"
            payload = json.loads(localized.read_text(encoding="utf-8"))
            assert payload["title"]
            assert payload["description"]
            assert payload.get("strings") or payload.get("copy")
            assert "Flirexa" in payload["title"] or "Flirexa" in parser.title

    script = (LANDING / "seo-pages.js").read_text(encoding="utf-8")
    assert "var params = new URLSearchParams(window.location.search);" in script
    assert "if (params.has('lang'))" in script
    assert "history.replaceState" in script
    assert "'/i18n-pages/' + routeKey()" in script


def test_mobile_navigation_surfaces_demo_and_pricing_before_long_section_lists():
    index = (LANDING / "index.html").read_text(encoding="utf-8")
    root_css = (LANDING / "style.v2.css").read_text(encoding="utf-8")
    shared_navigation = (LANDING / "seo-pages.js").read_text(encoding="utf-8")
    shared_css = (LANDING / "seo-pages.css").read_text(encoding="utf-8")

    assert 'class="flx-mobile-site-menu__quick"' in index
    assert '<a href="#pricing" data-i18n="navPricing">' in index
    assert 'href="/pricing/" class="flx-enterprise-trial-details" data-i18n="trialLearnMore"' in index
    for label in ("Learn more", "Узнать подробнее", "Дізнатися більше", "Mehr erfahren", "En savoir plus", "Más información"):
        assert label in (LANDING / "i18n.v2.js").read_text(encoding="utf-8")
    assert ".flx-mobile-site-menu__quick" in root_css

    assert 'class="seo-mobile-nav__quick"' in shared_navigation
    assert "link('/demo/', t.demo) + link('/news.html', t.news) + link('/#pricing', t.pricing)" in shared_navigation
    assert ".seo-mobile-nav__quick" in shared_css
    assert "flx-mobile-quick-shine" in root_css
    assert "seo-mobile-quick-shine" in shared_css
    assert "prefers-reduced-motion:reduce" in root_css

    root_script = (LANDING / "app.v2.js").read_text(encoding="utf-8")
    assert "scrollToLandingHash" in root_script
    assert "alignTarget = hash === '#pricing'" in root_script


def test_translation_directory_has_no_retired_page_bundles():
    pages = [LANDING / "news.html", LANDING / "blog/plugins.html"]
    pages.extend(
        route_file(route) for route in sorted(SEO_ROUTES) if route != "/demo/"
    )
    expected = set()
    for source in pages:
        relative = source.relative_to(LANDING).as_posix()
        if relative.endswith("/index.html"):
            expected.add(relative[: -len("/index.html")].replace("/", "--"))
        else:
            expected.add(relative.removesuffix(".html").replace("/", "--"))
    actual = {
        path.name.rsplit(".", 2)[0]
        for path in (LANDING / "i18n-pages").glob("*.json")
    }
    assert actual == expected


def test_navigation_keeps_product_and_solutions_focused_without_a_resources_menu():
    index = (LANDING / "index.html").read_text(encoding="utf-8")
    shared = (LANDING / "seo-pages.js").read_text(encoding="utf-8")
    demo = (LANDING / "demo-next" / "demo.js").read_text(encoding="utf-8")

    required_routes = (
        "/white-label-vpn-platform/",
        "/solutions/hosting-provider-vpn-platform/",
        "/solutions/corporate-vpn-management/",
        "/installation/",
        "/protocols/",
    )
    for source in (index, shared, demo):
        for route in required_routes:
            assert route in source

    for source in (index, shared, demo):
        assert "/guides/vpn-payment-providers/" not in source
    assert '<summary><span data-i18n="navResources">Resources</span></summary>' not in index
    assert "'<details><summary>' + t.resources" not in shared
    assert "<summary>${t.resources}</summary>" not in demo

    assert 'href="/guides/vpn-business-cost/" data-i18n="pricingCostGuide"' in index
    installation = route_file("/installation/").read_text(encoding="utf-8")
    multi_server = route_file("/multi-server-vpn-management/").read_text(encoding="utf-8")
    billing = route_file("/vpn-client-portal-billing/").read_text(encoding="utf-8")
    assert 'href="/guides/vpn-server-capacity/" data-seo-copy="capacityLink"' in installation
    assert 'href="/guides/vpn-server-capacity/" data-seo-copy="capacityLink"' in multi_server
    assert 'id="payment-providers"' in billing
    assert 'data-seo-copy="providerGuideTitle"' in billing

    assert index.index('href="/news.html"') < index.index('href="#pricing"')
    assert "link('/news.html', t.news) +\n        link('/#pricing', t.pricing)" in shared
    assert "${link('/news.html', t.news)}\n        ${link('/#pricing', t.pricing)}" in demo


def test_selected_guide_blocks_cycle_four_generated_space_backgrounds():
    expected = {
        "start-vpn-business/index.html": "seo-guide-stars-band--1",
        "vpn-client-portal-billing/index.html": "seo-guide-stars-band--2",
        "multi-server-vpn-management/index.html": "seo-guide-stars-band--3",
    }
    for relative, class_name in expected.items():
        source = (LANDING / relative).read_text(encoding="utf-8")
        assert f"seo-guide-stars-band {class_name}" in source

    security = (LANDING / "security-reliability/index.html").read_text(encoding="utf-8")
    assert "seo-guide-stars-band seo-guide-stars-band--1" in security
    assert "seo-guide-stars-band seo-guide-stars-band--4" in security

    css = (LANDING / "seo-pages.css").read_text(encoding="utf-8")
    for number in range(1, 5):
        asset_name = f"guide-space-stars-{number}-v1.webp"
        asset = LANDING / "assets" / asset_name
        assert asset.read_bytes()[:4] == b"RIFF"
        assert asset_name in css
    assert ".seo-guide-stars-band{" in css
    assert "background-image:linear-gradient" in css
    assert "var(--guide-stars-image)" in css
    assert "background-size:cover" in css
    assert "@media(max-width:820px)" in css


def test_current_marketing_copy_does_not_use_em_dash_as_a_prose_separator():
    sources = [
        LANDING / "index.html",
        LANDING / "news.html",
        LANDING / "privacy.html",
        LANDING / "terms.html",
        LANDING / "blog/plugins.html",
        LANDING / "app.v2.js",
        LANDING / "i18n.v2.js",
        LANDING / "seo-pages.js",
    ]
    sources.extend(route_file(route) for route in sorted(SEO_ROUTES))
    sources.extend(sorted((LANDING / "i18n-pages").glob("*.json")))

    for source in sources:
        assert "—" not in source.read_text(encoding="utf-8"), (
            f"{source} contains an em dash in current public marketing copy"
        )


def test_marketing_conversion_buttons_share_one_primary_and_secondary_palette():
    root_css = (LANDING / "style.v2.css").read_text(encoding="utf-8")
    seo_css = (LANDING / "seo-pages.css").read_text(encoding="utf-8")

    for css in (root_css, seo_css):
        assert "--button-primary:linear-gradient(135deg,#7161f3 0%,#584ac8 100%)" in css
        assert "--button-primary-hover:linear-gradient(135deg,#8274f7 0%,#6657d8 100%)" in css
        assert "--button-secondary:" in css
        assert "background:var(--button-primary)" in css
        assert "background:var(--button-primary-hover)" in css
        assert "background:var(--button-secondary)" in css
        assert "background:var(--button-secondary-hover)" in css

    for selector in (
        '.flx-nav-actions [data-action="openEnterpriseTrial"]',
        ".flx-hero-action--primary",
        ".flx-interface-demo-button",
        ".flx-pricing-choose",
        ".flx-enterprise-trial-button",
        ".flx-case__trial",
        ".flx-cta-button--primary",
        ".flx-enterprise-trial-send",
        '[data-action="chatSend"]',
        '[data-action="payContinue"]',
    ):
        assert selector in root_css

    assert "background:var(--button-primary)" in (LANDING / "app.v2.js").read_text(encoding="utf-8")
    assert ".seo-button:not(.seo-button--secondary)" in seo_css
    assert ".seo-pricing-plan-card .seo-text-link" in seo_css

    demo_overrides = (LANDING / "demo-next" / "demo-overrides.css").read_text(encoding="utf-8")
    assert ".demo-site-cta {" in demo_overrides
    assert "linear-gradient(135deg, #7161f3 0%, #584ac8 100%)" in demo_overrides

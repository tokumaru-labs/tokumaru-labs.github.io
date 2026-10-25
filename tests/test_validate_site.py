"""Regression tests use disposable sites, including deliberately broken pages."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_site import Validator, annotation_escape  # noqa: E402

SITE = "https://tokumaru-labs.github.io"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


class SiteValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write("asset.png", "image fixture")
        self.write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
        self.write("google9e6b85ab3daa42f4.html", "google-site-verification: google9e6b85ab3daa42f4.html\n")
        self.urls = ["/", "/ja/", "/widget/", "/ja/widget/", "/midnight-cockpit/", "/progress-sidecar/privacy/"]
        for url in self.urls:
            path = url.lstrip("/") + "index.html"
            lang = "ja" if url.startswith("/ja/") or "/privacy/" in url else "en"
            base = url[3:] if url.startswith("/ja/") else url
            pair = base in {"/", "/widget/"}
            links = (f'<link rel="alternate" hreflang="en" href="{SITE}{base}">'
                     f'<link rel="alternate" hreflang="ja" href="{SITE}/ja{base}">') if pair else ""
            kind = "Organization" if url in {"/", "/ja/"} else "SoftwareApplication"
            entity = {"@context": "https://schema.org", "@type": kind, "name": "Fixture",
                      "url": SITE + ("/" if kind == "Organization" else url)}
            metadata = f'<meta property="og:url" content="{SITE}{url}">' + self.ld(entity)
            if "/privacy/" in url:
                metadata = ""
            self.write(path, f'<!doctype html><html lang="{lang}"><head>'
                       f'<link rel="canonical" href="{SITE}{url}">{links}{metadata}</head>'
                       '<body><main id="main"><a href="#main">Main</a>'
                       '<img src="/asset.png"></main></body></html>')
        for path, tokens in (("stats/index.html", "noindex,nofollow,noarchive"),
                             ("404.html", "noindex, follow"),
                             ("after-hours/index.html", "noindex,nofollow,noarchive"),
                             ("toku-chime/index.html", "noindex")):
            self.write(path, '<html lang="ja"><head>'
                       f'<meta name="robots" content="{tokens}"></head>'
                       '<body><a href="/widget/#main">Tool</a></body></html>')
        self.sitemap(self.urls)

    def write(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8")

    def replace(self, path, before, after):
        original = (self.root / path).read_text(encoding="utf-8")
        self.assertIn(before, original, "Mutation must actually change the fixture")
        self.write(path, original.replace(before, after))

    def add_body(self, text, path="widget/index.html"):
        self.replace(path, "</body>", text + "</body>")

    def sitemap(self, urls):
        self.write("sitemap.xml", f'<urlset xmlns="{NS}">' + "".join(
            f"<url><loc>{SITE}{url}</loc><lastmod>2024-02-29</lastmod></url>" for url in urls) + "</urlset>")

    @staticmethod
    def ld(data):
        return '<script type="application/ld+json">' + json.dumps(data) + '</script>'

    def validate(self):
        # These patches fail the test if validation ever starts using the network.
        with patch("socket.create_connection", side_effect=AssertionError("Network is forbidden")), \
             patch("urllib.request.urlopen", side_effect=AssertionError("Network is forbidden")):
            return Validator(self.root).run()

    def assertPass(self):
        result = self.validate()
        self.assertEqual([], result.issues, result.markdown())
        return result

    def assertError(self, code, contains=""):
        result = self.validate()
        self.assertTrue(any(i.code == code and contains in i.message for i in result.issues), result.markdown())
        return result

    def test_valid_site_and_all_documented_exceptions(self):
        result = self.assertPass()
        self.assertEqual(10, len(result.pages))
        self.assertEqual(7, len(result.used_exceptions))

    def test_statistics_page_must_remain_unindexed(self):
        self.write("stats/index.html", '<html lang="ja"><head></head><body>Stats</body></html>')
        self.assertError("hidden", "robots")

    def test_statistics_page_cannot_enter_sitemap(self):
        p = self.root / "sitemap.xml"
        text = p.read_text().replace("</urlset>", '<url><loc>https://tokumaru-labs.github.io/stats/</loc><lastmod>2026-10-24</lastmod></url></urlset>')
        p.write_text(text)
        self.assertError("sitemap", "intentionally hidden")

    def test_relative_absolute_encoded_query_and_legacy_anchors(self):
        self.add_body('<a name="legacy"></a><p id="日本語"></p>'
                      '<a href="../widget/?mode=1&amp;x=2#%E6%97%A5%E6%9C%AC%E8%AA%9E">encoded</a>'
                      f'<a href="{SITE}/widget/index.html#legacy">absolute</a>'
                      '<a href="#top">top</a><a href="#">empty</a>'
                      '<a href="#main:~:text=Main">text fragment</a>')
        self.assertPass()

    def test_external_and_non_http_links_are_not_fetched(self):
        self.add_body('<a href="https://offline.invalid/x#not-local">external</a>'
                      '<a href="//offline.invalid/test">protocol-relative</a>'
                      '<a href="mailto:test@example.invalid">mail</a><a href="tel:123">tel</a>'
                      '<img src="data:image/png;base64,eA==">')
        self.assertEqual(2, len(self.assertPass().external))

    def test_missing_file_and_directory_without_index(self):
        (self.root / "empty").mkdir()
        self.add_body('<a href="/empty/">empty</a><a href="/absent.html">missing</a>')
        result = self.assertError("reference", "/absent.html")
        self.assertTrue(any("/empty/" in i.message for i in result.issues))

    def test_missing_fragment_on_another_page(self):
        self.add_body('<a href="/ja/widget/?q=1#absent">bad</a>')
        self.assertError("anchor", "#absent")

    def test_duplicate_anchor(self):
        self.add_body('<div id="main"></div>')
        self.assertError("anchor", "Duplicate")

    def test_missing_image_and_srcset_candidate(self):
        self.add_body('<picture><source srcset="/asset.png 1x, /missing.webp 2x">'
                      '<img src="/missing.png"></picture>')
        result = self.assertError("reference", "/missing.webp")
        self.assertTrue(any("/missing.png" in i.message for i in result.issues))

    def test_data_srcset_does_not_create_a_fake_local_target(self):
        self.add_body('<img srcset="data:image/png;base64,eA== 1x, /asset.png 2x">')
        self.assertPass()

    def test_og_image_exists(self):
        self.replace("widget/index.html", "</head>", '<meta property="og:image" content="/gone.png"></head>')
        self.assertError("reference", "/gone.png")

    def test_symlink_and_encoded_traversal_cannot_escape_root(self):
        self.add_body('<a href="/%2e%2e/outside.html">outside</a>')
        self.assertError("reference", "escapes")

    def test_base_tag_requires_explicit_support(self):
        self.replace("widget/index.html", "</head>", '<base href="/elsewhere/"></head>')
        self.assertError("reference", "base elements")

    def test_noncanonical_same_host_reference_is_rejected(self):
        self.add_body('<a href="http://tokumaru-labs.github.io/widget/">http</a>')
        self.assertError("reference", "HTTPS")

    def test_canonical_missing_duplicate_and_wrong_each_fail(self):
        path = "widget/index.html"
        original = (self.root / path).read_text()
        tag = f'<link rel="canonical" href="{SITE}/widget/">'
        for replacement in ("", tag + tag, tag.replace("/widget/", "/ja/widget/"), tag.replace(SITE, "")):
            with self.subTest(replacement=replacement):
                self.write(path, original.replace(tag, replacement))
                self.assertError("canonical")

    def test_canonical_in_body_cannot_satisfy_head_requirement(self):
        tag = f'<link rel="canonical" href="{SITE}/widget/">'
        self.replace("widget/index.html", tag, "")
        self.add_body(tag)
        self.assertError("canonical")

    def test_og_url_disagrees_with_canonical(self):
        self.replace("widget/index.html", f'property="og:url" content="{SITE}/widget/"',
                     f'property="og:url" content="{SITE}/ja/widget/"')
        self.assertError("og-url")

    def test_hreflang_missing_self_and_reciprocal_link(self):
        self.replace("ja/widget/index.html", f'<link rel="alternate" hreflang="en" href="{SITE}/widget/">', "")
        self.assertError("hreflang", "reciprocal")

    def test_hreflang_duplicate_wrong_language_and_wrong_pair(self):
        self.replace("widget/index.html", 'hreflang="ja"', 'hreflang="en"')
        self.replace("ja/widget/index.html", '<html lang="ja">', '<html lang="en">')
        self.assertError("hreflang")

    def test_adding_a_counterpart_removes_single_language_exception(self):
        self.write("ja/midnight-cockpit/index.html", (self.root / "midnight-cockpit/index.html").read_text())
        result = self.assertError("hreflang")
        self.assertTrue(any(i.path == "midnight-cockpit/index.html" and i.code == "hreflang" for i in result.issues))

    def test_optional_x_default_is_checked_when_present(self):
        self.replace("widget/index.html", "</head>", f'<link rel="alternate" hreflang="x-default" href="{SITE}/ja/widget/"></head>')
        self.assertError("hreflang", "x-default")

    def test_json_ld_syntax_shape_duplicates_constants_and_missing_entity(self):
        path = "widget/index.html"
        original = (self.root / path).read_text()
        start = original.index('<script type="application/ld+json">') + len('<script type="application/ld+json">')
        end = original.index('</script>', start)
        for broken in ('{"broken":', 'null', '[]', '{}', 'NaN', '{"name":"a","name":"b"}'):
            with self.subTest(broken=broken):
                self.write(path, original[:start] + broken + original[end:])
                self.assertError("json-ld")

    def test_json_ld_wrong_product_url(self):
        self.replace("widget/index.html", f'"url": "{SITE}/widget/"', f'"url": "{SITE}/ja/widget/"')
        self.assertError("json-ld", "SoftwareApplication.url")

    def test_json_ld_graph_and_array(self):
        entity = {"@type": "SoftwareApplication", "name": "Fixture", "url": SITE + "/widget/"}
        document = {"@context": "https://schema.org", "@graph": [entity]}
        self.add_body(self.ld([document]))
        self.assertPass()

    def test_json_ld_missing_local_download(self):
        self.replace("widget/index.html", '"name": "Fixture"', '"name": "Fixture", "downloadUrl": "/missing.zip"')
        self.assertError("reference", "/missing.zip")

    def test_sitemap_missing_duplicate_hidden_external_and_noncanonical_urls(self):
        for urls in (self.urls[1:], self.urls + ["/widget/"], self.urls + ["/after-hours/"],
                     self.urls + ["/toku-chime/index.html"], self.urls + ["/widget/index.html"]):
            with self.subTest(urls=urls):
                self.sitemap(urls)
                self.assertError("sitemap")
        self.sitemap(self.urls)
        self.replace("sitemap.xml", SITE, "https://example.invalid")
        self.assertError("sitemap")

    def test_sitemap_namespace_and_malformed_xml(self):
        self.replace("sitemap.xml", NS, "https://wrong.invalid")
        self.assertError("sitemap", "namespace")
        self.write("sitemap.xml", "<urlset>")
        self.assertError("sitemap", "Invalid XML")

    def test_sitemap_calendar_dates(self):
        for invalid in ("2025-02-29", "2026-13-01", "2026-04-31", "2026-1-01", "2026/01/01", "", "2026-01-01T00:00:00Z"):
            with self.subTest(invalid=invalid):
                self.sitemap(self.urls)
                self.replace("sitemap.xml", "2024-02-29", invalid)
                self.assertError("sitemap-date")

    def test_lastmod_is_required_exactly_once(self):
        self.replace("sitemap.xml", "<lastmod>2024-02-29</lastmod>", "")
        self.assertError("sitemap", "exactly one")

    def test_hidden_robots_directives_cannot_be_removed(self):
        for path, token in (("after-hours/index.html", "noindex"),
                            ("after-hours/index.html", "nofollow"),
                            ("after-hours/index.html", "noarchive"),
                            ("toku-chime/index.html", "noindex")):
            with self.subTest(path=path, token=token):
                original = (self.root / path).read_text()
                self.replace(path, token, "")
                self.assertError("hidden")
                self.write(path, original)

    def test_hidden_exception_still_validates_links_and_present_metadata(self):
        self.add_body('<a href="/gone/">broken</a>', "after-hours/index.html")
        self.replace("toku-chime/index.html", "</head>", '<link rel="canonical" href="/wrong/"></head>')
        self.assertError("reference", "/gone/")
        self.assertError("canonical")

    def test_public_noindex_and_conflicting_hidden_index(self):
        self.replace("widget/index.html", "</head>", '<meta name="robots" content="none"></head>')
        self.replace("toku-chime/index.html", 'content="noindex"', 'content="noindex,index"')
        self.assertError("robots", "indexable")
        self.assertError("hidden", "Conflicting")

    def test_noindex_must_be_in_head_and_bot_overrides_fail(self):
        self.replace("toku-chime/index.html", '<meta name="robots" content="noindex">', "")
        self.add_body('<meta name="robots" content="noindex">', "toku-chime/index.html")
        self.assertError("hidden")
        self.replace("after-hours/index.html", "</head>", '<meta name="googlebot" content="index"></head>')
        self.assertError("robots", "googlebot")

    def test_robots_crawl_access_including_bot_specific_rule(self):
        self.replace("robots.txt", "Allow: /", "Disallow: /toku-chime/")
        self.assertError("robots", "crawl")
        self.write("robots.txt", f"User-agent: Googlebot\nDisallow: /after-hours/\n\nUser-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
        self.assertError("robots", "Googlebot")

    def test_disallow_after_allow_and_wildcards_cannot_hide_noindex(self):
        original = (self.root / "robots.txt").read_text()
        for rule in ("/toku-chime/", "/toku-chime/*", "/after-hours/$"):
            with self.subTest(rule=rule):
                self.write("robots.txt", original + f"Disallow: {rule}\n")
                self.assertError("robots-policy", "Disallow")
        self.write("robots.txt", original + "Disallow: # empty is allowed\n")
        self.assertPass()

    def test_exception_deletion_and_verification_token_change_fail(self):
        (self.root / "after-hours/index.html").unlink()
        self.assertError("exception", "missing")
        self.write("google9e6b85ab3daa42f4.html", "wrong")
        self.assertError("verification")

    def test_cli_exit_status_json_summary_and_annotations(self):
        script = Path(__file__).resolve().parents[1] / "scripts/validate_site.py"
        report = self.root / "report.json"
        summary = self.root / "report.md"
        command = [sys.executable, str(script), "--root", str(self.root), "--json", str(report), "--summary", str(summary)]
        good = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(0, good.returncode, good.stdout + good.stderr)
        self.assertTrue(json.loads(report.read_text())["ok"])
        self.add_body('<a href="/missing/">bad</a>')
        bad = subprocess.run(command, capture_output=True, text=True, env={**os.environ, "GITHUB_ACTIONS": "true"})
        self.assertEqual(1, bad.returncode, bad.stderr)
        self.assertFalse(json.loads(report.read_text())["ok"])
        self.assertIn("**FAIL**", summary.read_text())
        self.assertIn("::error file=widget/index.html", bad.stdout)
        self.assertEqual("a%25%0A%0D%2Cb%3Ac", annotation_escape("a%\n\r,b:c"))


if __name__ == "__main__":
    unittest.main()

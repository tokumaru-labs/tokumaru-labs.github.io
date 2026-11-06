"""Offline fixtures exercise stale dates, meaningful changes and cosmetic edits."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sitemap_content import MANIFEST, check, fingerprint, read_manifest, snapshot


class SitemapContentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.page = self.root / "index.html"
        self.page.write_text('<html lang="en"><head><title>Tool</title>'
                             '<meta name="description" content="Local tool">'
                             '<script type="application/ld+json">{"name":"Tool","softwareVersion":"0.2.3"}</script>'
                             '</head><body><p>Version 0.2.3</p><a href="/v0.2.3.zip">Download</a>'
                             '<img src="/old.png" alt="Preview"></body></html>', encoding="utf-8")
        self.xml = self.root / "sitemap.xml"
        self.xml.write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                            '<url><loc>https://tokumaru-labs.github.io/</loc>'
                            '<lastmod>2026-10-25</lastmod></url></urlset>', encoding="utf-8")
        recorded = snapshot(self.root)
        recorded["index.html"]["reason"] = "Original release date reviewed"
        target = self.root / MANIFEST
        target.parent.mkdir()
        target.write_text(json.dumps(recorded), encoding="utf-8")

    def cli(self, *args):
        script = Path(__file__).resolve().parents[1] / "scripts/sitemap_content.py"
        return subprocess.run([sys.executable, "-B", str(script), "--root", str(self.root), *args],
                              capture_output=True, text=True)

    def errors(self):
        return check(snapshot(self.root), read_manifest(self.root))

    def test_clean_snapshot_needs_no_git_or_network(self):
        with patch("subprocess.run", side_effect=AssertionError("Git prohibited")), \
             patch("socket.socket.connect", side_effect=AssertionError("Network prohibited")):
            self.assertEqual([], self.errors())
        self.assertEqual(0, self.cli().returncode)

    def test_release_update_with_stale_sitemap_fails(self):
        self.page.write_text(self.page.read_text().replace("0.2.3", "0.3.0"))
        result = self.cli()
        self.assertEqual(1, result.returncode)
        self.assertIn("index.html: content or lastmod changed", result.stdout)

    def test_content_signals_are_independently_detected(self):
        html = self.page.read_text()
        for before, after in [("Version 0.2.3", "Version 0.3.0"), ("/v0.2.3.zip", "/v0.3.0.zip"),
                              ('"softwareVersion":"0.2.3"', '"softwareVersion":"0.3.0"'),
                              ("<title>Tool", "<title>New tool"), ("Local tool", "New description"),
                              ("/old.png", "/new.png"), ('alt="Preview"', 'alt="New preview"')]:
            with self.subTest(before=before):
                self.page.write_text(html.replace(before, after))
                self.assertTrue(self.errors())

    def test_cosmetic_changes_do_not_require_new_dates(self):
        html = self.page.read_text()
        changed = html.replace('<p>', '<p class="new" style="color:red">\n  ')
        changed = changed.replace('</head>', '<!-- comment --><style>p { color: red }</style>'
                                  '<script src="/new.js">console.log("changed")</script>'
                                  '<link rel="stylesheet" href="/new.css"></head>')
        changed = changed.replace('"name":"Tool","softwareVersion":"0.2.3"',
                                  '"softwareVersion": "0.2.3", "name": "Tool"')
        self.assertEqual(fingerprint(html), fingerprint(changed))

    def test_date_only_change_requires_review(self):
        self.xml.write_text(self.xml.read_text().replace("2026-10-25", "2026-10-27"))
        self.assertTrue(self.errors())

    def test_explicit_review_does_not_automatically_rewrite_dates(self):
        self.page.write_text(self.page.read_text().replace("0.2.3", "0.3.0"))
        before = self.xml.read_bytes()
        result = self.cli("--record", "index.html", "--lastmod", "2026-10-27", "--reason", "Release")
        self.assertEqual(1, result.returncode)
        self.assertEqual(before, self.xml.read_bytes())
        self.xml.write_text(self.xml.read_text().replace("2026-10-25", "2026-10-27"))
        result = self.cli("--record", "index.html", "--lastmod", "2026-10-27", "--reason", "Release")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([], self.errors())

    def test_same_day_or_minor_change_can_keep_reviewed_date(self):
        self.page.write_text(self.page.read_text().replace("Version 0.2.3", "Version 0.2.3 — corrected typo"))
        self.assertTrue(self.errors())
        self.assertEqual(1, self.cli("--record", "index.html", "--lastmod", "2026-10-25").returncode)
        self.assertEqual(0, self.cli("--record", "index.html", "--lastmod", "2026-10-25",
                                    "--reason", "Minor typo; substantive update date unchanged").returncode)
        self.assertEqual([], self.errors())

    def test_nonindexed_pages_are_not_added_to_manifest(self):
        (self.root / "hidden.html").write_text('<meta name="robots" content="noindex">Hidden')
        self.assertEqual([], self.errors())
        self.assertEqual(1, self.cli("--record", "hidden.html", "--lastmod", "2026-10-25",
                                    "--reason", "Not indexed").returncode)

    def test_missing_or_invalid_records_fail_closed(self):
        target = self.root / MANIFEST
        for content in ("{}", "[]", "broken", '{"index.html":{}}',
                        '{"other.html":{}}', '{"index.html":null}'):
            with self.subTest(content=content):
                target.write_text(content)
                self.assertEqual(1, self.cli().returncode)
        target.unlink()
        self.assertEqual(1, self.cli().returncode)

    def test_invalid_sitemap_fails_closed(self):
        xml = self.xml.read_text()
        for broken in ("<", xml.replace("2026-10-25", "2026-02-30"),
                       xml.replace("/</loc>", "/../outside.html</loc>"),
                       xml.replace("https://tokumaru-labs.github.io/", "https://example.com/")):
            with self.subTest(xml=broken):
                self.xml.write_text(broken)
                self.assertEqual(1, self.cli().returncode)


if __name__ == "__main__":
    unittest.main()

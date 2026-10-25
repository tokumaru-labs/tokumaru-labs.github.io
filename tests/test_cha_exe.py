"""Offline assurance for After Hours' unsigned CHA.EXE experiment."""
import hashlib
from pathlib import Path, PurePosixPath
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "after-hours/assets/CHA_EXE_Im_Still_Here.zip"
PREFIX = "CHA_EXE_machine_code/"
EXPECTED = {
    PREFIX + "CHA.exe",
    PREFIX + "build_cha.py",
    PREFIX + "verify_cha.py",
    PREFIX + "README.md",
    PREFIX + "SHA256SUMS.txt",
}
ZIP_SHA256 = "d92f5ab08ab2a4c162279d1b054a215c8b8c9818c2c2398f1544d36c9c2e8dc4"
EXE_SHA256 = "0391cac84bd25c18505db7a4586e931f3ba8fd4967f8b28b6d17128d80f0c3b2"


class TestChaExe(unittest.TestCase):
    def test_site_only_offers_explicit_zip_download(self):
        html = (ROOT / "after-hours/index.html").read_text(encoding="utf-8")
        self.assertIn('id="cha-exe-download"', html)
        self.assertIn('href="/after-hours/assets/CHA_EXE_Im_Still_Here.zip"', html)
        self.assertIn("Windows実機での起動は未確認", html)
        self.assertEqual(html.count('class="tool-card"'), 2)
        self.assertIn('name="robots" content="noindex,nofollow,noarchive"', html)
        self.assertNotIn("after-hours", (ROOT / "sitemap.xml").read_text(encoding="utf-8"))

    def test_package_hash_and_members(self):
        self.assertEqual(hashlib.sha256(PACKAGE.read_bytes()).hexdigest(), ZIP_SHA256)
        with ZipFile(PACKAGE) as archive:
            self.assertEqual(set(archive.namelist()), EXPECTED)
            self.assertIsNone(archive.testzip())
            for name in archive.namelist():
                path = PurePosixPath(name)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
            exe = archive.read(PREFIX + "CHA.exe")
            self.assertEqual(len(exe), 3072)
            self.assertEqual(hashlib.sha256(exe).hexdigest(), EXE_SHA256)
            self.assertEqual(
                archive.read(PREFIX + "SHA256SUMS.txt").decode("ascii").strip(),
                EXE_SHA256 + "  CHA.exe",
            )

    def test_handwritten_machine_code_is_reproducible(self):
        with ZipFile(PACKAGE) as archive, TemporaryDirectory() as tmp:
            archive.extractall(tmp)
            work = Path(tmp) / PREFIX
            check = subprocess.run(
                [sys.executable, "-B", "verify_cha.py"],
                cwd=work, text=True, capture_output=True, timeout=15,
                check=True,
            )
            self.assertIn("PASS:", check.stdout)
            self.assertIn(EXE_SHA256, check.stdout)


if __name__ == "__main__":
    unittest.main()

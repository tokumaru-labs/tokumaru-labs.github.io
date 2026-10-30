#!/usr/bin/env python3
"""Offline reminder to review lastmod when indexed HTML content changes."""

import argparse
from datetime import date
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from validate_site import ORIGIN, SITEMAP_NS

MANIFEST = "scripts/sitemap-content.json"


class Content(HTMLParser):
    """Fingerprint content signals, not CSS, executable JS or HTML formatting."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tokens = []
        self.skip = None
        self.ld = None
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style"}:
            self.skip = tag
            if tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
                self.ld = []
            return
        if self.skip:
            return
        if tag == "link" and not {"canonical", "alternate"} & set(attrs.get("rel", "").lower().split()):
            return
        if tag == "meta":
            name = attrs.get("name", attrs.get("property", "")).lower()
            if name and name not in {"viewport", "theme-color"}:
                self.tokens.append(("meta", name, attrs.get("content", "")))
            return
        meaningful = {k: v for k, v in attrs.items() if k in {
            "href", "src", "srcset", "poster", "alt", "title", "lang", "hreflang",
            "aria-label", "data-release-asset",
        }}
        if meaningful:
            self.tokens.append((tag, meaningful))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == self.skip:
            if self.ld is not None:
                self.tokens.append(("json-ld", json.loads("".join(self.ld))))
                self.ld = None
            self.skip = None

    def handle_data(self, data):
        if self.ld is not None:
            self.ld.append(data)
        elif not self.skip:
            text = " ".join(data.split())
            if text:
                self.tokens.append(("text", text))


def fingerprint(html):
    payload = json.dumps(Content(html).tokens, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def snapshot(root):
    """Only sitemap-listed pages; the existing validator enforces indexing policy."""
    result = {}
    tree = ET.parse(root / "sitemap.xml")
    if tree.getroot().tag != SITEMAP_NS + "urlset":
        raise ValueError("Invalid sitemap namespace")
    for entry in tree.getroot():
        locations = entry.findall(SITEMAP_NS + "loc")
        dates = entry.findall(SITEMAP_NS + "lastmod")
        if len(locations) != 1 or len(dates) != 1:
            raise ValueError("Each sitemap entry needs one loc and one lastmod")
        url = urlsplit(locations[0].text or "")
        modified = dates[0].text or ""
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", modified):
            raise ValueError(f"Invalid lastmod: {modified!r}")
        date.fromisoformat(modified)
        if f"{url.scheme}://{url.netloc}" != ORIGIN or url.query or url.fragment:
            raise ValueError(f"Invalid sitemap URL: {locations[0].text}")
        path = unquote(url.path).lstrip("/")
        if url.path.endswith("/"):
            path += "index.html"
        file = (root / path).resolve()
        if not file.is_relative_to(root.resolve()) or file.suffix != ".html":
            raise ValueError(f"Invalid page path: {path}")
        if path in result:
            raise ValueError(f"Duplicate page: {path}")
        result[path] = {"lastmod": modified, "sha256": fingerprint(file.read_text(encoding="utf-8"))}
    if not result:
        raise ValueError("Empty sitemap")
    return result


def read_manifest(root):
    data = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or any(not isinstance(v, dict) for v in data.values()):
        raise ValueError("Invalid sitemap content manifest")
    return data


def check(current, recorded):
    errors = []
    for path in sorted(current.keys() | recorded.keys()):
        if path not in current or path not in recorded:
            errors.append(f"{path}: sitemap/manifest page set differs; review addition or removal")
            continue
        old = recorded[path]
        if not isinstance(old.get("reason"), str) or not old["reason"].strip():
            errors.append(f"{path}: missing lastmod review reason")
        if any(old.get(key) != value for key, value in current[path].items()):
            errors.append(f"{path}: content or lastmod changed; review the actual content update date, "
                          "then record this page (see tests/README.md)")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--record", nargs="+", metavar="PAGE", help="Explicitly record reviewed page paths")
    parser.add_argument("--lastmod", help="Reviewed content date; must already match sitemap.xml")
    parser.add_argument("--reason", help="Why this is the actual update date, or why it is unchanged")
    args = parser.parse_args()
    try:
        current = snapshot(args.root)
        if args.record:
            if not args.lastmod or not args.reason or not args.reason.strip():
                raise ValueError("--record requires explicit --lastmod and --reason")
            for path in args.record:
                if path not in current or current[path]["lastmod"] != args.lastmod:
                    raise ValueError(f"{path}: --lastmod must match this sitemap-listed page")
            recorded = read_manifest(args.root) if (args.root / MANIFEST).exists() else {}
            for path in args.record:
                recorded[path] = {**current[path], "reason": args.reason.strip()}
            target = args.root / MANIFEST
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(recorded, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"Recorded {len(args.record)} reviewed pages; sitemap dates were not rewritten.")
            return 0
        if args.lastmod or args.reason:
            raise ValueError("--lastmod and --reason require --record")
        errors = check(current, read_manifest(args.root))
        for error in errors:
            print(error)
        print(f"Sitemap content review: {len(current)} pages, {len(errors)} errors")
        return int(bool(errors))
    except (OSError, ValueError, ET.ParseError) as error:
        print(f"Sitemap content review failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

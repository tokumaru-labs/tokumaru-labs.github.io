#!/usr/bin/env python3
"""Offline checks for the static site. Python 3.12+, standard library only."""

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urljoin, urlsplit
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

ORIGIN = "https://tokumaru-labs.github.io"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
# Exact paths, never wildcard suppressions. Present metadata is still validated.
HIDDEN = {
    "after-hours/index.html": {"noindex", "nofollow", "noarchive"},
    "toku-chime/index.html": {"noindex"},
    "404.html": {"noindex"},
}
POLICY = "progress-sidecar/privacy/index.html"
VERIFICATION = "google9e6b85ab3daa42f4.html"
EXCEPTIONS = {
    "after-hours/index.html": "Hidden launcher: no search metadata required; noindex/nofollow/noarchive and sitemap exclusion required.",
    "toku-chime/index.html": "Hidden app: no search metadata required; noindex and sitemap exclusion required.",
    "404.html": "Error page: no search metadata required; noindex and sitemap exclusion required.",
    POLICY: "One bilingual policy document: canonical required; hreflang, OG and JSON-LD optional.",
    "midnight-cockpit/index.html": "English-only product: no hreflang required while no Japanese counterpart exists.",
    VERIFICATION: "Search Console verification token, not an HTML page; exact content checked, excluded from sitemap.",
}
IGNORED_DIRS = {"node_modules", "__pycache__"}


def route(path):
    return "/" + (path[:-10] if path.endswith("index.html") else path)


def srcset_urls(value):
    """Read URL tokens separately from descriptors; preserve commas in data URLs."""
    rest = value.lstrip(" ,\t\r\n")
    while rest:
        match = re.match(r"\S+", rest)
        token = match.group()
        rest = rest[match.end():]
        yield token.rstrip(",")
        if not token.endswith(","):
            rest = rest.partition(",")[2]
        rest = rest.lstrip(" ,\t\r\n")


class Page(HTMLParser):
    def __init__(self, path, content):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.url = ORIGIN + route(path)
        self.elements = []
        self.ids = Counter()
        self.anchors = set()
        self.json_blocks = []
        self.in_head = False
        self.json_buffer = None
        self.feed(content)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "head":
            self.in_head = True
        line = self.getpos()[0]
        self.elements.append((tag, attrs, line, self.in_head))
        if attrs.get("id"):
            self.ids[attrs["id"]] += 1
            self.anchors.add(attrs["id"])
        if tag == "a" and attrs.get("name"):
            self.anchors.add(attrs["name"])
        if tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self.json_buffer = [line, ""]

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self.json_buffer is not None:
            self.json_buffer[1] += data

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False
        if tag == "script" and self.json_buffer is not None:
            self.json_blocks.append(tuple(self.json_buffer))
            self.json_buffer = None

    def links(self, relation):
        return [(attrs, line) for tag, attrs, line, head in self.elements
                if head and tag == "link" and relation in attrs.get("rel", "").lower().split()]

    def metas(self, name):
        return [(attrs.get("content", ""), line) for tag, attrs, line, head in self.elements
                if head and tag == "meta" and
                (attrs.get("property", "").lower() == name or attrs.get("name", "").lower() == name)]

    def robots(self):
        return {token for value, _ in self.metas("robots")
                for token in re.split(r"[\s,]+", value.lower()) if token}


@dataclass
class Issue:
    code: str
    path: str
    line: int
    message: str


class Validator:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.pages = {}
        self.issues = []
        self.checks = Counter()
        self.external = set()
        self.used_exceptions = {}

    def check(self, condition, code, path, message, line=1):
        self.checks[code] += 1
        if not condition:
            self.issues.append(Issue(code, path, line, message))
        return bool(condition)

    def reference(self, value, source, line, base=None):
        """Check an internal URL without making an HTTP request."""
        if not self.check(isinstance(value, str) and bool(value.strip()), "reference", source,
                          "Empty or non-string URL", line):
            return
        try:
            url = urlsplit(urljoin(base or ORIGIN + route(source), value.strip()))
            if url.scheme not in {"http", "https"}:
                self.check(url.scheme in {"mailto", "tel", "data", "blob"}, "reference", source,
                           f"Unsupported URL scheme: {url.scheme}", line)
                return
            if url.hostname != urlsplit(ORIGIN).hostname:
                self.external.add(value)
                return
            self.check(url.scheme == "https" and url.netloc == urlsplit(ORIGIN).netloc,
                       "reference", source, f"Use the HTTPS site origin: {value}", line)
            decoded = unquote(url.path, errors="strict")
            if "\x00" in decoded or "\\" in decoded:
                raise ValueError("invalid path character")
            target = (self.root / decoded.lstrip("/")).resolve()
            if not target.is_relative_to(self.root):
                raise ValueError("path escapes the site root")
            if target.is_dir():
                target /= "index.html"
            if not self.check(target.is_file(), "reference", source,
                              f"Missing local target: {value}", line):
                return
            fragment = unquote(url.fragment, errors="strict").split(":~:text=", 1)[0]
            target_page = self.pages.get(target.relative_to(self.root).as_posix())
            if fragment and target_page:
                self.check(fragment in target_page.anchors or fragment.lower() == "top",
                           "anchor", source, f"Missing anchor #{fragment} in {target_page.path}", line)
            # Non-HTML fragments (e.g. SVG views, PDF #page=2) are not HTML IDs.
        except (ValueError, UnicodeError, OSError) as error:
            self.check(False, "reference", source, f"Invalid local URL {value!r}: {error}", line)

    def load(self):
        for file in sorted(self.root.rglob("*.html")):
            path = file.relative_to(self.root).as_posix()
            if any(part.startswith(".") or part in IGNORED_DIRS for part in file.relative_to(self.root).parts):
                continue
            if not self.check(file.resolve().is_relative_to(self.root), "html", path,
                              "HTML symlink escapes the site root"):
                continue
            try:
                content = file.read_text(encoding="utf-8")
                if path == VERIFICATION:
                    self.check(content.strip() == f"google-site-verification: {VERIFICATION}",
                               "verification", path, "Search Console token changed")
                else:
                    self.pages[path] = Page(path, content)
            except (OSError, UnicodeError) as error:
                self.check(False, "html", path, str(error))
            if path in EXCEPTIONS:
                self.used_exceptions[path] = EXCEPTIONS[path]
        self.check(bool(self.pages), "html", ".", "No HTML pages found")
        for path in EXCEPTIONS:
            self.check(path in self.used_exceptions, "exception", path,
                       "Expected exception page is missing; review its policy before removing it")
        for path in ("index.html", "ja/index.html"):
            self.check(path in self.pages, "html", path, "Homepage missing")

    def page_references(self, page):
        for anchor, count in page.ids.items():
            self.check(count == 1, "anchor", page.path, f"Duplicate id: {anchor}")
        for tag, attrs, line, _ in page.elements:
            if tag == "base":
                self.check(False, "reference", page.path,
                           "base elements are unsupported; use explicit site-relative URLs", line)
            for key in ("href", "src", "poster"):
                if key in attrs:
                    self.reference(attrs[key], page.path, line)
            if "srcset" in attrs:
                for value in srcset_urls(attrs["srcset"] or ""):
                    self.reference(value, page.path, line)
            if tag == "meta" and attrs.get("property", attrs.get("name", "")).lower() in {
                "og:image", "og:image:url", "og:image:secure_url", "twitter:image"
            }:
                self.reference(attrs.get("content", ""), page.path, line)

    def metadata(self, page):
        hidden = page.path in HIDDEN
        policy = page.path == POLICY
        canonical = page.links("canonical")
        if not hidden or canonical:
            self.check(len(canonical) == 1, "canonical", page.path, "Expected exactly one head canonical")
            for attrs, line in canonical:
                self.check(attrs.get("href") == page.url, "canonical", page.path,
                           f"canonical must be {page.url}", line)
        og = page.metas("og:url")
        if not (hidden or policy) or og:
            self.check(len(og) == 1, "og-url", page.path, "Expected exactly one head og:url")
            for value, line in og:
                self.check(value == page.url, "og-url", page.path, f"og:url must be {page.url}", line)
        language = [attrs.get("lang") for tag, attrs, _, _ in page.elements if tag == "html"]
        self.check(len(language) == 1 and language[0] in {"en", "ja"}, "language", page.path,
                   "Expected one html element with lang=en or lang=ja")
        if not hidden:
            self.check(not ({"noindex", "none"} & page.robots()), "robots", page.path,
                       "Public page must remain indexable")
        self.hreflang(page, language[0] if language else None)
        self.structured_data(page, required=not (hidden or policy))

    def hreflang(self, page, language):
        alternate = page.links("alternate")
        entries = [(a.get("hreflang", "").lower(), a.get("href"), line)
                   for a, line in alternate if "hreflang" in a]
        en_path = page.path.removeprefix("ja/")
        ja_path = "ja/" + en_path
        paired = en_path in self.pages and ja_path in self.pages
        optional = page.path in HIDDEN or page.path in {POLICY, "midnight-cockpit/index.html"}
        if not paired and optional and not entries:
            return
        self.check(paired, "hreflang", page.path, f"Missing language counterpart: {en_path} / {ja_path}")
        expected = {"en": ORIGIN + route(en_path), "ja": ORIGIN + route(ja_path)}
        counts = Counter(lang for lang, _, _ in entries)
        for lang in ("en", "ja"):
            self.check(counts[lang] == 1, "hreflang", page.path, f"Expected one {lang} hreflang (including self)")
        for lang, value, line in entries:
            self.check(lang in {"en", "ja", "x-default"} and counts[lang] == 1, "hreflang", page.path,
                       f"Unsupported or duplicate hreflang: {lang}", line)
            self.check(value == expected.get("en" if lang == "x-default" else lang), "hreflang", page.path,
                       f"Incorrect {lang} hreflang: {value}", line)
        self.check(language == ("ja" if page.path.startswith("ja/") else "en"),
                   "hreflang", page.path, "html lang does not match the localized path")
        if paired:
            other = self.pages[en_path if page.path.startswith("ja/") else ja_path]
            other_map = {a.get("hreflang", "").lower(): a.get("href")
                         for a, _ in other.links("alternate") if "hreflang" in a}
            self.check(dict((lang, value) for lang, value, _ in entries) == other_map,
                       "hreflang", page.path, f"hreflang set is not reciprocal with {other.path}")

    def structured_data(self, page, required):
        expected_type = "Organization" if page.path in {"index.html", "ja/index.html"} else "SoftwareApplication"
        expected_url = ORIGIN + "/" if expected_type == "Organization" else page.url
        found = False
        for line, raw in page.json_blocks:
            try:
                def unique_pairs(pairs):
                    obj = {}
                    for key, value in pairs:
                        if key in obj:
                            raise ValueError(f"Duplicate JSON key: {key}")
                        obj[key] = value
                    return obj

                def invalid_constant(value):
                    raise ValueError(f"Invalid JSON constant: {value}")

                data = json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=invalid_constant)
                documents = data if isinstance(data, list) else [data]
                if not documents or not all(isinstance(d, dict) for d in documents):
                    raise ValueError("JSON-LD must be a nonempty object or array of objects")
                for document in documents:
                    self.check(document.get("@context") in ("https://schema.org", "https://schema.org/"),
                               "json-ld", page.path, "Expected schema.org @context", line)
                    nodes = document.get("@graph", [document])
                    if not isinstance(nodes, list) or not nodes or not all(isinstance(n, dict) for n in nodes):
                        raise ValueError("@graph must be a nonempty array of objects")
                    for node in nodes:
                        kind = node.get("@type")
                        self.check(isinstance(kind, str) and bool(kind), "json-ld", page.path,
                                   "Each top-level entity needs a nonempty @type", line)
                        if kind == expected_type:
                            found = True
                            self.check(isinstance(node.get("name"), str) and bool(node["name"].strip()),
                                       "json-ld", page.path, f"{kind} needs a name", line)
                            self.check(node.get("url") == expected_url, "json-ld", page.path,
                                       f"{kind}.url must be {expected_url}", line)
                    self.json_references(document, page, line)
            except (ValueError, TypeError, RecursionError) as error:
                self.check(False, "json-ld", page.path, f"Invalid JSON-LD: {error}", line)
        if required:
            self.check(found, "json-ld", page.path, f"Missing {expected_type} JSON-LD")
        self.check(page.json_buffer is None, "json-ld", page.path, "Unclosed JSON-LD script")

    def json_references(self, node, page, line):
        if isinstance(node, list):
            for item in node:
                self.json_references(item, page, line)
        elif isinstance(node, dict):
            for key, value in node.items():
                if key in {"url", "installUrl", "downloadUrl", "image", "logo", "contentUrl"}:
                    for item in value if isinstance(value, list) else [value]:
                        if not isinstance(item, dict):
                            self.reference(item, page.path, line)
                self.json_references(value, page, line)

    def hidden_policy(self):
        for path, required in HIDDEN.items():
            if path not in self.pages:
                continue
            page = self.pages[path]
            tokens = page.robots()
            self.check(required <= tokens, "hidden", path,
                       f"Required head robots directives: {', '.join(sorted(required))}")
            self.check(not ({"index", "all"} & tokens) and
                       not ("nofollow" in required and "follow" in tokens),
                       "hidden", path, "Conflicting robots directives")
        try:
            robot_text = (self.root / "robots.txt").read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            self.check(False, "robots", "robots.txt", str(error))
            return
        parser = RobotFileParser()
        parser.parse(robot_text.splitlines())
        self.check(parser.site_maps() == [ORIGIN + "/sitemap.xml"], "robots", "robots.txt",
                   "Expected the site sitemap declaration")
        for path in self.pages:
            for agent in ("*", "Googlebot", "Bingbot"):
                for url in {ORIGIN + route(path), ORIGIN + "/" + path}:
                    self.check(parser.can_fetch(agent, url), "robots", "robots.txt",
                               f"{agent} must be able to crawl {url} (including noindex pages)")
        # A specific bot directive must not re-index an intentionally hidden page.
        for page in self.pages.values():
            for name in ("googlebot", "bingbot"):
                for value, line in page.metas(name):
                    tokens = set(re.split(r"[\s,]+", value.lower()))
                    forbidden = {"index", "all"} if page.path in HIDDEN else {"noindex", "none"}
                    self.check(not tokens & forbidden, "robots", page.path,
                               f"{name} conflicts with the page indexing policy", line)

    def sitemap(self):
        try:
            tree = ET.parse(self.root / "sitemap.xml")
        except (ET.ParseError, OSError) as error:
            self.check(False, "sitemap", "sitemap.xml", f"Invalid XML: {error}")
            return
        root = tree.getroot()
        self.check(root.tag == SITEMAP_NS + "urlset", "sitemap", "sitemap.xml", "Expected sitemap urlset namespace")
        seen = set()
        expected = {page.url for path, page in self.pages.items() if path not in HIDDEN}
        for element in root:
            self.check(element.tag == SITEMAP_NS + "url", "sitemap", "sitemap.xml", "Expected a url element")
            locations = element.findall(SITEMAP_NS + "loc")
            dates = element.findall(SITEMAP_NS + "lastmod")
            self.check(len(locations) == 1 and len(dates) == 1, "sitemap", "sitemap.xml",
                       "Each url needs exactly one loc and one lastmod")
            for location in locations:
                value = location.text or ""
                self.check(value not in seen, "sitemap", "sitemap.xml", f"Duplicate URL: {value}")
                seen.add(value)
                self.check(value in expected, "sitemap", "sitemap.xml",
                           f"URL is not a public canonical page (or is intentionally hidden): {value}")
            for modified in dates:
                value = modified.text or ""
                try:
                    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                        raise ValueError("use YYYY-MM-DD")
                    date.fromisoformat(value)
                    valid = True
                except ValueError:
                    valid = False
                self.check(valid, "sitemap-date", "sitemap.xml", f"Invalid lastmod calendar date: {value!r}")
        for missing in sorted(expected - seen):
            self.check(False, "sitemap", "sitemap.xml", f"Public page missing from sitemap: {missing}")

    def run(self):
        self.load()
        for page in self.pages.values():
            self.page_references(page)
            self.metadata(page)
        self.hidden_policy()
        self.sitemap()
        return self

    def report(self):
        return {
            "ok": not self.issues, "pages": len(self.pages), "checks": dict(sorted(self.checks.items())),
            "errors": [vars(issue) for issue in self.issues],
            "exceptions": self.used_exceptions, "external_urls_not_fetched": len(self.external),
        }

    def markdown(self):
        lines = ["## Static site validation", "",
                 f"**{'PASS' if not self.issues else 'FAIL'}** — {len(self.pages)} HTML pages, "
                 f"{sum(self.checks.values())} checks, {len(self.issues)} errors.", "",
                 "| Check | Count |", "| --- | ---: |"]
        lines += [f"| {code} | {count} |" for code, count in sorted(self.checks.items())]
        if self.issues:
            lines += ["", "### Errors", ""]
            lines += [f"- <code>{escape(i.path)}:{i.line} [{i.code}] {escape(i.message)}</code>" for i in self.issues]
        lines += ["", "### Intentional exceptions", ""]
        lines += [f"- `{path}`: {reason}" for path, reason in self.used_exceptions.items()]
        lines += ["", "`x-default` is optional; when present it must point to English and be reciprocal.",
                  "The Japanese homepage's Organization.url identifies the organization at the English root.",
                  f"External URLs not fetched: {len(self.external)}. No network or third-party packages used.",
                  "lastmod is checked for calendar-date validity, not substantive-update accuracy or SEO results."]
        return "\n".join(lines) + "\n"


def annotation_escape(value):
    return str(value).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A").replace(",", "%2C").replace(":", "%3A")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", type=Path, help="Write a machine-readable report")
    parser.add_argument("--summary", type=Path, help="Write a Markdown report")
    args = parser.parse_args()
    result = Validator(args.root).run()
    print(result.markdown())
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for issue in result.issues:
            print(f"::error file={annotation_escape(issue.path)},line={issue.line},title={issue.code}::"
                  f"{annotation_escape(issue.message)}")
    if args.json:
        args.json.write_text(json.dumps(result.report(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.summary:
        args.summary.write_text(result.markdown(), encoding="utf-8")
    return 1 if result.issues else 0


if __name__ == "__main__":
    sys.exit(main())

# After Hours — 夜の実験室

A small green-phosphor CRT interface with full-color pixel illustrations, serving as a launcher for the existing Nemumaru private Site and Toku Chime. Vanilla HTML/CSS/Canvas; no new dependencies, cookies, analytics, autoplay or access-policy changes.

The English and Japanese home-page footers reveal a moon after five successive clicks/taps on “Tokumaru Labs”. A gap over two seconds, switching tabs or losing window focus resets the partial sequence. Enter or Space works with the footer button. The moon opens `/after-hours/`.

The room is unlisted in the sitemap and requests `noindex,nofollow,noarchive`. **This is an Easter egg, not authentication.** Its public source and direct URL can be discovered. Nemumaru keeps its own owner-only access. Toku Chime remains the existing public tool. No passwords or access tokens belong in these files.

The Canvas scenes animate at most ~6 frames/second while visible. The motion toggle and OS reduced-motion preference freeze them. No audio plays in the room.

## Verify locally

With Playwright installed for development:

```sh
node tests/after-hours.cjs
```

The test starts a temporary local server and checks the entry on both home pages, keyboard operation, links, responsive layout, animation/reduced motion and the existing Toku Chime controls. `AFTER_HOURS_CHROMIUM` optionally selects an installed Chromium executable. `AFTER_HOURS_OUTPUT` selects a screenshot directory; the default `.dev-flow/qa` is local evidence, not deployment content.

The default target is Chromium; Safari/iPhone physical-device behavior has not been exercised. All production paths are root-relative for this existing GitHub Pages site. Deployment is gated on the owner's final approval; no new Site is registered.

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

## CHA.EXE — unlisted artifact 001

Below the two existing launch cards is a small link to `/after-hours/assets/CHA_EXE_Im_Still_Here.zip`. The archive bundles a 3,072-byte unsigned Windows x64 demonstration and its reproducible, hand-authored machine-code builder and checks. It displays only “I'M STILL HERE.” and exits; it does not execute in the browser, change existing apps, require administrator privileges, contact a server or install anything. **Windows Server 2022 GitHub Actions runtime smoke-test PASSED**: the actual program displayed the expected message and exited with code 0 without elevation. Consumer Windows 10/11 machines have not been tested. Keep Windows Defender and SmartScreen enabled; a local Defender scan is still recommended. Leave SmartScreen/Defender enabled and do not ask visitors to bypass warnings. The ZIP's SHA-256 is `d92f5ab08ab2a4c162279d1b054a215c8b8c9818c2c2398f1544d36c9c2e8dc4`; the EXE's is `0391cac84bd25c18505db7a4586e931f3ba8fd4967f8b28b6d17128d80f0c3b2`. The archive integrity and source reproducibility are checked in CI.

### Local verification tooling

The repository now provides a preflight-only default in
`tests/cha_windows_smoke.ps1`. Explicitly adding `-RunExecutable`
requests the dialog/exit check after pinned hashes and Defender verification.
See [the Windows verification instructions](../tests/README.md#chaexe-windows-preflight-and-opt-in-runtime-test)
for report states, PowerShell compatibility, CI exceptions and limitations.
The downloadable ZIP and EXE have not changed. **Windows 10/11 physical-device
runtime tests and local Defender/SmartScreen behavior remain unverified.**
The script preserves existing download-zone metadata and does not bypass warnings.

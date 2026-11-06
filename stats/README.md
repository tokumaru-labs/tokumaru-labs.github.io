# Download Observatory

`/stats/` is an unlisted **public** dashboard, not an authenticated admin area.
It requests `noindex,nofollow,noarchive`, is excluded from sitemap/navigation, and
contains only public aggregate GitHub release-asset counts. Anyone with the URL
can view it; source and history are public too.

## What is measured

- TOKU CONTROL: stable published release assets matching the original Windows ZIP
  pattern. The `toku-control` ID, CSV product name, asset filter, and history stay
  unchanged. The dashboard labels this series as 通常ZIP.
- Two separate **reference** series cover the additional v0.3.0 distribution paths:
  `toku-control-portable` matches exactly `TokuControl-win-Portable.zip`, and
  `toku-control-update` matches `TokuControl-<version>-full.nupkg`.
  They have their own totals, intervals, chart selections, and CSV rows; they are
  excluded from the existing distribution total and product coverage denominator.
  No combined TOKU CONTROL total is computed. Portable ZIP has the same content
  as the ordinary ZIP. These counters are neither unique users nor successful
  updates; manual downloads, retries, multiple-file downloads and testing may count.
  Update metadata, checksums, source archives and delta packages are not counted.
  A future package naming change requires an explicit filter review.
- VS Code Themes: stable published release VSIX assets. Marketplace installs and
  pre-existing website downloads are not included.
- Counts come from GitHub's `download_count`, not visitors, clicks, installations,
  or proof that a file was fully saved. Re-downloads and testing can contribute.
- All pages and assets are paginated; drafts, prereleases, checksums, and source
  archives are excluded. Product filters live in `products.json`.
- `initial.json` is a real read-only observation from 2026-10-24, not sample data.
  It seeds the first automatic history and is a clearly labeled page fallback.

## Collection and storage

`.github/workflows/download-stats.yml` runs at 15:17 UTC (00:17 JST), manually,
when its collector/config changes land on main, and initially when installed.
It runs only in the original repository on `main`, using the standard public
Ubuntu runner, the built-in token, Python stdlib, and pinned checkout. No new
service, tracking SDK, personal access token, or metered API is required.

Before collection, the workflow idempotently mirrors the **existing** 0.2.1 VSIX
into the reserved `vscode-themes-v0.2.1` release. It verifies the source SHA-256,
uploads to a draft, verifies GitHub's asset digest/size/state, then publishes.
Existing assets are never deleted, clobbered, or replaced. Unexpected content or
metadata fails safely. Mirror failure still allows other counters to be recorded
and then marks the workflow failed. **Merging this workflow authorizes publication
of that byte-identical mirror.** It does not publish a new Marketplace version.

History is written to `downloads.json` on `download-stats-data`, never to main.
The existing collector already supports independent configured series, so adding
the two reference entries reuses its pagination, release filtering, validation,
failure handling and append-only history behavior without a collector rewrite.
Schema 1 and all existing snapshots (including `initial.json`) remain unchanged.
Reference keys first appear in a new observation after the updated config runs;
old snapshots are never backfilled. Missing keys display/export as `not_recorded`
(未記録), distinct from observed `no_assets` or `unavailable`. This derived status
is not written back to history. The first successful reference value is a baseline,
not that day's increase, even if the package was released before collection began.
The first data ref is published only after a complete initial data commit exists.
Later updates use the file's expected blob SHA to reject concurrent overwrites.
Missing/corrupt data on an existing branch is an error, not permission to reset it.
The workflow concurrency group also serializes scheduled/manual runs.

The dashboard reads that branch from raw.githubusercontent.com. This avoids
relying on another Pages deployment: pushes made with GITHUB_TOKEN do not trigger
GitHub Pages builds. A 12-second timeout, a labeled initial snapshot fallback, and
a 48-hour freshness warning cover unavailable or stale history. No token is sent
by the browser; cookies and referrers are omitted.

## VSIX download continuity

The four home/theme pages retain the original local VSIX hrefs. A small script
reads the public observation and prefers the release URL only when the latest
record is less than 48 hours old and the exact filename, repository, release URL,
and reviewed digest match. It does not record clicks or identify users.

If JavaScript, data access, mirror setup, or freshness checks fail, the original
local file remains available. **Those fallback downloads are not counted.**
The original local file and Marketplace link are kept. Do not sum Marketplace
installs with release downloads as though they were the same metric.

## Interpreting changes

- The first successful observation of a product is a baseline, never an increase.
- Changes compare asset IDs and counters against the previous successful sample.
- Missing observations stay null. Recovery spans the whole missed interval;
  the dashboard says so rather than allocating downloads to invented days.
- A new asset's count can be added if it was created after the previous sample.
  Discovering an older asset, losing/replacing an asset, or a counter decreasing
  makes that interval incomparable. The next observation uses the new baseline.
- The 7-/30-day filter uses elapsed days ending now. An interval crossing the
  period's starting boundary is shown but excluded from the period summary.
- CSV contains every observation, UTC/JST time, cumulative count, interval start,
  increase, status, and note. Missing values are blank. Public display uses JST.
  The original eight columns keep their names, order and existing series values.
  Three trailing columns identify `metric_id`, `metric_role` (`distribution` or
  `reference`), and `measurement_note`. Consumers requiring exactly eight columns
  must allow the added columns. Do not sum the reference rows with distribution
  rows or interpret their counts as people or successful updates.
- No extrapolation, backfilling, visitor attribution, or conversion-rate claim.

## Validation

```sh
python -B -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/download_stats.test.mjs
python -B scripts/validate_site.py
# With Playwright and a compatible Chromium installed:
node tests/download-stats.cjs
```

Optional browser-test environment variables: `STATS_CHROMIUM`, `STATS_QA_OUTPUT`.
Browser tests stub only GitHub data and never download real release assets.
History chart fixtures are test-only and never shipped as production data.
Fixture timestamps and the browser clock are fixed at 2026-10-25, so the
rolling-window assertions remain reproducible after the initial record ages.

A non-writing live observation is available with:

```sh
python -B scripts/download_stats.py --output /tmp/download-observation.json
```

Do not repeatedly download release binaries to test the counter: that pollutes it.

## Operation

After approved merge, check the **Record download statistics** Actions run,
release mirror, dedicated branch, `/stats/`, and public VSIX link fallback. The
first complete run starts daily collection. The page links to workflow status.
GitHub may delay scheduled runs; public-repo schedules can be disabled after 60
days without repository activity. If stale, inspect/re-enable the existing
workflow and run it manually; never manufacture missed daily values.

To stop collection, disable this workflow in GitHub Actions. Keep the history
branch to retain past observations. Removing the page/script changes does not
require deleting statistics or the release. Release/branch deletions require
separate owner approval.

Sources: [release assets](https://docs.github.com/en/rest/releases/assets),
[GITHUB_TOKEN behavior](https://docs.github.com/en/actions/concepts/security/github_token),
[schedules](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows),
[public runner billing](https://docs.github.com/en/actions/concepts/billing-and-usage).

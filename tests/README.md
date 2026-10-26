# Static site validation

製品ページのリンク・検索メタデータの回帰を、公開サイトへ接続せずに確認します。
Python 3.12以降の標準ライブラリだけを使い、npm/pip install、ブラウザー、APIキーは不要です。

```sh
python -B -m unittest discover -s tests -p 'test_validate_site.py' -v
python -B scripts/validate_site.py
```

任意のチェックアウトや機械可読レポートを指定する場合:

```sh
python -B scripts/validate_site.py --root /path/to/site --json /tmp/site-report.json --summary /tmp/site-report.md
```

エラーが1件でもあれば終了コード1。成功時は0です。レポートの件数は検証した述語の数であり、
回帰テストのケース数とは別です。ファイル名・行番号・検証カテゴリ・対象URLを出力します。
サイトマップやページ全体の不足のように行を特定できないエラーは1行目に表示します。

## CI

`.github/workflows/validate-site.yml` が全PR、mainへのpush、手動実行で動きます。
画像削除や新しい製品ディレクトリも拾うため、パスフィルターを置いていません。
Ubuntu 24.04 / Python 3.12を指定し、GitHub公式のcheckoutとsetup-pythonはコミットSHA固定です。
ネットワーク依存はチェックアウトとPythonの準備のみで、検証自体には通信がありません。
トークンは `contents: read`、資格情報の永続化なし、ジョブ上限5分です。

PRのChecksから、個別エラーの注釈・検証ログ・ActionsのJob summaryを確認できます。
summaryにはカテゴリ別の件数、適用した例外、外部URLの未検証数を表示します。
回帰テストが失敗してもサイト検証を実行し、両方の結果を残します。
既存のVS Codeテーマ用CIには変更を加えていません。

## 検証範囲

| 対象 | 確認内容 |
| --- | --- |
| HTMLの収集 | リポジトリ内の全 `*.html` を自動収集。隠しディレクトリ、node_modules、__pycache__は対象外 |
| 内部リンク・画像・資源 | `href` / `src` / `srcset` / `poster`、OG画像、Twitter画像、JSON-LDのURL・画像・ダウンロード先。相対、ルート相対、同一ホストの絶対URLをファイルへ解決 |
| アンカー | 同一ページ・別HTMLの `id` と旧式の `a[name]`、重複ID。URLエンコード、クエリ、空フラグメント、`#top`、テキストフラグメントを考慮 |
| canonical / OG URL | head内で各1件、HTTPSの自己URLと一致。index.html別名や他言語URLをcanonicalにしない |
| hreflang | `/ja/` と英語パスの対応、en/ja両方の自己参照・相互参照・実在、HTML言語、重複。新しい日英ページも自動対象 |
| JSON-LD | 厳密なJSON構文、重複キー・NaN等を拒否。schema.orgコンテキスト、型・名称・URL。製品はSoftwareApplication、トップはOrganization。オブジェクト・配列・@graph対応 |
| サイトマップ | XML名前空間、loc/lastmod各1件、URL一意性、公開canonicalページとの過不足。lastmodはYYYY-MM-DD形式かつ実在する暦日（うるう年含む） |
| 非公開設定 | After Hoursのnoindex/nofollow/noarchive、Toku Chimeのnoindex、各ページのサイトマップ除外。robots.txtのクロール許可、公開ページのnoindex混入も確認。現在の全ページクロール許可方針を保つため、非空Disallowを明示エラーにする |

外部URLは取得しません。`mailto:` / `tel:` / `data:` / `blob:` はローカルファイルとして扱いません。
HTML以外のSVG/PDF等のフラグメントは、そのファイルの存在のみ確認します。
`base` 要素は現在のサイトでは使っていないため、追加されたら明示エラーにします。

## 意図的な例外

例外は `scripts/validate_site.py` 内の**完全一致パス**に理由を記載しています。
該当ファイルがなくなった場合もエラーにし、不要になった例外の見直しを促します。
例外でも内部リンクは検証し、canonical / OG / JSON-LD等が存在すればその内容を検証します。

| ページ・規則 | 扱いと理由 |
| --- | --- |
| `/stats/` | 公開集計データの裏ページ。noindex/nofollow/noarchiveとサイトマップ非掲載を必須化。認証ページではない |
| `/after-hours/` | 隠し部屋。canonical / OG / JSON-LD / hreflangの必須化を免除。noindex/nofollow/noarchiveとサイトマップ非掲載は必須 |
| `/toku-chime/` | 非公開アプリ。検索メタデータの必須化を免除。noindexとサイトマップ非掲載は必須 |
| `/404.html` | エラーページ。同様に検索メタデータの必須化を免除し、noindexとサイトマップ非掲載を必須化 |
| `/progress-sidecar/privacy/` | 日英が1つの文書内に併記される。自己canonicalとサイトマップ掲載は必須。別言語ページ・OG・JSON-LDを要求しない |
| `/midnight-cockpit/` | 現時点で英語のみ。日本語版ができた場合は自動的に日英hreflang検証の対象になる |
| `/google9e6b85ab3daa42f4.html` | Search Console認証用テキスト。トークンの内容一致を検証し、HTMLメタデータとサイトマップ対象から除外 |
| `x-default` | 任意。既存のVS Codeテーマページにはない。存在する場合は英語URLと日英での相互整合を検証 |
| 日本語トップのOrganization.url | ページではなく組織を表すため、英語トップURLを使用。日本語ページのcanonical / OG URLは自己URLのまま |

新規ページは原則として公開ページ扱いです。別の意図的な非公開ページや単一言語ページを追加する際は、
広い除外ルールを作らず、この表・実装・回帰テストに個別の理由を追加してください。

## 限界と既存テスト

- lastmodの**形式と暦日**を検証します。本文の実質更新日、Gitコミット日との一致、未来日、検索順位は判定しません。
  軽微な整形と内容更新を機械的に同一視しないため、内容を変更したPRではlastmodもレビューしてください。
- HTML構文全体・Schema.org全語彙・リッチリザルト適格性の検証器ではありません。
  JSON-LDはこのサイトの単一文字列の@typeとschema.orgコンテキストを対象にします。
- CSS内のurl()、JavaScriptで生成したURL・アンカー、外部サービスのHTTP状態、画像のデコードや描画は対象外です。
  robots.txtの基本判定はPythonのRobotFileParserを使いますが、検索エンジンの最長一致・ワイルドカードを再現しません。
  そのため、Allowより後の禁止ルールやワイルドカードの見逃しを避ける独立した方針チェックで、
  全User-agentの非空Disallowを拒否します。空のDisallowとコメントは許可します。
  将来クロール禁止が必要になった場合は、その目的とnoindexへの影響をレビューして検証方針も更新してください。
- `tests/after-hours.cjs` は既存のPlaywright実動テストです。入口やタイマーの操作、表示の検証には引き続きこちらを使います。
  新CIは軽量な静的検証に限定し、Playwright依存を増やしていません。

`test_validate_site.py` は一時ディレクトリ内の小さなサイトを意図的に壊して検出を確認します。
実サイトを変更せず、正常例、例外、リンク切れ、片方向hreflang、不正JSON、無効日付、
非公開設定の欠落、終了コード・JSON/Markdown出力・GitHub注釈などを検証します。


## CHA.EXE: Windows preflight and opt-in runtime test

Run from a trusted checkout in an ordinary (non-administrator) Windows terminal.
Windows PowerShell 5.1 and PowerShell 7 syntax are supported. Use native x64
Windows and 64-bit PowerShell for execution. **Consumer Windows 10/11 physical
devices remain unverified**; a Windows Server 2022 CI pass is not a consumer-PC pass.

From the repository root, the default performs integrity checks and attempts a
Defender custom scan, but **does not launch CHA.EXE**:

```powershell
./tests/cha_windows_smoke.ps1
```

Only after choosing to run the executable, use:

```powershell
./tests/cha_windows_smoke.ps1 -RunExecutable
```

Optional output parent and time limits:

```powershell
./tests/cha_windows_smoke.ps1 -OutputDirectory "$env:TEMP/cha-checks" -ScanTimeoutSeconds 120 -DialogTimeoutSeconds 20
```

Each invocation creates a new `cha-smoke-<GUID>` directory. The default parent is
the OS temporary directory; a valid RUNNER_TEMP is used only on GitHub-hosted
Windows CI. The console prints the path to `result.json`. Keep it as evidence.
The directory also retains the package snapshot and extracted files; the script
does not recursively delete or reuse directories. Output-path setup errors can
occur before a report can be written.

The test checks the pinned ZIP hash before extraction, the EXE hash after
extraction, and the EXE hash again after scanning immediately before opt-in launch.
A read-only handle prevents replacement through normal filesystem writes during
the runtime check. Hash matches establish identity with the reviewed artifact,
not universal safety. If the ZIP has a Zone.Identifier (Mark of the Web), that
metadata is copied to the snapshot and every extracted file. No Unblock-File,
execution-policy change, security exclusion, warning acceptance, antivirus
disablement, or elevation is performed. A policy/security warning is a stop
condition: leave it in place and retain the report; do not use Run anyway.

Defender command availability, antivirus service state, engine/signature versions,
signature update time, scan-job completion, and detections matching this unique
binary path are recorded separately. A scan timeout (default 120 seconds), access
error, failed scan, or unreadable detection history fails verification. Detected
threats, including remediated detections for this path, block execution. Other
files' threat history is not logged. Normal Defender remediation remains enabled;
the test never restores quarantined files. The script does not update signatures
or alter cloud-protection settings; existing Defender policy may contact Microsoft.

| Report status | Meaning |
| --- | --- |
| PreflightPassed | Hashes verified and custom scan completed with no matching detection; EXE not launched |
| PreflightIncomplete | Hashes verified, Defender unavailable/inactive; EXE not launched; not a scan pass |
| Passed | Explicit execution verified the owned visible dialog, exact message and exit code 0 |
| PassedWithDefenderUnavailable | GitHub-hosted CI runtime check passed with a separately recorded unavailable scan |
| Failed | Integrity, scan or runtime check failed; see error and execution fields |

Unavailable Defender blocks local execution, even when another antivirus is
installed. There is no local override. CI explicitly supplies both
`-RunExecutable -AllowUnavailableDefenderOnCI`; the latter is accepted only with
GitHub-hosted Windows runner metadata and only for the Unavailable state. It does
not exempt detections, errors, timeouts, or unknown results. Environment metadata
is an operational guard, not an authentication boundary: do not spoof it locally.

The runtime check enumerates windows by the launched PID, validates the visible
CHA.EXE dialog and exact `I'M STILL HERE.` static control, sends WM_CLOSE only to
that owned dialog, and requires exit code 0 within ten seconds. On failure it
cleans up only its own process instance. Elevation state is recorded, not inferred
from the absence of an elevation request. The JSON can include local paths;
review it before sharing.

Regression tests require no Pester installation and use mocks; they do not launch
CHA.EXE or invoke a real Defender scan:

```powershell
./tests/test_cha_windows_smoke.ps1
```

CI runs those cases under both Windows PowerShell 5.1 and PowerShell 7, then runs
the existing pinned artifact's real dialog test on Windows Server 2022. The
JSON is printed in the job summary and uploaded as an artifact for 14 days,
including on failure. Consumer Windows 10/11, local Defender policy behavior,
and real SmartScreen warning presentation require separate physical-device checks.

Microsoft references:
- [Start-MpScan](https://learn.microsoft.com/en-us/powershell/module/defender/start-mpscan)
- [Get-MpThreatDetection](https://learn.microsoft.com/en-us/powershell/module/defender/get-mpthreatdetection)
- [Review scan results](https://learn.microsoft.com/en-us/defender-endpoint/review-scan-results-microsoft-defender-antivirus)

# Static site validation

製品ページのリンク・検索メタデータの回帰を、公開サイトへ接続せずに確認します。
Python 3.12以降の標準ライブラリだけを使い、npm/pip install、ブラウザー、APIキーは不要です。

```sh
python -B -m unittest discover -s tests -p 'test_validate_site.py' -v
python -B -m unittest discover -s tests -p 'test_sitemap_content.py' -v
python -B scripts/validate_site.py
python -B scripts/sitemap_content.py
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

## lastmodの更新漏れ防止

`scripts/sitemap_content.py` はサイトマップ掲載ページの内容と、レビュー済みの
`scripts/sitemap-content.json`（内容ハッシュ・lastmod・判断理由）を比較します。
既存CIで毎回実行し、追加のGit fetch、完全履歴、API、外部ライブラリは不要です。
記録の欠落、ページの追加・削除、内容またはlastmodの変更があれば失敗します。

対象は本文・title・検索メタデータ・JSON-LD・リンク・画像URL/altなどです。
HTMLコメント、空白の整形、class/style、CSS、実行用JavaScriptは比較から除外します。
JSON-LDはキー順や整形を正規化します。Gitの最終コミット日、ファイルmtime、CI実行日を
自動的にlastmodへ転記しません。日付は**実質的な内容更新日**をレビューして決めます。

製品を更新するときは、対応する日英製品ページと、カードを更新したトップページを確認します。
本文・ダウンロードURL・構造化データなどの実質更新なら、まず `sitemap.xml` の対象日付を変更し、
その日付と理由を明示して対象ページだけを記録します（次は2026-10-27の更新を記録する例）。

```sh
python -B scripts/sitemap_content.py --record index.html ja/index.html toku-control/index.html ja/toku-control/index.html --lastmod 2026-10-27 --reason "TOKU CONTROL v0.3.0: version, downloads and updater guides updated"
python -B scripts/sitemap_content.py
```

記録コマンドはサイトマップの日付を自動変更せず、指定日との不一致を拒否します。
同日中の再更新は同じ日付で記録できます。誤字修正・著作権年だけの変更などなら、日付を保持して
`--reason` にその理由を書きます。ハッシュを通すためだけに日付を進めないでください。
追加ページは通常の公開・hreflang検証も必要です。削除時は対応する記録も明示的に削除します。

これは**更新日のレビュー漏れを検出する仕組み**であり、選んだ日付の歴史的な正しさや
変更の重要性を自動証明するものではありません。PRで内容差分・日付・理由を確認してください。
同じURLの画像ファイル差し替え、CSS/JSによる表示内容の変更は自動検出の対象外なので、
実質更新なら影響するページのlastmodと記録を手動で更新します。
小さな静的サイトのため、毎回全Git履歴を取得する方式や、全ファイル変更を日付更新とみなす方式は採用していません。

初期記録はmain `ff19d0e6561d5628cbeacb027c2b8f4440124547` の全14掲載ページをGit履歴と照合しました。
4ページ（英日トップ・TOKU CONTROL）のlastmodを2026-10-25から2026-10-27へ修正し、
残る10ページは一致していたため保持しています。各記録の理由に根拠コミットを記載しています。
基準はGoogleの[サイトマップのlastmod指針](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap#additional-notes-about-xml-sitemaps)に沿います。

## 限界と既存テスト

- 基本検証器はlastmodの**形式と暦日**を検証し、上記の内容チェックでレビュー漏れを検出します。
  Gitコミット日との機械的な一致、未来日、検索順位は判定しません。
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

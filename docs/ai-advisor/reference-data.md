# 参照データ（kabulab 公開 API とライセンス境界）

Automations が一次情報の前段として使う **既定の参照データ源** と、Notion に書いてよい／書いてはいけないデータの境界。正本は [`satoki252595/kabulab_tool_cloudflare`](https://github.com/satoki252595/kabulab_tool_cloudflare) の `docs/HANDOFF-2026-09.md`（§1 恒久の制約・§4-C ライセンス境界）と `src/shared/db/public-columns.ts`（`PERSONAL_ONLY_COLUMNS`）。ここはそれを自動化の運用語に落としたもの。

## 1. ライセンス境界（出典タグ）

| 出典タグ | 出典 | 共有 Notion（`知識` / `日次レポート` / `振り返り` / コメント / 実行サマリー）に書けるか |
| --- | --- | --- |
| `commercial-ok` | **EDINET**（有価証券報告書・四半期報告書。`yuho-quant` の受注高／受注残高／海外売上高、EDINET 提出者業種 `sector33`） | **書ける**。出典 URL＋基準日を付ける |
| `factual-cite` | **TDnet**（適時開示。`ir-catalog` の開示タイトル・日付・タグ・PDF リンク） | **事実として引用できる**（表題・日付・分類・URL）。PDF 本文の長い転記はしない。要約は自分の言葉で 1〜2 行 |
| `primary` | 会社 IR ページ・決算短信（会社サイト）・JPX の**公開開示文書そのもの**（上場・市場再編の公表文など） | 書ける。出典 URL＋基準日を付ける |
| `personal-only` | **Yahoo Finance 由来**（株価・出来高・OHLCV・5分足・PER/PBR/配当利回り/時価総額・RSI/SMA/ATR/MACD 等のテクニカル・それらから作ったスコア）、**JPX 由来**（`data_j.xlsx` の市場区分 `market`・JPX 33/17 業種 `sector`/`sector17`・`instrument_type`）、**日証金/JPX 由来**（信用残高 `margin`） | **書かない**。値も、値を復元できる記述（「RSI は 27.3」「PER 8.9 倍」など）も書かない。読むこと自体は可（§3） |
| `no-store` | **みんかぶ**由来の優待掲載文（`yutai_benefits.description`。要約 `short_summary` もその派生） | **どこにも書かない**。Notion・レポート・コメント・実行サマリー・ログ・リポジトリ・Issue/PR のすべてで禁止。必要なら kabulab のページ URL だけ貼る |

補足:

- 「公開 API が返している値だから書いてよい」ではない。kabulab の公開面は運用者本人のためのもので、`personal-only` の値を含むページには public キャッシュも付けていない（HANDOFF D-14-3）。共有 Notion への転記は再配布に当たる。
- 業種は **EDINET 由来の 33 業種（`sector33`）だけ** を書く。JPX の `sector` を業種として書かない。市場区分は書かない。
- 実在の銘柄コードと区分（`instrument_type` 等）の対応表を作らない。ドキュメントの例には合成コード（1000〜1299）を使う。
- 日次ループが `知識` に書く行は、`種別=事実` でも **出典タグが `commercial-ok` / `factual-cite` / `primary` のものだけ**。`personal-only` / `no-store` は `知識` にも書かない。

## 2. 既定の参照データ源: kabulab 公開 JSON API（シークレット不要）

ベース URL: `https://kabulab-cf.satoki252595.workers.dev`。すべて GET、認証なし、JSON。まずここを読み、足りない事実だけ一次情報（EDINET / TDnet / 会社 IR）へ戻る。

### 2.1 書いてよいデータ（既定で使う）

| # | エンドポイント | 返るもの | 出典タグ | 主な用途 |
| --- | --- | --- | --- | --- |
| A1 | `GET /yuho-quant/api/screening?…` | 受注高・受注残高の成長スクリーニング。`{opts, count, rows[]}`、行に `code, name, sector(=sector33), years, latestOrdersYen, latestBacklogYen, ordersCagr, backlogCagr, ordersYoy, hasYearGap …` | `commercial-ok` | スクリーニング（受注成長の条件）、企業分析の事実 |
| A2 | `GET /yuho-quant/api/screening-overseas?…` | 海外売上高比率のスクリーニング。行に `latestRatioPct, ratioChangePp, latestOverseasYen, latestTotalYen, overseasCagr …` | `commercial-ok` | スクリーニング（地域エクスポージャ）、企業分析 |
| A3 | `GET /yuho-quant/api/trend/{code}` | 1 銘柄の受注高／受注残高の最大 5 年推移（会計期末×セグメント）。存在しなければ `404 {error}` | `commercial-ok` | 企業分析「事実」節、`知識` 行 |
| A4 | `GET /ir-catalog/api/stock/{code}?months=12&tag=` | 1 銘柄の適時開示タイムライン（表題・開示日・タグ・センチメント・PDF リンク） | `factual-cite` | 企業分析「事実」節（開示の有無・日付）、「次に確認する日」 |
| A5 | `GET /ir-catalog/file/{tdnetId}` | 開示 PDF のプロキシ（TDnet 原本 ≤31 日、その後は kabulab の Notion アーカイブ） | `factual-cite` | 一次情報の確認（本文を長く転記しない） |

クエリの仕様（`limit`、成長率の閾値、業種フィルタなど）は各 API の `opts` に返ってくる値と、リポジトリの `services/yuho-quant/src/routes/pages.ts` / `services/ir-catalog/src/routes/pages.ts` を正とする。

### 2.2 読めるが Notion に書かないデータ（`personal-only`）

| # | エンドポイント | 返るもの | 扱い |
| --- | --- | --- | --- |
| B1 | `GET /otakara-yutai/api/screening?month=&genre=&perMax=&pbrMax=&yieldMin=&rsiMax=&sort=&order=&limit=&offset=&withTotal=1` | 優待銘柄の一覧 `{items[], total, offset, limit}`。`code, name` と `sector`（EDINET）は書けるが、`price, per, pbr, dividendYield, yutaiYield, rsi14, fundamentalScore, technicalScore, totalScore` は `personal-only`。`market` は常に `null` | 条件の判定に読んでよい。値は書かない。掲載文（`description`）はこの API には含まれない |
| B2 | `GET /vwap-analysis/api/daily?code={code}` | 日足 10 年 `{bars[{date,o,h,l,c,v,adj}], splits}` | Yahoo 由来。値を書かない |
| B3 | `GET /vwap-analysis/api/intra?code={code}` | 5 分足（直近約 1 年） | Yahoo 由来。値を書かない |
| B4 | `GET /vwap-analysis/api/margin?code={code}&n=16` | 週次信用残高 | JPX/日証金 由来。値を書かない |
| B5 | `GET /vwap-analysis/api/chart?symbol={code}.T&range=60d&interval=5m` | Yahoo 当日 5 分足の中継 | Yahoo 由来。使わない（ライブ中継。自動化に不要） |

`/rsi-screening/api/*` は撤去済み（404）。RSI は B1 の `rsi14` にしか出ない。

### 2.3 kabulab のページ（人間が値を見る場所）

`personal-only` の値が必要な判断は、レポートに **ページ URL** を貼って本人に見てもらう:

`/rsi-screening/stocks/{code}` ・ `/swing-trading/stock/{code}` ・ `/otakara-yutai/stocks/{code}` ・ `/vwap-analysis/` ・ `/financial-math/`

## 3. 自動化での使い方（ルール）

1. **読む順**: 2.1（A1〜A5）→ 一次情報（EDINET / TDnet / 会社 IR）→ 必要なときだけ 2.2（B1〜B4）。ただし **順に全部読むのではなく、`分析観点` が宣言したスライスだけ** を、観点ごとに取る（§4）。
2. **`知識` に書くのは 2.1 と一次情報だけ**。`出典` は kabulab の API URL ではなく、元の EDINET / TDnet / IR の URL を優先し、取れなければ kabulab の該当ページ URL。
3. **`personal-only` の値を条件判定に使ったとき**（例: ルール「RSI が 30 未満」）は、レポートに「ルール条件〈RSI 30 未満〉を満たす（数値は kabulab で本人確認: 〈URL〉）」と書き、数値・帯・比率は書かない。投資判断のエントリー帯・破綻条件も **式**（「25 日線 −3%」「直近安値割れ」）で書き、価格の数値は書かない。
4. **`no-store`**（優待掲載文）は API からも取得しない設計になっているが、Web ページや PDF で見えても転記しない。
5. **条件判定の結果を書くことまで許すか** は運用者の判断で狭めてよい（`TODO`: 確認後この行を確定に）。狭める場合は「該当ルール条件の判定は kabulab で本人が行う」と書き、AIは EDINET/TDnet 由来の条件だけで一覧を作る。
6. **全表読みの禁止（ハードルール）**: `limit` なしの API 呼び出し、全銘柄ループ、全ページ送り、`SELECT *`、`LIMIT` なしの SQL、R2/D1 のダンプはしない。件数はスライスの `件数上限`、列は `フィールド`、期間は `期間` で必ず絞る。上限で足りないときは `確認不能（観点の上限）` と書いて先へ進む。

## 4. 分析観点（axis）とスライス

**前提**: データ全体をコンテキストに載せない。1 回の実行は `分析観点` を 1 つずつ処理する — その観点の **スライス**（エンドポイント / フィールド / 銘柄 / 期間 / 件数上限）だけを取り → **要約を Notion に書き** → 生データを捨てて次の観点へ。

### 4.1 観点定義の置き場所

- **確定後**: Notion の `分析観点` 定義（別担当が `schema-spec.md` / `automation-spec.md` に追加中。`docs/ai-advisor/notion-schema.md` §4.10 の `AXES` を参照）。**存在すればそれに従う**。
- **未定義のとき**: 下の §4.3 の既定カタログを使う。ルール本文の見出し（選定基準 / 必ず見る項目 …）が観点に対応する。

### 4.2 スライスの宣言項目（観点 1 つにつき）

| 項目 | 意味 | 例 |
| --- | --- | --- |
| `観点名` | 何を見るか（1 観点 = 1 問い） | 受注成長 |
| `対象目的` | スクリーニング / 企業分析 / 投資判断（売買計画） | 企業分析 |
| `データ源` / `エンドポイント` | §2 の 1 本、または EDINET / TDnet / 会社 IR / Notion のビュー | A3 `/yuho-quant/api/trend/{code}` |
| `フィールド` | 読む列（これ以外は捨てる） | `fiscalYearEnd, ordersYen, backlogYen, segment` |
| `銘柄範囲` | タスクの対象銘柄 / 前回一覧 / 上位 N / 指定リスト | タスクの対象銘柄 |
| `期間` | 直近 N 期・N か月・当日 | 直近 5 期 |
| `件数上限` | 行数（API の `limit` や SQL の `LIMIT` に必ず入れる） | 50 |
| `出典タグ` | §1 のタグ。`personal-only` なら値を書かない | commercial-ok |
| `要約テンプレ` | Notion に書く形（文字数上限つき） | 事実 2 行 / 変化 1 行 / 確認不能 |

### 4.3 既定カタログ（`分析観点` 定義が無いときの暫定。TODO: 確定後は Notion 側を正本に）

| 順 | 目的 | 観点 | スライス（エンドポイント / フィールド / 銘柄 / 期間 / 上限） | 出典タグ | Notion に書く要約 |
| --- | --- | --- | --- | --- | --- |
| S1 | スクリーニング | 受注成長 | A1 / `code,name,sector,ordersCagr,backlogCagr,ordersYoy,hasYearGap` / 母集団 / 直近 5 期 / `limit=` ウォッチ上限×2（最大 50） | commercial-ok | 残した条件・銘柄 ≤ ウォッチ上限・落とした理由（各 1 行） |
| S2 | スクリーニング | 海外売上高比率 | A2 / `code,name,sector,latestRatioPct,ratioChangePp,overseasCagr` / 母集団 / 直近 5 期 / 同上 | commercial-ok | 同上 |
| S3 | スクリーニング | ルール条件（personal-only） | B1 / 条件に要る列だけ（例 `code,per,pbr,rsi14`）/ S1・S2 の候補のみ / 当日 / `limit=` 候補数 | personal-only | 「条件〈…〉を満たす」の判定だけ。**数値は書かない**。kabulab URL |
| S4 | スクリーニング | 直近開示 | A4 / `title,date,tag` / 候補のみ / 直近 3 か月 / 1 銘柄 10 件 | factual-cite | 高シグナル開示の有無（表題・日付） |
| C1 | 企業分析 | 受注・受注残の推移 | A3 / `fiscalYearEnd,segment,ordersYen,backlogYen` / 対象銘柄 / 直近 5 期 / 50 行 | commercial-ok | 事実 2〜3 行＋計算（CAGR）1 行 |
| C2 | 企業分析 | 海外売上高比率 | A2（`code=` 絞り）/ `latestRatioPct,ratioChangePp,latestOverseasYen` / 対象銘柄 / 直近 5 期 / 10 行 | commercial-ok | 事実 1〜2 行 |
| C3 | 企業分析 | 適時開示タイムライン | A4 / `title,date,tag,sentiment` / 対象銘柄 / 直近 12 か月 / 30 件 | factual-cite | 上方修正・増配・自社株買い等の有無（表題・日付）。次に確認する日 |
| C4 | 企業分析 | 一次情報の確認 | EDINET 有報 / 決算短信（会社 IR）— 必要な節だけ / 対象銘柄 / 直近 1〜2 期 / 文書 2 本 | commercial-ok / primary | 数字ごとに出典＋基準日。取れなければ確認不能 |
| C5 | 企業分析 | 買わない理由 | 新規取得なし。C1〜C4 の要約だけから | — | 反証 3 つ |
| I1 | 投資判断 | 企業分析レポートの要約 | Notion `REPORTS`（対象銘柄・目的=企業分析・完了・最新 1 件）/ 本文の推論・確認不能 / 1 件 | — | 3 行 |
| I2 | 投資判断 | ルールの IF-THEN | Notion `RULES`（適用ルール 1 件）/ 見出し 4・5 だけ / 1 件 | — | 条件文への写像 |
| I3 | 投資判断 | 直近開示 | A4 / `title,date,tag` / 対象銘柄 / 直近 1 か月 / 10 件 | factual-cite | 破綻条件に触れる開示の有無 |
| I4 | 投資判断 | 価格条件（personal-only） | B2 / `date,c`（終値）/ 対象銘柄 / 直近 60 営業日 / 60 行 | personal-only | 条件式の成否（「25 日線 −3% 帯にある／ない」）だけ。**価格の数値は書かない**。kabulab URL |

観点の途中で上限に達したら、その観点の要約に `確認不能（観点の上限）` と書き、実行サマリーに「観点〈…〉の上限見直し提案」を残す。観点定義そのものは自動化が変えない。

## 5. 後日の選択肢: D1 REST / R2（シークレットが必要・任意）

公開 API で足りない集計が必要になったときだけ。Automations が動く環境（Cloud Agents → Secrets）に **任意** で追加する。いまは追加しない。

| 用途 | 追加するシークレット | 備考 |
| --- | --- | --- |
| D1 REST（読み取り） | `CLOUDFLARE_API_TOKEN`（D1 Read 権限のみ）・`CLOUDFLARE_ACCOUNT_ID`・`D1_DATABASE_ID` | `POST https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query`、`{"sql": "...", "params": []}`。**SELECT だけ**。`core_stocks` から `market / sector / sector17 / instrument_type / license_tag / src_source / quality` を選ばない（`PERSONAL_ONLY_COLUMNS`）。`yutai_benefits.description` を選ばない。表名は接頭辞ごとの一覧（`yuho_*` / `ir_disclosures` は書ける、`swing_*` / `rsi_*` / `p_momentum` / `otakara_*` は `personal-only`） |
| R2（`vwap-data`） | `R2_ACCOUNT_ID`・`R2_ACCESS_KEY_ID`・`R2_SECRET_ACCESS_KEY`（読み取り専用） | 中身は Yahoo/JPX 由来の時系列（`personal-only`）。Notion に書けるものが無いので **自動化には不要**。B2〜B4 の公開 API で足りる |

いずれもトークンをリポジトリ・ドキュメント・Notion・実行サマリーに書かない。Runtime Secret として登録し、値は `[REDACTED]` のまま扱う。

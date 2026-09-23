# 参照データ（参照資産・ライセンス階層・観点ごとの取得形）

正本は Project の `internal/schema-spec.md` §7（共通観点）・§8（参照資産）と `internal/automation-spec.md` §1（文脈予算）・§6（観点 → 取得の対応）。棚卸しは `internal/kabulab-cf-inventory.md`。ここはそれらを **自動化が叩く形** に転記したもので、矛盾したら正本が勝つ。

観点の定義（問い・参照資産・スライス・取得上限・重さ）は **Notion の `分析観点` DB が正本**（運営が schema-spec §7 の共通観点を登録する）。この文書に観点のカタログは持たない。

## 1. ライセンス階層 → Notion への書き方（schema-spec §8.3）

| `参照資産.ライセンス` | 由来 | Notion への書き方（本文・事実台帳・`AIの一言`・`追跡メモ` すべて） |
| --- | --- | --- |
| `commercial-ok` | EDINET（有報の受注・海外売上、EDINET 提出者業種 `sector`=33 業種）、`stocks.json` の `name` | 数値・要約を出典 URL＋取得日時付きで書いてよい |
| `factual-cite` | TDnet（適時開示の表題・日付・タグ・URL）、お宝優待の `benefitSummary`／`genres`／`benefitMonths`（自作要約） | 事実を短く（数値・日付・件名）、出典 URL 付きで。PDF 本文の転載・長文要約はしない |
| `personal-only` | Yahoo 由来（株価・出来高・OHLCV・5 分足・PER/PBR/配当利回り/時価総額・RSI 等・スコア）、JPX 由来（`market`・JPX 業種・`instrument_type`）、日証金/JPX 由来（信用残高） | **値を書かない**。ルール条件に対する `成立／未成立` と「参照資産『名称』で確認（値は転記しない）」だけ。読んで判定に使うことは可 |
| `no-store` | みんかぶ由来の優待掲載原文（`yutai_benefits.description`） | 参照資産に載せない。読まない。どこにも書かない |

補足: 業種を書くなら EDINET 由来の 33 業種だけ。`market` は書かない。実在銘柄コードと区分の対応表を作らない。`sector` が空の銘柄は `見ない領域` の **業種一致** を `確認不能` にする（除外しない）。ただし IR 表題/タグの `監理銘柄` `整理銘柄` `上場廃止`、および `見ない領域` テキストの表題/タグ部分一致は宇宙外として落とす／見送り（朝スキル §0.1）。

## 2. 参照資産の既定行（schema-spec §8.4。運営が `参照資産` DB に登録）

`…` ＝ `https://kabulab-cf.satoki252595.workers.dev`。自動化は **`状態=有効` かつ `必要Secret` 空** の行だけ読む。`保留` は Secret を配れる段階で `有効` にする（後日の選択肢。いまは追加しない）。

| # | 名称 | 種別 | パス・URL | 提供データ（項目名は 2026-09-15 の実応答） | 用途 | 更新 | ライセンス | 必要Secret | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | kabulab 有報定量検索 | 公開API | `…/yuho-quant/api/screening?metric=orders&minYears=3&limit=30` | `{opts,count,rows[]{code,name,sector,years,firstFiscalYearEnd,lastFiscalYearEnd,latestOrdersYen,latestBacklogYen,firstOrdersYen,firstBacklogYen,hasYearGap,ordersCagr,backlogCagr,ordersYoy,backlogYoy}}`（EDINET 由来） | スクリーニング・企業分析 | 毎営業日 20:00 JST | commercial-ok | — | 有効 |
| 2 | kabulab 有報定量検索（海外） | 公開API | `…/yuho-quant/api/screening-overseas?minYears=3&limit=30` | `{opts,count,rows[]{code,name,sector,years,…,latestRatioPct,firstRatioPct,ratioChangePp,latestOverseasYen,latestTotalYen,firstOverseasYen,hasYearGap,overseasCagr,overseasYoy,regionLabel,latestRegionYen,regionRatioPct}}` | スクリーニング・企業分析 | 毎営業日 20:00 JST | commercial-ok | — | 有効 |
| 3 | kabulab 有報定量検索（推移） | 公開API | `…/yuho-quant/api/trend/{code}` | `{stock{id,code,name,market,sector},documents[]{docId,periodEnd,submittedAt,docTypeCode,parseStatus},points[],hasStructuredData}`（`hasStructuredData=false` は受注表なし。無い銘柄は `404 {error}`） | 企業分析 | 毎営業日 20:00 JST | commercial-ok | — | 有効 |
| 4 | kabulab IR Catalog | 公開API | `…/ir-catalog/api/stock/{code}`（PDF `…/ir-catalog/file/{tdnetId}`） | `{code,name,market,since,months,disclosures[]{tdnetId,title,pubdate,documentUrl,tags[],primaryTag,pdfSentiment,pdfSentimentMethod,pdfSentimentScore}}`（TDnet 由来。無い銘柄は `404`） | 企業分析・投資判断 | 毎営業日 20:00 JST | factual-cite | — | 有効 |
| 5 | kabulab お宝優待 | 公開API | `…/otakara-yutai/api/screening?limit=30&sort=total&order=desc`（`month,genre,perMax,pbrMax,yieldMin,rsiMax,offset,withTotal=1` 可） | `{items[]{code,name,market,sector,price,per,pbr,dividendYield,yutaiYield,rsi14,fundamentalScore,technicalScore,totalScore,benefitMonths[],benefitSummary,genres[]},total,offset,limit}`。`price…totalScore` は personal-only、`market` は常に null | スクリーニング | スコア月次・財務日次 | factual-cite（数値は personal-only） | — | 有効 |
| 6 | kabulab 日足10年 | 公開API | `…/vwap-analysis/api/daily?code={code}` | `{code,updated,bars[]{date,o,h,l,c,v,adj},splits[]{date,ratio}}`（Yahoo 由来。未取得は `bars:[]`） | 投資判断 | 月水金 17:00 JST | personal-only | — | 有効 |
| 7 | kabulab 5分足 | 公開API | `…/vwap-analysis/api/intra?code={code}` | 5 分足 ≤1 年（Yahoo 由来） | 投資判断 | 月水金 | personal-only | — | 有効 |
| 8 | kabulab 当日ライブ | 公開API | `…/vwap-analysis/api/chart?symbol={code}.T&range=5d&interval=5m` | Yahoo 中継（15〜20 分遅延） | 投資判断 | ライブ | personal-only | — | 有効 |
| 9 | kabulab 信用残高 | 公開API | `…/vwap-analysis/api/margin?code={code}&n=8`（`n=1..260`） | `{code,weeks[]{week,code,sell,buy,sell_chg,buy_chg}}`（JPX 由来） | 投資判断 | 土曜 18:00 JST | personal-only | — | 有効 |
| 10 | kabulab 銘柄リスト（凍結） | GitHubファイル | `https://raw.githubusercontent.com/satoki252595/kabulab_tool_cloudflare/main/public/vwap-analysis/data/stocks.json` | `{count,stocks[][code,name,market]}`。2026-06-18 凍結。**`jq` で 1 件だけ引く** | 全目的（銘柄名の解決） | 凍結 | commercial-ok（`market` は書かない） | — | 有効 |
| 11 | EDINET | 一次情報 | `https://disclosure2.edinet-fsa.go.jp/` | 有価証券報告書（#3 の `docId` で特定） | 企業分析 | 提出時 | commercial-ok | — | 有効 |
| 12 | TDnet | 一次情報 | `https://www.release.tdnet.info/` | 適時開示（#4 の `documentUrl`／`tdnetId`） | 全目的 | 開示時 | factual-cite | — | 有効 |
| 13 | kabulab 銘柄マスタ core_stocks | D1 REST | `POST https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}/query`（SELECT `code,name,edinet_code,sector33,is_active,is_yutai,listing_date` のみ） | 母集団 ~3,700。`market/sector/sector17/instrument_type/license_tag/src_source/quality` は WHERE にだけ使う | 全目的 | 月次 | commercial-ok（列限定） | `CLOUDFLARE_API_TOKEN`（D1 Read）・`CLOUDFLARE_ACCOUNT_ID` | **保留** |
| 14 | kabulab 最新ファンダ断面 | D1 REST | 同上（`core_stock_financials` JOIN `rsi_percentile`） | Yahoo 由来 | スクリーニング・企業分析 | 毎営業日 06:00 JST | personal-only | 同上 | **保留** |
| 15 | kabulab スイング指標・シグナル・マクロ | D1 REST | 同上（`swing_*`） | Yahoo 由来の派生 | 投資判断・スクリーニング | 毎営業日 06:00 JST | personal-only | 同上 | **保留** |
| 16 | kabulab スキーマ辞書 | GitHubファイル | `…/src/shared/db/core-schema.ts` ほか | D1 の列名（#13〜15 用） | 全目的 | コミット時 | — | — | **保留** |
| 17 | kabulab 一次データ保管庫（Notion） | Notion | 「バックアップ」配下 `一次データ｜yuho-quant` 等 | 有報 ZIP・開示 PDF の実体 | 企業分析 | 取込時 | EDINET commercial-ok／TDnet factual-cite | Notion 連携 | **保留** |

載せないもの: ローカル限定資産、みんかぶ掲載原文（no-store）、`core_stocks` の JPX 由来区分値の転記、旧 Neon 系、本番で 404 の `/rsi-screening/api/*`。R2 直読（`R2_*`）は中身が personal-only で Notion に書けるものが無いため **自動化には不要**。

## 3. 取得の型（automation-spec §1）

```bash
# 切ってから読む。結果（数KB）だけを文脈に入れ、書いたら消す
curl -sS -m 30 "<URL>" | jq -c '<射影・件数制限>' > /tmp/axis-<観点>.json
# 初回は構造だけ確認し、その出力も捨てる
curl -sS -m 30 "<URL>" | jq 'keys'
# jq が無いとき
curl -sS -m 30 "<URL>" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps([{k:r.get(k) for k in ("code","name")} for r in d.get("rows",[])[:30]], ensure_ascii=False))'
rm -f /tmp/axis-*.json   # 観点を終えたら
```

取得失敗（HTTP 5xx、タイムアウト 30 秒、JSON 不正、期待フィールド欠落）→ 1 回だけ再試行 → それでも失敗なら寄与 `確認不能`、根拠に `到達不能 <HTTPコード>`。**不足にはしない。** 対象コードの **HTTP 404** または **`points[]` / `disclosures[]` / `bars[]` が空** は到達不能ではなく **`データ不足`**（朝スキル §0.1-7・`DATA_MISSING`）。`hasStructuredData` や ping だけでは分析にしない。

## 4. 観点 → 取得の対応（automation-spec §6。既定の共通観点）

`B=https://kabulab-cf.satoki252595.workers.dev`。フィールド名は 2026-09-15 の実応答。応答が変わったら **`参照資産.提供データ` と `分析観点.スライス` を直す**（スキルとプロンプトは変えない）。

| 観点 | 取得（シェル） | 切り方（jq） | ライセンス → 書き方 |
| --- | --- | --- | --- |
| 受注トレンド | `curl -sS -m 30 "$B/yuho-quant/api/screening?metric=orders&minYears=3&limit=30"` | `.rows[] \| {code,name,sector,years,latestOrdersYen,latestBacklogYen,ordersCagr,backlogCagr,ordersYoy,backlogYoy,hasYearGap}` | commercial-ok → 数値可 |
| 海外売上比率 | `curl -sS -m 30 "$B/yuho-quant/api/screening-overseas?minYears=3&limit=30"` | `.rows[] \| {code,name,sector,years,latestRatioPct,ratioChangePp,overseasCagr,overseasYoy}` | commercial-ok |
| 優待・還元（既定 OFF） | `curl -sS -m 30 "$B/otakara-yutai/api/screening?limit=30&sort=total&order=desc[&perMax=&pbrMax=&yieldMin=]"` | `.items[] \| {code,name,sector,benefitMonths,genres,benefitSummary: .benefitSummary[0:80]}`（`price/per/pbr/yield/rsi14/score` は絞り込み判定にだけ使い、出力に含めない） | factual-cite（優待内容）／personal-only（数値）→ 数値は書かない |
| 受注・海外の推移 | `curl -sS -m 30 "$B/yuho-quant/api/trend/{code}"` | `{stock:{code,name,sector}, n_points:(.points\|length), points, docs:[.documents[] \| {periodEnd,parseStatus}], hasStructuredData}`。**`points[]` の中身を読む**（`hasStructuredData` や件数だけは不可） | commercial-ok。`points` 空または 404 → `データ不足`（`DATA_MISSING:系列`）。`hasStructuredData=false` かつ `points` 空も同じ |
| 開示の流れ | `curl -sS -m 30 "$B/ir-catalog/api/stock/{code}"` | `{n:(.disclosures\|length), titles:[.disclosures[] \| {pubdate,title,primaryTag,tags}]}`。**表題全件**（先頭 3 件・`[0:30]` で終わらせない）。PDF は含めない | factual-cite → 日付・表題・タグ。404 / `n=0` → `データ不足`（`DATA_MISSING:IR`）。不利語・宇宙外語は表題/タグで判定 |
| 一次情報（重） | 開示の流れの `documentUrl`（決算短信）と EDINET の直近有報。PDF → テキスト化し `節=` の見出しで抜く | 各文書 ≤2、節ごと ≤3000 字 | EDINET commercial-ok／TDnet factual-cite |
| 株主還元・優待（既定 OFF） | お宝優待の一覧から `code` 一致を抽出（ページング ≤3 回で見つからなければ確認不能） | `{benefitMonths,genres,benefitSummary}` | factual-cite |
| 企業分析の継承 | Notion: 同じ利用者×銘柄の直近 `企業分析` タスク（レポート済）の `## 統合` 節と判断行 | ≤600 字 | — |
| 価格条件 | `curl -sS -m 30 "$B/vwap-analysis/api/daily?code={code}"` | `{updated, splits, n:(.bars\|length), bars: (.bars[-120:] \| map({date,c,v,adj}))}`。`bars` が空または 404 なら `データ不足`（`DATA_MISSING:系列`）。基準日は最終 `date`（月水金更新・最大 2 営業日遅れ） | personal-only → 成立／未成立のみ。値を書かない |
| 需給 | `curl -sS -m 30 "$B/vwap-analysis/api/margin?code={code}&n=8"` | `.weeks[] \| {week,buy,sell,buy_chg,sell_chg}`。基準日は最新 `week`（土曜更新）。空なら需給は `確認不能`（価格系列の `DATA_MISSING` とは別） | personal-only → 成立／未成立のみ |
| 直近開示 | `curl -sS -m 30 "$B/ir-catalog/api/stock/{code}"` | `{n:(.disclosures\|length), titles:[.disclosures[] \| select(.pubdate >= "<30日前>") \| {pubdate,title,primaryTag,tags}]}`。30 日窓は **全件**（`[0:10]` で終わらせない） | factual-cite。空/404 は `DATA_MISSING:IR` |
| サイズと破綻条件 | Notion: 専属の `1銘柄あたり金額`・`許容損失`・`低確信度のサイズ`、ルール IF-THEN | — | 金額で提案。価格の値を使う計算は式だけ示す |
| 反証 | 本文の観点の節の要約のみ | — | — |
| 制約と既判断 | Notion: 専属の `見ない領域`・`ウォッチ上限`、`判断`（利用者、90 日）。残す候補は IR Catalog の表題/タグ | 過去判断 ≤20 行。業種は `sector` 部分一致（空は `確認不能` で除外しない）。宇宙外語（監理/整理/上場廃止）と `見ない領域` テキストは IR 表題/タグでも照合して落とす | — |
| （銘柄名の解決） | #4 `name`／#3 `stock.name`、無ければ `curl -sS -m 30 <stocks.json raw> \| jq -c '.stocks[] \| select(.[0]=="{code}")'` | 1 件だけ。`market` は書かない | commercial-ok（name） |

## 5. 後日の選択肢: D1 REST（シークレットが必要・任意）

公開 API で足りない集計（母集団 `core_stocks` の全件条件など）が必要になったときだけ。`参照資産` #13〜#16 を `有効` にし、Cloud Agents → Secrets に **任意** で追加する:

- `CLOUDFLARE_API_TOKEN` … D1 **Read** に絞った専用トークンを新規発行（Runtime Secret）
- `CLOUDFLARE_ACCOUNT_ID`、`D1_DATABASE_ID`（`wrangler.toml` の値）

運用: `SELECT *` ではなく列名を明示（列の改名・削除で壊れる）。`core_stocks` の personal-only 列（`market sector sector17 instrument_type license_tag src_source quality`）と `yutai_benefits.description` を選ばない。実行は 06:30 JST 以降（stock-sync 完了後）。トークンをリポジトリ・ドキュメント・Notion・実行サマリーに書かない。

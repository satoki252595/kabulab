# 参照データ — 固定切片と取得形

正本は計画書 §7。観点 DB / 参照資産 DB は **無い**。人が増やすのはルール条件。新しいデータ源は運営が計画書とこの文書とスキルを改版する。

日本株のみ。Mac の `/Users/satoki252595/projects/kabulab-cf` はクラウドのインタフェースではない（参照もデプロイ元にもしない）。公開 JSON はデータ面として再利用してよい。

`B=https://kabulab-cf.satoki252595.workers.dev`

## 1. ライセンス → Notion への書き方

| 階層 | 由来 | Notion |
| --- | --- | --- |
| commercial-ok | EDINET（受注・海外、33 業種）、凍結 `stocks.json` の `name` | 数値可。出典 URL＋取得日時 |
| factual-cite | TDnet 表題・日付・タグ・URL、お宝優待の `benefitSummary` / `genres` / `benefitMonths` | 短く出典付き。PDF 転載しない |
| personal-only | Yahoo / JPX / 日証金（株価・出来高・OHLCV・RSI・PER・PBR・利回り・信用・スコア・`market`） | **値を書かない**。成立／未成立。円は CF 私有 |
| no-store | みんかぶ掲載原文 | 読まない |

業種は EDINET 33 業種だけ。`market` は書かない。

## 2. 経路の優先（1 切片ごとに 1 経路）

1. **jss-api MCP**（ダッシュボードで Notion と並べて接続済みなら）。必要な項目・件数・期間だけ。limit なし・全銘柄ループ禁止。公開＝licenced 切片、私有＝Yahoo/JPX を判定用に読む。
2. **他の接続済み MCP** で、その切片が既に返るときだけ（Notion MCP は 5 DB 用。価格の正本にしない）。
3. **kabulab-cf 公開 JSON**（認証不要）
   - commercial-ok: `/yuho-quant/api/screening` `screening-overseas` `trend/{code}`
   - factual-cite: `/ir-catalog/api/stock/{code}`、お宝優待の `benefitSummary` / `genres` / `benefitMonths`
   - personal-only（読んで Notion に値を書かない）: `/vwap-analysis/api/{daily,intra,chart,margin}`、お宝優待の price/PER/PBR/RSI/score
   - 銘柄名: 有報・IR の `name`。無ければ凍結 `stocks.json` を **1 コードだけ** `jq`
4. **公開 Web の地合い**（日経・TOPIX・ドル円・金利・原油などの要約ソース）。引用は URL + 取得日時。HTML 全文・全表読み禁止。数値は出典付きで、Yahoo 個別株の転記に使わない。

使わない: `CRON_SECRET` ingest、R2 ダンプ、D1 `SELECT *`、`kabumcp` / `paperstock` を正にすること、みんかぶ原文、旧 8DB、パイプライン用 `db_ids.json`、Cloudflare bindings のアカウント横断 `d1_database_query`。

## 3. 取得の型

```bash
curl -sS -m 30 "<URL>" | jq -c '<射影・件数制限>' > /tmp/slice-<切片>.json
# 書いてから捨てる
rm -f /tmp/slice-*.json
```

失敗（HTTP ≠ 200、タイムアウト 30 秒、JSON 不正、期待フィールド欠落）→ 1 回再試行 → それでも失敗なら寄与 `確認不能`、根拠に `到達不能 <HTTPコード>`。**仕事全体は不足にしない。**

## 4. 固定切片（スキルに埋め込む）

| 切片 | 目的 | 重さ | 取得（フォールバック） | 切り方 | Notion への書き方 |
| --- | --- | --- | --- | --- | --- |
| 地合い | スクリーニング先頭 | 軽 | 公開 Web 要約（日経平均・TOPIX・ドル円・金利・原油のうち到達できたもの。各ソース HTML を全文読まない） | 資金の向き 3 行。出典 URL | 出典＋取得日時 |
| 受注 | スクリーニング | 軽 | `curl -sS -m 30 "$B/yuho-quant/api/screening?metric=orders&minYears=3&limit=30"` | `.rows[] \| {code,name,sector,years,latestOrdersYen,latestBacklogYen,ordersCagr,backlogCagr,ordersYoy,backlogYoy,hasYearGap}` 項目 ≤12 | commercial-ok |
| 海外 | スクリーニング | 軽 | `curl -sS -m 30 "$B/yuho-quant/api/screening-overseas?minYears=3&limit=30"` | `.rows[] \| {code,name,sector,years,latestRatioPct,ratioChangePp,overseasCagr,overseasYoy}` | commercial-ok |
| 開示の流れ | 両方 | 軽 | `curl -sS -m 30 "$B/ir-catalog/api/stock/{code}"` | `[.disclosures[] \| select(.pubdate >= "<12ヶ月前>") \| {pubdate,title,primaryTag,tags,documentUrl}][0:30]` | 表題・日付・タグ・URL |
| 一次情報 | 売買判断 | **重** | EDINET / TDnet。開示の流れの `documentUrl` と有報。`節=` ≤3000 字 × 文書 2 | 要約。PDF 転載しない | commercial-ok / factual-cite |
| 優待 | スクリーニング | 軽・既定 OFF | `curl -sS -m 30 "$B/otakara-yutai/api/screening?limit=30&sort=total&order=desc"` | `.items[] \| {code,name,sector,benefitMonths,genres,benefitSummary: .benefitSummary[0:80]}`（price/per/pbr/rsi/score は判定だけ） | 要約のみ |
| 価格条件 | 売買判断 | 軽 | jss-api 私有または `curl -sS -m 30 "$B/vwap-analysis/api/daily?code={code}"` | `{updated, bars: (.bars[-120:] \| map({date,c}))}` | 成立／未成立のみ |
| 需給 | 売買判断 | 軽 | `curl -sS -m 30 "$B/vwap-analysis/api/margin?code={code}&n=8"` | `.weeks[] \| {week,buy,sell,buy_chg,sell_chg}` | 成立／未成立のみ |
| 直近開示 | 売買判断 | 軽 | IR catalog 30 日 10 件 | `[.disclosures[] \| select(.pubdate >= "<30日前>") \| {pubdate,title,primaryTag,documentUrl}][0:10]` | factual-cite |
| サイズと破綻 | 売買判断 | 軽 | エージェント制約 + ルール（再取得しない） | 式と金額言葉 | 円の代入結果は私有面 |
| 反証 | 両方 | 軽 | 本文の節だけ（再取得しない） | 入らない理由 3 | — |
| 制約と既判断 | 両方 | 軽 | Notion。過去判断 20 行 | 見ない領域・90 日除外 | — |

スクリーニング既定セット（軽）: 地合い、受注、海外、開示の流れ（ウォッチがあるときコードごと上限内）、制約と既判断、反証。優待はルールが明示したときだけ。

売買判断既定セット: 地合い、開示の流れ、直近開示、価格条件、需給、サイズと破綻、反証、制約と既判断、一次情報（重・1 ラン 1 つ）。

銘柄名の解決: IR / 有報の `name`、無ければ

```bash
curl -sS -m 30 "https://raw.githubusercontent.com/satoki252595/kabulab_tool_cloudflare/main/public/vwap-analysis/data/stocks.json" \
  | jq -c --arg c "$CODE" '.stocks[] | select(.[0]==$c)'
```

1 コードだけ。`market` は書かない。

## 5. 円帯 POST（私有面）

仕事がレポート済になる直前、円帯がある判断だけ 1 回:

```bash
# 値は環境変数。ログ・Notion・実行サマリーにシークレットを出さない
curl -sS -m 30 -X POST "$AI_EXPERT_YEN_API_URL/api/internal/yen" \
  -H "Authorization: Bearer $AI_EXPERT_YEN_STORE_SECRET" \
  -H "Content-Type: application/json" \
  -d @/tmp/yen-payload.json
rm -f /tmp/yen-payload.json
```

ペイロード: `notion_decision_id`, `user_id`（エージェントの `WebユーザーID`）, `code`, `side`, `as_of`, `entry_yen`, `stop_yen`, `take_yen`, `size_yen`, `source=automation`。結果％は夕の追跡で本人分だけ更新してよい（既存行の円は変えない。結果列のみ）。

`WebユーザーID` が空なら POST せず `実行メモ` に `YEN_STORE_SKIPPED:NO_WEB_USER`。失敗しても Notion は `成立／未成立` で完了し、`実行メモ` に `YEN_STORE_FAILED`（シークレットは書かない）。既存行があれば上書きしない（API は 409）。

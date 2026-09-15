# Notion スキーマ配線表（Automations が読む正本）

Automations のスキルは、DB名・プロパティ名・ID を **この文書だけ** から取る。スキーマが変わったらここを直せば、3つのスキルとダッシュボードのプロンプトを触らずに追従できる。

> **状態: 仮（TODO）**
> 現在の内容は [計画書（要件起点）](https://app.notion.com/p/3dad74ff84cd81f9b807dd7971230449) §5 由来の暫定スキーマ。Notion 側は別担当が再設計中で、確定スキーマ仕様と自動化仕様が出たら、この文書の `TODO` を埋めて `状態: 確定` に変える。
> ID が `TODO` の DB に対してスキルは **書き込みをしない**（読み取りだけ試み、実行サマリーに「未配線」と書いて終了する）。

## 0. 親ページと接続

| 項目 | 値 |
| --- | --- |
| Notion ワークスペース | はぴまね |
| 親ページ | [AI専属アナリスト](https://app.notion.com/p/3dad74ff84cd80c4956feaf9255de7e1) |
| Notion MCP（Cursor 側） | Cloud Agents の MCP 一覧にある `Notion`（HTTP / OAuth） |
| REST フォールバック用トークン | Cursor Secrets の `NOTION_TOKEN`（Internal Integration。親ページに「接続」済みであること） |
| タイムゾーン | すべて JST（`Asia/Tokyo`）。`対象日` は JST の日付 |

## 1. DB 一覧（ID 配線）

`data_source_id` は Notion MCP の `fetch` 結果に出る `collection://<uuid>` の uuid。`database_id` は DB ページ URL 末尾の 32 桁。

| キー | DB 名 | database_id | data_source_id | 自動化用ビュー URL | 状態 |
| --- | --- | --- | --- | --- | --- |
| `STOCKS` | 銘柄 | `TODO` | `TODO` | — | TODO |
| `EXPERTS` | 専属エキスパート | `TODO` | `TODO` | `TODO`（ビュー「自動化_設定中」） | TODO |
| `RULES` | ルール | `TODO` | `TODO` | — | TODO |
| `TASKS` | 日次タスク | `TODO` | `TODO` | `TODO`（ビュー「自動化_実行待ち」） | TODO |
| `REPORTS` | 日次レポート | `TODO` | `TODO` | `TODO`（ビュー「自動化_未振り返り」） | TODO |
| `KNOWLEDGE` | 知識 | `TODO` | `TODO` | — | TODO |
| `DECISIONS` | 最終判断 | `TODO` | `TODO` | — | TODO（AIは **読むだけ**） |
| `REVIEWS` | 振り返り | `TODO` | `TODO` | — | TODO |
| `LEARNINGS` | 学び | `TODO` | `TODO` | — | TODO |
| `AXES` | 分析観点 | `TODO` | `TODO` | `TODO`（ビュー「自動化_有効観点」） | TODO（別担当が `schema-spec.md` に定義中。未定義なら `docs/ai-advisor/reference-data.md` §4.3 の既定カタログを使う） |

## 2. 自動化用ビュー（Notion 側で人間が作る）

MCP の `query_data_sources` は SQL モードにプランの利用上限があり、**ビューモードは上限なし**。したがって取得はビュー経由を第一にする。ビューのフィルタが「拾う条件」の正本になるので、人間がビューを見れば「次に自動化が拾う行」がそのまま見える。

| ビュー名 | DB | フィルタ | 並び |
| --- | --- | --- | --- |
| 自動化_実行待ち | 日次タスク | `状態` = `READY_STATUS` かつ `目的` 空でない かつ `ルール` 空でない | `対象日` 昇順 → 作成日時 昇順 |
| 自動化_未振り返り | 日次レポート | `完了` = ✓ かつ `振り返り`（relation）が空 | `対象日` 昇順 |
| 自動化_設定中 | 専属エキスパート | `状態` = `設定中` または 作成日時が 14 日以内 | 作成日時 降順 |
| 自動化_有効観点 | 分析観点 | `状態` = `有効` | `対象目的` → `順序` 昇順 |

ビューを読むときも **必ず `page_size` / `limit` を付け、1 ページ目（上限件数）だけ** を読む。全ページ送りはしない（`guardrails.md` §6.6）。

## 3. 状態値（`状態` 列の語）

| キー | 値 | 意味 | 誰が付けるか |
| --- | --- | --- | --- |
| `READY_STATUS` | `入力中` **(TODO: 確定スキーマで「実行待ち」等になる可能性)** | 起動列が埋まり、AIが拾ってよい | 人間（列を埋めた結果） |
| `RUNNING_STATUS` | `実行中` | AIがロック中 | AI（日次ループ） |
| `REPORTED_STATUS` | `レポート済` | 日次レポートが完了条件を満たした | AI（日次ループ） |
| `AWAITING_REVIEW_STATUS` | `振り返り待` | 振り返り対象として待機 | 人間または AI |
| `DONE_STATUS` | `完了` | 振り返りが付いた | AI（日次振り返り） |
| `INSUFFICIENT_STATUS` | `不足` | 必須列欠落または完了条件未達。ループしない | AI（日次ループ） |

## 4. プロパティ名（スキルが参照する名前）

名前はすべて **完全一致** で使う（MCP の `fetch` で確認してから書く）。確定スキーマで改名されたら右列を直す。

### 4.1 日次タスク（`TASKS`）

| 論理名 | プロパティ名 | 型 | 備考 |
| --- | --- | --- | --- |
| タイトル | `タスク名` | title | 例 `2026-09-14 スクリーニング` |
| 利用者 | `利用者` | person | 任意 |
| 目的 | `目的` | select | `スクリーニング` / `企業分析` / `投資判断（売買計画）` |
| ルール | `ルール` | relation → ルール | 必須。`状態=発効` のみ有効 |
| 対象日 | `対象日` | date | 空なら AI が当日(JST)を入れてよい |
| 対象銘柄 | `対象銘柄` | relation → 銘柄 | 企業分析・投資判断で必須 |
| 専属 | `専属エキスパート` | relation | 空なら補完 |
| 状態 | `状態` | status | §3 |
| 完了条件 | `完了条件` | text | 目的からコピー |
| レポート | `日次レポート` | relation → 日次レポート | 1:1 |
| 最終判断 | `最終判断` | relation → 最終判断 | 人間 |
| 振り返り | `振り返り` | relation → 振り返り | |

### 4.2 専属エキスパート（`EXPERTS`）

`名前`(title), `オーナー`(person), `状態`(select: 設定中/運用中/休止), `現行ルール`(relation), `既定の目的`(select), `投資期間`(text), `1銘柄あたり金額`(text), `許容損失`(text), `見ない領域`(text), `低確信度のサイズ`(text, 初期「通常の半分」), `ウォッチ上限`(number)

制約4項目 = `投資期間` / `1銘柄あたり金額` / `許容損失` / `見ない領域`

### 4.3 ルール（`RULES`）

`ルールID`(title), `利用者`(person), `オーナー`(person), `専属エキスパート`(relation), `対象目的`(multi-select), `種別`(select: 共通テンプレ/個人), `バージョン`(text), `状態`(select: 草案/発効/失効/棄却), `上位`(relation → ルール), `根拠学び`(relation), `根拠振り返り`(relation), `発効日`(date), `変更要約`(text)

本文見出し: 1 選定基準 / 2 除外・見ない領域 / 3 企業分析で必ず見る項目 / 4 エントリー・損切り・利確・破綻（IF-THEN） / 5 ポジションサイズとRR / 6 評価・振り返りの見方 / 7 変更理由

`分析観点`(relation → 分析観点, **TODO**: 確定スキーマで追加される見込み。ルールが「この目的ではこの観点をこの順で見る」を宣言する。無ければ `対象目的` に対応する既定カタログの観点を順に使う)

### 4.4 日次レポート（`REPORTS`）

`レポート名`(title), `利用者`(person), `目的`(select), `対象日`(date), `元タスク`(relation → 日次タスク), `適用ルール`(relation → ルール), `対象銘柄`(relation → 銘柄), `根拠知識`(relation → 知識), `完了`(checkbox), `変化`(select: あり/なし)

### 4.5 知識（`KNOWLEDGE`）

`タイトル`(title), `種別`(select: 事実/計算/推論/不明), `共有範囲`(select: 全員共通/専属の解釈), `銘柄`(relation), `出典`(url), `基準日`(date), `データ品質`(select: 正常/要確認/欠損/確認不能), `一過性`(checkbox), `元タスク`(relation), `オーナー`(person)

### 4.6 最終判断（`DECISIONS`）— AIは作成・編集しない

`判断ID`(title), `利用者`(person), `元レポート`(relation), `元タスク`(relation), `銘柄`(relation), `最終判断`(select: 買う/待つ/見送る), `判断日`(date), `判断メモ`(text), `適用ルール`(relation), `反証条件`(text)

### 4.7 振り返り（`REVIEWS`）

`振り返りID`(title), `利用者`(person), `対象日`(date), `対象レポート`(relation → 日次レポート), `目的フィルタ`(multi-select), `ルール遵守`(select: ○/×/混在), `見落とし`(text), `ルール対応`(select: 変更なし/追記/修正/削除), `対象ルール`(relation → ルール), `草案ルール`(relation → ルール), `ベンチマーク対比`(text), `小サンプル`(checkbox)

### 4.8 学び（`LEARNINGS`）

`学びタイトル`(title), `利用者`(person), `専属エキスパート`(relation), `根拠振り返り`(relation), `確かさ`(select: 仮説/実地支持), `ルール化`(select: 未提案/草案済/発効済/棄却), `提案ルール`(relation), `範囲`(select: 個人のみ/共通テンプレ候補)

### 4.9 銘柄（`STOCKS`）

`名称`(title), `証券コード`(text, 一意キー), `市場`(select), `状態`(select: ウォッチ候補/監視中/対象外)

`市場` は JPX 由来（personal-only）になり得るため、AIは **書かない**（人間が入れる任意列）。業種を持つなら EDINET 由来の 33 業種だけ。

### 4.10 分析観点（`AXES`）— **TODO: 確定スキーマ待ち**

別担当が `schema-spec.md` / `automation-spec.md` に定義中。**それらが存在すればそれに従う。** 無い間の暫定形（`docs/ai-advisor/reference-data.md` §4.2 と同じ項目）:

| 論理名 | プロパティ名（暫定） | 型 | 意味 |
| --- | --- | --- | --- |
| 観点名 | `観点名` | title | 1 観点 = 1 問い |
| 対象目的 | `対象目的` | multi-select | スクリーニング / 企業分析 / 投資判断（売買計画） |
| 順序 | `順序` | number | 同じ目的内の処理順 |
| データ源 | `データ源` | select | kabulab-yuho-screening / kabulab-yuho-overseas / kabulab-yuho-trend / kabulab-ir-stock / kabulab-otakara-screening / kabulab-vwap-daily / EDINET / TDnet / 会社IR / Notion |
| エンドポイント | `エンドポイント` | url or text | 具体的な URL テンプレ（`{code}` 可）または Notion ビュー URL |
| フィールド | `フィールド` | text | 読む列（カンマ区切り）。これ以外は捨てる |
| 銘柄範囲 | `銘柄範囲` | select | タスクの対象銘柄 / 前回一覧 / 候補上位N / 指定リスト / 母集団（`limit` 必須） |
| 期間 | `期間` | text | 直近 N 期 / N か月 / 当日 / 直近 N 営業日 |
| 件数上限 | `件数上限` | number | API の `limit` / SQL の `LIMIT` に必ず入れる値 |
| 出典タグ | `出典タグ` | select | commercial-ok / factual-cite / primary / personal-only / no-store |
| 要約テンプレ | `要約テンプレ` | text | Notion に書く形（文字数上限つき） |
| 状態 | `状態` | select | 有効 / 無効 |

## 5. 実行パラメータ

| キー | 既定 | 意味 |
| --- | --- | --- |
| `MAX_TASKS_PER_RUN` | 5 | 日次ループが1回で処理する日次タスクの上限 |
| `MAX_AXES_PER_TASK` | 6 | 1タスクで処理する分析観点の上限（超えた観点は `確認不能（観点数の上限）`） |
| `MAX_ROWS_PER_AXIS` | 50 | 1観点で取得する行数の上限（観点の `件数上限` がこれより小さければそちら） |
| `MAX_FIELDS_PER_AXIS` | 8 | 1観点で読む列数の上限 |
| `MAX_STOCKS_PER_AXIS` | 20 | 1観点で対象にする銘柄数の上限（スクリーニング候補） |
| `MAX_FACTS_PER_AXIS` | 5 | 1観点の要約に書く数字（出典つき）の上限 |
| `MAX_SUMMARY_CHARS_PER_AXIS` | 600 | 1観点の要約の文字数上限（Notion に書く量） |
| `MAX_KNOWLEDGE_PER_AXIS` | 3 | 1観点で作る知識行の上限 |
| `MAX_KNOWLEDGE_PER_TASK` | 15 | 1タスクで作る知識行の上限 |
| `MAX_REPORTS_PER_REVIEW` | 20 | 振り返りが1回で読むレポート上限（ビュー 1 ページ目だけ） |
| `MAX_KNOWLEDGE_PER_REPORT_REVIEW` | 10 | 振り返りが 1 レポートあたり読む根拠知識の上限 |
| `PAST_REPORTS_TO_READ` | 3 | 同じ目的・同じルールの過去レポートを読む件数（本文は「入替」「推論」節だけ） |
| `DECISION_WAIT_DAYS` | 3 | 投資判断レポートの `最終判断` を待つ日数。超えたら最終判断なしで振り返る |
| `STALE_RUNNING_HOURS` | 6 | `実行中` のまま経過したら実行サマリーで警告（自動で戻さない） |

全表読みは禁止（`guardrails.md` §6.6）。上限で足りないときは `確認不能（観点の上限）` と書き、上限の見直しは人間が行う。

## 6. REST フォールバック（MCP が使えないときだけ）

```bash
# 値は表示しない。存在確認だけ
test -n "$NOTION_TOKEN" && echo "NOTION_TOKEN: set" || echo "NOTION_TOKEN: missing"

# データソースを問い合わせる（Notion API 2025-09-03 以降は data_sources エンドポイント）
curl -sS -X POST "https://api.notion.com/v1/data_sources/${DATA_SOURCE_ID}/query" \
  -H "Authorization: Bearer ${NOTION_TOKEN}" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  --data '{"filter":{"property":"状態","status":{"equals":"入力中"}},"page_size":5}'
```

トークンはヘッダにだけ載せ、レスポンスやログに写さない。

## 7. 確定時のチェックリスト

- [ ] §1 の 9 DB（＋ `分析観点`）の `database_id` / `data_source_id` を埋めた
- [ ] §2 の 4 ビューを Notion で作り、URL を §1 に貼った
- [ ] §4.10 の `分析観点` を `schema-spec.md` の定義に合わせ、`reference-data.md` §4.3 の既定カタログを Notion 側へ移した
- [ ] §3 の `READY_STATUS` を確定スキーマの語に合わせた
- [ ] §4 のプロパティ名を `fetch` 結果と突き合わせた（改名があれば右列を直した）
- [ ] `NOTION_TOKEN` の Integration を親ページに接続した（REST フォールバック用）
- [ ] 冒頭の `状態: 仮（TODO）` を `状態: 確定（YYYY-MM-DD）` に変えた

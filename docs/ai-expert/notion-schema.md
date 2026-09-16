# Notion スキーマ — 自己成長するあなただけのAI投資エージェント（5 DB）

親ページ名: **`AI投資エージェント`**。旧「AI専属アナリスト」8DB には relation しない。

DB は **名前で解決**する。下記 ID は 2026-09-16 に `notion-fetch` で照合済み（正本の転記: Project store `docs/ai-expert-notion.md`）。食い違えば **名前解決を優先** して実行サマリーに書く。

観点カタログ・参照資産カタログ・銘柄マスタは **DB にしない**。コードは `仕事` / `判断` のテキスト、正式名は commercial-ok の `name` だけ。円・結果％・TOPIX 列は無い。

## 0. 型の確定（MCP 実体）

| 計画上の型 | 実体 | 自動化・Web の扱い |
| --- | --- | --- |
| `エージェント.状態` `ルール.状態` `仕事.状態` | 計画は status。**実体は select**（MCP がカスタム status 選択肢を作れなかった） | フィルタ・更新は **`select` / `select_equals`**。`status`・`status_is`・`is_group`（to_do / in_progress / complete）は **使わない** |
| `判断ID` | 計画は text。**実体は title**（DB に他のタイトル列が無い） | 作成・検索は title。CF 円帯キーはタイトル文字列 |

語彙（選択肢名）は計画どおり。`ルール公開` checkbox の MCP 既定は false。Web がエージェント作成時に ON を入れる。

## 1. 識別子

親: page_id `3ddd74ff-84cd-8178-9abb-cf86708626c0` — https://app.notion.com/p/3ddd74ff84cd81789abbcf86708626c0

`data_source_id` は MCP の `collection://<uuid>`。REST の database query は `database_id`。

| キー | DB 名 | 環境変数 | database_id | data_source_id |
| --- | --- | --- | --- | --- |
| AGENTS | `エージェント` | `NOTION_AGENT_DB_ID` / `NOTION_AGENT_DS_ID` | `0bbeee51-024a-4930-937e-e27390c12572` | `f716eb85-55d8-4989-8693-575ed3a77387` |
| RULES | `ルール` | `NOTION_RULE_DB_ID` / `NOTION_RULE_DS_ID` | `ebe48548-1475-4139-9fed-d9becc1aefe2` | `517560c4-ff55-4524-a8f9-374e6d534d7c` |
| JOBS | `仕事` | `NOTION_JOB_DB_ID` / `NOTION_JOB_DS_ID` | `dd841447-06d0-4385-811e-ee52abf3185e` | `c8e1c2a2-18e2-4fcc-b853-927ee8975ec9` |
| DECISIONS | `判断` | `NOTION_DECISION_DB_ID` / `NOTION_DECISION_DS_ID` | `64bbb3ed-1a36-4d0b-8d4f-25f44ea219da` | `22d332de-be5e-4193-9280-c509262c7629` |
| REVIEWS | `振り返り` | `NOTION_REVIEW_DB_ID` / `NOTION_REVIEW_DS_ID` | `f6553c22-36d6-40de-a0c1-a38adc178790` | `cc35ddd1-7c2d-4678-9476-9cb1a6ae9a36` |

URL:

- エージェント https://app.notion.com/p/0bbeee51024a4930937ee27390c12572
- ルール https://app.notion.com/p/ebe48548147541399fedd9becc1aefe2
- 仕事 https://app.notion.com/p/dd84144706d04385811eee52abf3185e
- 判断 https://app.notion.com/p/64bbb3ed1a364d0b8d4f25f44ea219da
- 振り返り https://app.notion.com/p/f6553c2236d640dea0c1a38adc178790

## 2. 保存ビュー（仕事）

ビュー URL は `https://app.notion.com/p/<database id 32桁>?v=<view id 32桁>`。自動化はビューを信用しきらず、`対象日` ≤ 当日（空は可）を自分で見る。

| ビュー名 | フィルタ | URL |
| --- | --- | --- |
| `自動化_実行待ち` | (`状態` = 未着手) OR (`状態` = 実行中 AND `完了切片` is not empty)。AND `対象日` on or before today。`対象日` 昇順 | https://app.notion.com/p/dd84144706d04385811eee52abf3185e?v=3ddd74ff84cd81b08dc5000cfecbf101 |
| `再開待ち` | `状態` = 実行中。`対象日` 昇順 | https://app.notion.com/p/dd84144706d04385811eee52abf3185e?v=3ddd74ff84cd810d8762000cd0892b29 |
| `今日のレポート` | `状態` = レポート済 AND `対象日` is today。`対象日` 降順 | https://app.notion.com/p/dd84144706d04385811eee52abf3185e?v=3ddd74ff84cd8126ae31000c95dfd617 |

`today` は DSL `{type: exact, value: "today"}`。判断の「追跡中」「判断待ち（自分）」は未作成なら rows + `select` フィルタで代替（`limit` 付き）。

## 3. プロパティ

本文（ページ本体）は列ではない。旧 8DB への relation は無い。

### 3.1 `エージェント`

| プロパティ | 型 | 誰が | 内容 |
| --- | --- | --- | --- |
| エージェント名 | title | 人 / Web | 例: `はぴまねのエージェント` |
| オーナー | person | 人（運営が初回紐づけ） | Web は自動推定しない |
| WebユーザーID | text | Web | Google `sub`。値の運用以外に出さない |
| 状態 | **select** | 人 / Web | `設定中` / `運用中` / `休止`。自動化は `運用中` だけ回す |
| 投資期間 | text | 人 | 空なら `不足 CONSTRAINT_EMPTY:投資期間` |
| 1銘柄あたり金額 | text | 人 | 金額の言葉。円の時価は書かない |
| 許容損失 | text | 人 | |
| 見ない領域 | text | 人 | EDINET 33 業種の言葉 |
| 低確信度のサイズ | text | 人 | 既定「通常の半分」 |
| ウォッチコード | text | 人 / Web | 4 桁を最大 30。カンマ区切り |
| ルール公開 | checkbox | 人 / Web | 既定は Web が ON。OFF なら他人のルール一覧に出さない |
| 直近の学び | text | AI（夕） | 短文 |

逆側: `仕事` `判断`。

### 3.2 `ルール`

円の数値は本文に置かない。

| プロパティ | 型 | 誰が | 内容 |
| --- | --- | --- | --- |
| ルール名 | title | 人 / AI（草案） | |
| オーナー | person | 人 | 空なら共通 |
| 種別 | select | 人 | `共通` / `個人` |
| 目的 | select | 人 | `スクリーニング` / `売買判断` / `両方` |
| 方向 | select | 人 | `買い` / `売り` / `両方` |
| 状態 | **select** | 人（発効・棄却）/ AI（草案・同系旧版の失効） | `草案` / `発効` / `失効` / `棄却` |
| 前バージョン | relation → ルール | AI | 逆側 `次バージョン` |
| 発効日 | date | AI 補完 | |
| 変更要約 | text | AI 追記 | |

発効ルールが 0 ならその利用者の仕事は回さず `不足 RULE_UNRESOLVED`。他人のルールは Web で読めるが、**適用は自分の発効＋共通だけ**。

### 3.3 `仕事`

| プロパティ | 型 | 誰が | 内容 |
| --- | --- | --- | --- |
| 仕事名 | title | AI / Web | |
| 利用者 | person | 人 / Web | |
| エージェント | relation → エージェント | AI 補完 | |
| 目的 | select | 人 / Web | `スクリーニング` / `売買判断` のみ |
| 対象日 | date | AI 補完 | 空＝当日（JST） |
| 対象コード | text | 人 / Web | 売買判断は必須 |
| 方向 | select | 人 / Web | 売買判断: `買い` / `売り` / `両方` |
| 状態 | **select** | AI | `未着手` / `不足` / `実行中` / `レポート済` |
| 変化 | select | AI | `初回` / `あり` / `なし` |
| 適用ルール | relation → ルール | AI（開始時に固定） | |
| 完了切片 | text | AI | 例: `地合い,受注` |
| 要約 | text | AI | ≤200 字 |
| 実行メモ | text | AI | |
| 起票元 | select | Web / AI | `Web` / `繰り返し` / `連鎖` / `Notion` |
| 繰り返し | select | 人 | `なし` / `毎営業日` |

`不足` は select 選択肢として存在する。グループ代替は不要。

### 3.4 `判断`

| プロパティ | 型 | 誰が |
| --- | --- | --- |
| 判断ID | **title** | AI（一意。CF 円帯のキー） |
| 元仕事 | relation → 仕事 | AI |
| コード | text | AI（4 桁。事後修正しない） |
| 銘柄名 | text | AI（commercial-ok の name のみ） |
| 目的 | select | AI（`スクリーニング` / `売買判断`） |
| 方向 | select | AI（`買い` / `売り`） |
| 利用者 | person | AI |
| エージェント | relation → エージェント | AI |
| 適用ルール | relation → ルール | AI |
| AIの結論 | select | AI（`通過` / `除外` / `確認不能` / `条件成立` / `押し目待ち` / `戻り待ち` / `監視のみ` / `見送り`） |
| 観点別寄与 | text | AI |
| AIの一言 | text | AI |
| 確信度 | select | AI（`高` / `中` / `低`） |
| 入らない理由 | text | AI |
| 制約との一致 | select | AI（`○` / `×` / `確認不能`） |
| 分類 | select | AI（`条件成立` / `押し目待ち` / `戻り待ち` / `監視のみ` / `見送り` / `確認不能`） |
| 反証条件 | text | AI |
| エントリー条件 | text | AI |
| 損切り条件 | text | AI |
| 利確条件 | text | AI |
| サイズ方針 | text | AI |
| 円帯キー | text | AI（CF 側 UUID。数値ではない） |
| 最終判断 | select | **人だけ**（`残す` / `落とす` / `買う` / `売る` / `待つ` / `見送る`） |
| 判断メモ | text | **人だけ** |
| 判断日 | date | AI（夕） |
| 追跡メモ | text | AI（夕） |
| ルール遵守 | select | AI（夕） |
| 見落とし | text | AI（夕） |

### 3.5 `振り返り`

| プロパティ | 型 | 誰が |
| --- | --- | --- |
| 振り返り名 | title | AI（`YYYY-MM-DD 振り返り`） |
| 利用者 | person | AI |
| 対象日 | date | AI |
| ルール遵守 | select | AI |
| ルール対応 | select | AI（`変更なし` / `追記` / `修正` / `削除`） |
| 外した切片 | text | AI |
| 学び | text | AI |
| 草案ルール | relation → ルール | AI |

## 4. MCP / REST のフィルタ例

```json
{ "property": "状態", "select": { "equals": "運用中" } }
```

更新:

```json
{ "状態": { "select": { "name": "実行中" } } }
```

判断の新規:

```json
{ "判断ID": { "title": [{ "type": "text", "text": { "content": "2026-09-16 売買判断 6098" } }] } }
```

`status_equals` / `status_is` は旧 8DB 専用。この 5DB では使わない。

## 5. 文脈予算

- エージェント: 必要列のみ（制約4・ウォッチ・低確信度のサイズ・状態・WebユーザーID・ルール公開）
- ルール: 発効行の共通節と該当切片節
- 仕事本文: 切片の節と `## 統合` だけを後段の入力にする
- 過去判断: 同じ利用者×コード、20 行
- DB クエリは必ずフィルタ＋`limit`（実行待ち 20、ルール 100、運用中エージェント 10）

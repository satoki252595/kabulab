# Cursor Automations セットアップガイド — AI専属アナリスト（自己成長する AI 投資家アドバイザー）

- 日付: 2026-09-15（Cursor Automations の仕様は 2026-09 時点の公式ドキュメントに基づく）
- 対象: このリポジトリ（`satoki252595/kabulab`）と Notion ワークスペース「はぴまね」で、日次ループを Cursor Automations で回す運用者
- 状態: **雛形**。Notion の DB ID・ビュー URL・`分析観点` 定義は確定待ち（`docs/ai-advisor/notion-schema.md` の `TODO`）。配線が済むまで自動化は「読み取り確認だけ」で終了する設計

---

## 0. 全体像

```plain
人間: 日次タスク の起動列を埋める（目的 / ルール / 対象日 / 必要なら対象銘柄）
  └─ Notion ビュー「自動化_実行待ち」に載る
Automation ①「日次ループ」（定時 or Notion webhook）
  ├─ 前検査（発効ルール・制約4項目・対象銘柄）→ 欠けていれば 状態=不足 ＋コメント
  ├─ 分析観点を 1 つずつ: スライス取得 → 要約を 日次レポート に追記 → 捨てる
  └─ 結論節を書き 完了 → 日次タスク 状態=レポート済
人間: 投資判断レポートだけ 最終判断（買う / 待つ / 見送る）を 1 行書く
Automation ②「日次振り返り」（毎日 19:00 JST）
  ├─ 未振り返りレポートを 1 件ずつ当時の適用ルールで検査 → 振り返り に追記
  └─ 学び を書き、必要なら ルール の 草案 行を作る（発効はしない）
人間: 草案を読み、ルールを追記 / 修正（新バージョン発効）/ 失効
Automation ③「オンボーディング確認」（任意・毎朝）: 新しい 専属エキスパート 行の不足をコメント
```

| 置き場所 | 何が入っているか |
| --- | --- |
| Cursor ダッシュボード（cursor.com/automations） | 3 つの Automation（トリガー・リポジトリ・ツール・モデル・権限・**短いプロンプト**） |
| `.cursor/skills/ai-advisor-*/SKILL.md` | 各 Automation の **手順本体**（Git で版管理。ダッシュボードのプロンプトはこれを呼ぶだけ） |
| `docs/ai-advisor/automations/*.md` | ダッシュボードに貼るプロンプト全文と設定値 |
| `docs/ai-advisor/guardrails.md` | 絶対ルール（表現・ライセンス境界・データ読み込みの原則） |
| `docs/ai-advisor/notion-schema.md` | DB ID・ビュー・プロパティ名・状態値・上限（配線の唯一の場所） |
| `docs/ai-advisor/reference-data.md` | 参照データ源（kabulab 公開 API）・出典タグ・`分析観点` のスライス |
| `AGENTS.md`（リポジトリ直下） | Cloud Agent（= Automation の実行体）が最初に読む短い案内 |
| Notion | 知識・設定・成果物の正本（DB 9〜10 個＋自動化用ビュー） |

---

## 1. 調査結果の要点（Cursor Automations, 2026-09）

| 論点 | 現状 | この設計での扱い |
| --- | --- | --- |
| 作り方 | ダッシュボード（cursor.com/automations）、Agents Window、ローカルの `/automate` スキル、Marketplace テンプレート。**リポジトリ内ファイルや API で Automation 本体を定義する方法は無い**（Automations as Code / Automations API は要望段階。保存後に生成される Webhook URL＋API キーで外部から起動だけできる） | プロンプトの正本は `docs/ai-advisor/automations/*.md` に置き、ダッシュボードへ貼る。手順本体は `.cursor/skills` に置き、プロンプトから読ませる |
| 実行体 | Automation は Cloud Agent を起動する。**リポジトリを 1 つ指定すると、そのリポの `AGENTS.md` と `.cursor/skills/*/SKILL.md`（`.agents/skills/` も可）が読める** | `satoki252595/kabulab` @ `main` を必ず指定する（Cron/Slack トリガーの既定は「リポジトリなし」なので明示する） |
| トリガー | Scheduled（プリセット or cron。**cron は UTC**。遅延はあるが早く動くことはない）、GitHub/GitLab/Bitbucket、Slack（公開チャンネル）、**Webhook**（保存後に URL と API キー。`Authorization: Bearer …` 必須）、Linear、Sentry、PagerDuty。1 Automation に複数トリガー可 | 日次ループ: cron 3 本＋任意で Notion DB オートメーション（Send webhook）から即時起動。振り返り: cron 1 本 |
| シークレット | ダッシュボード Cloud Agents → Secrets。種別は Environment Variable / **Runtime Secret**（値は `[REDACTED]` に置換）/ Build Secret。環境変数として注入。**起動時に注入**（追加後は新しい実行から） | `NOTION_TOKEN`（この環境に既にある）を Runtime Secret に。Cloudflare 系は任意 |
| MCP | 個人 MCP は cursor.com/agents の MCP ドロップダウンで追加。チームは Dashboard → Integrations & MCP。HTTP 推奨、OAuth はユーザーごと。Automation 側で **ツール「MCP server」を ON にして接続** する | 既存の `Notion` MCP を各 Automation で ON |
| モデル | Automation ごとに選択。コンテキストは常に最大（切替なし） | 日次ループ・振り返りは推論の強い上位モデル。オンボーディング確認は標準で可 |
| ツール | PR 作成（既定 ON）、PR コメント、レビュアー依頼、Slack 送信/読取、MCP、**Memories（既定 ON、`MEMORIES.md`）**、Computer use（既定 ON） | Memories **OFF**（正本は Notion）。PR 作成 **OFF**。Slack OFF |
| 権限と課金 | Private（自分の認可で動く。自分に課金）/ Team Visible / Team Owned（チームのサービスアカウント。チームに課金）。Cloud Agent の API 従量課金、利用上限（spend limit）あり | まず Private。多人数運用で Team Owned に上げる際は MCP 認可を再設定 |
| 実行上限 | 実行ごとの時間・費用の上限設定は **無い**（月次の利用上限と手動キャンセルのみ）。同時実行数はプラン依存（Pro は 8 と案内） | スキル側に件数上限（`MAX_TASKS_PER_RUN` 等）を持ち、1 回の実行を短く保つ |

---

## 2. 前提条件チェック

- [ ] Cursor は有料プラン。GitHub 連携済みで `satoki252595/kabulab` に読み書き権限がある
- [ ] Cloud Agents → Secrets に `NOTION_TOKEN` がある（この環境で `CLOUD_AGENT_INJECTED_SECRET_NAMES=NOTION_TOKEN` を確認済み）
- [ ] cursor.com/agents の MCP 一覧に `Notion` があり、認可（OAuth）が済んでいる
- [ ] Notion ワークスペース「はぴまね」に親ページ「AI専属アナリスト」と DB（銘柄 / 専属エキスパート / ルール / 日次タスク / 日次レポート / 知識 / 最終判断 / 振り返り / 学び、＋分析観点）がある — **別担当の再設計待ち**
- [ ] `NOTION_TOKEN` の Internal Integration が親ページに「接続」されている（REST フォールバック用）
- [ ] この PR がマージされ、`main` に `AGENTS.md` / `.cursor/skills/ai-advisor-*` / `docs/ai-advisor/*` がある（Automation は `main` を読む）

---

## 3. Notion 側の準備（人間がやる）

1. 各 DB のプロパティ名を `docs/ai-advisor/notion-schema.md` §4 と突き合わせる（違えば **schema 文書の右列を直す**。DB 側を合わせる必要はない）。
2. 自動化用ビューを 4 つ作る（`notion-schema.md` §2）:
   - 日次タスク → 「自動化_実行待ち」（`状態` = 実行待ちの語 かつ `目的`・`ルール` 非空。`対象日` 昇順）
   - 日次レポート → 「自動化_未振り返り」（`完了` = ✓ かつ `振り返り` 空）
   - 専属エキスパート → 「自動化_設定中」（`状態` = 設定中 または作成 14 日以内）
   - 分析観点 → 「自動化_有効観点」（`状態` = 有効。`対象目的` → `順序`）
3. 各ビューの URL と、各 DB の `database_id` / `data_source_id`（MCP `fetch` の `collection://…`）を `notion-schema.md` §1 に貼る。
4. 「AI専属アナリスト」ページの「接続」に `NOTION_TOKEN` の Integration を追加する。
5. （任意・Notion 有料プラン）`日次タスク` の DB オートメーションで「`状態` が 実行待ちの語 になったら **Send webhook**」を作る（§6 で URL とヘッダを設定）。

---

## 4. Cursor 側の準備（人間がやる）

1. **Secrets**（cursor.com/dashboard → Cloud Agents → Secrets）
   - `NOTION_TOKEN` … 種別を **Runtime Secret** にする（Environment Variable になっていたら作り直す）。必須。
   - 任意（後日、公開 API で足りなくなったときだけ）: `CLOUDFLARE_API_TOKEN`（D1 **Read** 権限のみ）・`CLOUDFLARE_ACCOUNT_ID`・`D1_DATABASE_ID`。R2 用の `R2_*` は **不要**（中身が personal-only で Notion に書けるものが無い）。
   - トークンはリポジトリ・ドキュメント・Notion・Issue/PR に書かない。
2. **MCP**（cursor.com/agents → MCP）… `Notion` が有効で、認可済みであることを確認。
3. **リポジトリ** … Automation の Repository で `satoki252595/kabulab` を選べることを確認（GitHub App のインストール範囲）。

---

## 5. Automation ①「AI専属アナリスト｜日次ループ」を作る

設定値とプロンプト全文: `docs/ai-advisor/automations/daily-loop-runner.md`

1. cursor.com/automations → **New automation**。
2. **Name**: `AI専属アナリスト｜日次ループ`
3. **Triggers** → Scheduled → Cron expression を 3 本追加（cron は UTC。§8 の表参照）:
   - `30 22 * * 0-4`（月〜金 07:30 JST）
   - `30 3 * * 1-5`（月〜金 12:30 JST）
   - `30 7 * * 1-5`（月〜金 16:30 JST）
   プリセット UI にタイムゾーン欄が出る場合は `Asia/Tokyo` で 07:30 / 12:30 / 16:30 平日を選んでもよい（どちらか一方。二重登録しない）。
4. **Repository** → Single repository → `satoki252595/kabulab` / `main`。
5. **Prompt** → `daily-loop-runner.md` の「プロンプト（このまま貼る）」を貼る。
6. **Tools**:
   - MCP server → **ON** → `Notion` を選ぶ
   - Memories → **OFF**
   - Pull request creation → **OFF**（トグルが無ければそのまま。プロンプトで禁止済み）
   - Send to Slack / Read Slack / Comment on PR / Request reviewers → OFF
7. **Model** → 長文推論に強い上位モデル（Auto でも可）。
8. **Permissions** → Private。
9. **Save** → **Activate**（配線前は実行しても「未配線」サマリーで終わるだけ。まず §10 のテストで確認してから Activate でもよい）。

---

## 6. （任意）Notion から即時起動する: Webhook トリガー

「行を埋めた瞬間に走る」を文字どおりにしたい場合。Notion の有料プランが必要。

1. Automation ① を開き **Triggers** → **Webhook** を追加 → **Save**（保存後に Webhook URL と API キーが出る。「Generate auth header」で `Authorization: Bearer crsr_…` をコピー）。
2. Notion の `日次タスク` → オートメーション → 新規: トリガー「`状態` が〈実行待ちの語〉に変更されたとき」→ アクション **Send webhook**:
   - URL: 手順 1 の Webhook URL
   - **Add custom header**: Key `Authorization` / Value `Bearer crsr_…`
   - 送るプロパティ: `タスク名`（ページ URL が本文に入る）
3. 動作: Webhook で起動しても、Automation は **同じスキル**を実行する（ビュー「自動化_実行待ち」を読む）。ペイロードに依存しないので、cron と併用しても二重処理はロック（`状態=実行中`）で防ぐ。
4. Automation を Team Owned に上げたら Webhook API キーを再生成し、Notion 側の値も更新する。

---

## 7. Automation ②「日次振り返り」と ③「オンボーディング確認」を作る

| | ② 日次振り返り | ③ オンボーディング確認（任意） |
| --- | --- | --- |
| 設定・プロンプト | `docs/ai-advisor/automations/daily-review.md` | `docs/ai-advisor/automations/onboarding-check.md` |
| Trigger（UTC cron） | `0 10 * * *`（毎日 19:00 JST。平日のみなら `0 10 * * 1-5`） | `0 23 * * *`（毎日 08:00 JST） |
| Repository | `satoki252595/kabulab` / `main` | 同じ |
| Tools | MCP `Notion` ON / Memories OFF / PR OFF / Slack OFF | 同じ |
| Model | 上位モデル | 標準で可 |
| Permissions | Private | Private |

手順は §5 と同じ（Name → Triggers → Repository → Prompt → Tools → Model → Permissions → Save → Activate）。

---

## 8. スケジュール（JST ⇄ UTC）

Cursor の cron は **UTC**。JST = UTC+9 なので、**09:00 JST より前の時刻は前日の UTC** になり、曜日指定もずれる（月〜金 07:30 JST = 日〜木 22:30 UTC）。

| 目的 | JST | UTC cron | 備考 |
| --- | --- | --- | --- |
| 日次ループ 1 回目 | 月〜金 07:30 | `30 22 * * 0-4` | 寄付き前。前日夕方〜朝に埋めた行を拾う |
| 日次ループ 2 回目 | 月〜金 12:30 | `30 3 * * 1-5` | 昼休み |
| 日次ループ 3 回目 | 月〜金 16:30 | `30 7 * * 1-5` | 大引け後。TDnet の 15:30 開示を含められる |
| 日次振り返り | 毎日 19:00 | `0 10 * * *` | 3 回目のあと、人間が `最終判断` を書く時間を挟む |
| オンボーディング確認 | 毎日 08:00 | `0 23 * * *` | |
| （代替）日次ループ 毎時 | 月〜金 07:00–20:00 | `0 22,23 * * 0-4` と `0 0-11 * * 1-5` | 実行回数 14 回/日。実行待ち 0 件なら数十秒で終わる |

注意:

- Cursor スタッフはフォーラムで `CRON_TZ=Asia/Tokyo 30 7 * * 1-5` のような接頭辞が使える可能性を示しているが、公式ドキュメントには無い。使うなら 1 本だけで試し、実行履歴の時刻で確認する。
- タイムゾーン絡みで「1 時間早くも走る」「曜日がずれる」不具合報告が 2026 年前半にあった。作成後 1 週間は実行履歴（Runs）の時刻を見る。
- 祝日・休場日は cron では判定しない。行が無ければ「実行待ち 0 件」で即終了する（費用は僅少）。休場日に `対象日` を入れた行は、そのまま処理される（レポートに基準日を書く）。

---

## 9. 参照データ（既定 = kabulab 公開 API、任意 = D1/R2）

正本: `docs/ai-advisor/reference-data.md`

- **既定（シークレット不要）**: `https://kabulab-cf.satoki252595.workers.dev` の公開 JSON API。
  - 書いてよい: `/yuho-quant/api/screening`、`/yuho-quant/api/screening-overseas`、`/yuho-quant/api/trend/{code}`（EDINET 由来 = commercial-ok）、`/ir-catalog/api/stock/{code}`、`/ir-catalog/file/{tdnetId}`（TDnet 由来 = factual-cite）
  - 読めるが書かない: `/otakara-yutai/api/screening` の `price/per/pbr/dividendYield/yutaiYield/rsi14/各スコア`、`/vwap-analysis/api/daily|intra|margin`（Yahoo / JPX 由来 = personal-only）
  - 撤去済み: `/rsi-screening/api/*`（404）
- **任意（後日）**: D1 REST（`CLOUDFLARE_API_TOKEN` D1 Read ＋ `CLOUDFLARE_ACCOUNT_ID` ＋ `D1_DATABASE_ID`）。SELECT だけ。`core_stocks` の personal-only 列と `yutai_benefits.description` は選ばない。R2 は不要。
- 一次情報（EDINET / TDnet / 会社 IR）は、公開 API で足りない事実を補うときに、観点が指す文書だけを読む。

---

## 10. データ読み込みの原則（観点単位・全表読み禁止）

前提: **データ全体をコンテキストに載せない。** 正本は `guardrails.md` §6.6 と `reference-data.md` §4。

| 原則 | 具体 |
| --- | --- |
| 読む順 | ① 設定（当該タスク 1 ページ → 専属 1 ページ → 発効ルール 1 ページの必要な見出し → 観点一覧）→ ② 観点ごとにスライス → ③ 結論節は観点要約だけから |
| 観点単位 | `分析観点` を 1 つずつ。各観点は **エンドポイント / フィールド / 銘柄 / 期間 / 件数上限 / 出典タグ / 要約テンプレ** を宣言する（Notion の `分析観点` DB が正本。未定義なら `reference-data.md` §4.3 の既定カタログ） |
| 観点ごとの予算（既定） | 行 ≤ `MAX_ROWS_PER_AXIS`=50、列 ≤ 8、銘柄 ≤ 20、要約 ≤ 600 字、数字 ≤ 5 個、知識行 ≤ 3。1 タスク ≤ 6 観点、1 実行 ≤ 5 タスク。振り返りは 1 実行 ≤ 20 レポート、1 レポートの根拠知識 ≤ 10（`notion-schema.md` §5） |
| 要約して捨てる | 観点の要約を **Notion（レポート本文の節・知識行）に書いた時点** でその観点の生データを捨てる。次の観点は前の観点の要約だけを前提にする。再取得・再掲をしない。レポート／振り返り行は **先に空で作り、追記していく**（途中で落ちても書いた分が残る） |
| 全表読みの禁止 | `limit` なしの API 呼び出し・全銘柄ループ・全ページ送り・`SELECT *`・`LIMIT` なし SQL・`日次レポート`／`知識`／`ルール` DB の総なめ・R2/D1 ダンプ — すべて禁止。ビューは 1 ページ目だけ。ページは `fetch` 1 件ずつ |
| 上限に当たったら | `確認不能（観点の上限）` と書いて先へ進む。上限や観点定義の見直しは **実行サマリーで提案**し、人間が Notion の `分析観点` を直す（自動化は変えない） |
| 確定スキーマとの関係 | 別担当が `分析観点` の定義を schema-spec / automation-spec に追加中。**存在すればそれに従う**。それまでの既定カタログは暫定 |

---

## 11. ガードレール（AI が絶対にしないこと）と、どこで強制するか

| ガードレール | 強制する場所 |
| --- | --- |
| 「買う」「今すぐ買う」「おすすめ」「推奨」「必ず」「確実」を書かない（AI所見は 有利寄り / 中立 / 回避寄り、材料分類は 監視のみ / 押し目待ち / 見送り） | プロンプト・スキル §8 自己検査・振り返りの語彙検査 |
| 未発効（草案 / 失効 / 棄却）のルールを使わない。他人の個人ルールを適用しない | 日次ループ §3 前検査（違反は `不足`） |
| 注文・発注しない。証券 API・自動売買は持たない | ツール構成（Notion MCP のみ）・プロンプト |
| `最終判断` 行を作らない・編集しない | プロンプト・スキル。Notion 側で `最終判断` DB の編集権限を人間に限定してもよい |
| ルールを発効・失効しない。既存ルール本文を書き換えない（草案は新しい行だけ） | 振り返りスキル §5・自己検査。人間が草案を読んで発効する |
| 過去レポートの数字を書き換えない | 振り返りスキル（誤りは振り返りに書く） |
| 捏造しない。取れない数字は `確認不能`。事実 / 計算 / 推論を分け、買わない理由 3 つを先に書く | スキルの本文テンプレ・自己検査 |
| **personal-only（Yahoo / JPX / 日証金 由来）の値を Notion に書かない。みんかぶ由来の掲載文はどこにも書かない。業種は EDINET 33 業種だけ** | `reference-data.md` §1・スキル自己検査・振り返りの「ライセンス境界」検査 |
| **データ全体を読まない（観点単位・スライス・上限・全表読み禁止）** | `guardrails.md` §6.6・スキルの観点ループ・実行サマリーの観点別行数 |
| リポジトリを変更しない。PR を作らない。Slack へ出さない。Memories に頼らない。シークレット値を出力しない | ツール設定（PR OFF / Memories OFF / Slack OFF）・Runtime Secret・プロンプト |
| 1 回の実行で処理する件数の上限、二重処理の防止（`状態=実行中` ロック） | スキル §2・§4 |

---

## 12. テスト（1 回だけ動かして確かめる）

### 12.1 配線前（今できる）

1. Automation ① を Save（Activate はしなくてよい）→ **Test run / Run now**。
2. 期待: 実行サマリーに「未配線: TASKS/REPORTS/…」と出て、Notion に **何も書かれない**。Notion MCP が繋がっていれば親ページ配下の DB 名が列挙される。
3. 失敗するなら: MCP 認可（cursor.com/agents → MCP → Notion）、Repository が `kabulab` になっているか、プロンプトがスキルのパスを指しているか。

### 12.2 配線後（正常系）

1. Notion で `専属エキスパート` 1 行（オーナー・制約4項目・低確信度のサイズ・ウォッチ上限・既定の目的）と、`ルール` v1（`状態=発効`、`対象目的` にスクリーニング）を用意する。
2. `日次タスク` に 1 行: `目的=スクリーニング`、`ルール`=v1、`対象日`=当日、`状態`=実行待ちの語。ビュー「自動化_実行待ち」に載ることを確認。
3. Automation ① → **Test run**。
4. 確認:
   - `日次タスク.状態` が `実行中` → `レポート済` に変わった
   - `日次レポート` が 1 行でき、本文に「0. 適用ルールと制約」→「観点: …」節 → 一覧表 / 落とした銘柄 / 確認不能 / 入替 / 免責文 がある。`完了`=✓、`変化` が入っている
   - 本文・`知識` に `買う` / `おすすめ` が無い。株価・PER・RSI の **数値** が無い（あれば「kabulab で本人確認」と URL）。みんかぶ由来の掲載文が無い
   - 数字に出典 URL＋基準日、または `確認不能`
   - 実行サマリーに観点ごとの取得行数（すべて上限以内）が出ている
5. Automation ② → **Test run** → `振り返り` 1 行、`ルール遵守`、`見落とし`。草案が作られていれば `状態=草案` で、元ルールの `状態` が変わっていない。

### 12.3 異常系

- `ルール` を外した行 → `状態=不足` になり、コメントに「ルールが空です」。レポートは作られない。
- `ルール` の `状態` を `草案` にした行 → `不足`、コメントに「発効ではありません」。
- 制約 4 項目のどれかを空にした専属 → `不足`、コメントに項目名。

### 12.4 Webhook（§6 を設定した場合）

```bash
# 値を貼らずに環境変数から。Notion 側設定の前に疎通だけ確認
curl -sS -X POST "$CURSOR_AUTOMATION_WEBHOOK_URL" \
  -H "Authorization: Bearer $CURSOR_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"source":"manual-test"}'
```

Runs に新しい実行が出れば疎通 OK。実行待ち 0 件なら数十秒で終わる。

---

## 13. 運用

- **実行履歴**: cursor.com/automations → 各 Automation → Runs。実行サマリーが会話の末尾に出る。失敗時は Cloud Agent の run を開いて MCP 認証エラー（`mcp_auth_error`）や `setup_failed` を見る。
- **費用**: Cloud Agent の API 従量課金。実行待ち 0 件の空実行は短い。Cloud Agents の利用上限（spend limit）を設定する。1 実行の上限はスキルの件数上限で抑える。
- **同時実行**: プラン依存（Pro は 8）。3 Automation を同時刻に置かない（07:30 / 08:00 / 19:00 と分けてある）。
- **失敗時**: `実行中` のまま残った行は次回サマリーで警告される。人間が `状態` を戻す。自動では戻さない。
- **トークン**: `NOTION_TOKEN` を更新したら Secrets を更新（新しい実行から反映）。Webhook API キーは Team Owned 昇格時に再生成。
- **Team Owned へ昇格**: 実行主体がチームのサービスアカウントに変わる。Notion MCP の OAuth をそのアカウントで再設定し、Secrets をチーム/環境スコープに置く。
- **Memories は OFF のまま**: 正本は Notion。実行間の記憶が判断を汚染しないようにする。
- **上限の見直し**: 実行サマリーの「観点の上限見直し提案」が続く観点は、人間が Notion の `分析観点`（件数上限・期間）を直す。自動化は定義を変えない。

---

## 14. 配線チェックリスト（DB ID 確定後にこの PR を仕上げる）

- [ ] `docs/ai-advisor/notion-schema.md` §1 の `database_id` / `data_source_id`（9 DB ＋ 分析観点）
- [ ] 同 §1 のビュー URL 4 本、§3 の `READY_STATUS` の語
- [ ] 同 §4 のプロパティ名を `fetch` と突き合わせ、§4.10 `分析観点` を schema-spec に合わせる
- [ ] `reference-data.md` §4.3 の既定カタログを Notion の `分析観点` へ移し、暫定表記を外す
- [ ] `notion-schema.md` 冒頭を `状態: 確定（YYYY-MM-DD）` に
- [ ] §12.1 → §12.2 → §12.3 のテストを通す
- [ ] 3 Automation を Activate

---

## 15. 参考

- Cursor Automations: https://cursor.com/docs/cloud-agent/automations ／ ヘルプ: https://cursor.com/help/ai-features/automations
- Cloud Agent 設定（Secrets・AGENTS.md）: https://cursor.com/docs/cloud-agent/setup ／ Secrets & Network: https://cursor.com/docs/cloud-agent/security-network
- Cloud Agent の MCP: https://cursor.com/docs/cloud-agent/capabilities#mcp-tools
- Skills（`.cursor/skills`）: https://cursor.com/docs/context/skills ／ Rules・AGENTS.md: https://cursor.com/docs/context/rules
- Notion「Send webhook」: https://www.notion.com/help/webhook-actions
- kabulab 公開 API のライセンス境界: https://github.com/satoki252595/kabulab_tool_cloudflare/blob/main/docs/HANDOFF-2026-09.md

# Cursor Automations セットアップガイド — 自己成長するAI投資家アドバイザー（AI専属アナリスト）

- 日付: 2026-09-15（Cursor Automations の仕様は 2026-09 時点の公式ドキュメント、自動化の中身は Project の `internal/automation-spec.md` / `internal/schema-spec.md` に基づく）
- 対象: このリポジトリ（`satoki252595/kabulab`）と Notion ワークスペース「はぴまね」で、日次ループを Cursor Automations で回す運用者
- 状態: **配線済み（2026-09-15）— 起動前の Notion 手作業あり（§2.5）**。8DB は構築済みで、ID・保存ビュー URL は `docs/ai-advisor/notion-schema.md` に転記、全 8 データソースのプロパティ名を `notion-fetch` で照合済み。MCP で設定できなかった点（`日次タスク.状態` の選択肢名、相対日付フィルタ、DB テンプレート、共通ルール v1 の発効、インテグレーションのコネクト）が人の手作業として残っている。スキルはその一部（状態名・日付絞り）を防御的に扱うが、**§2.5 が済むまで Activate しない**

---

## 0. 全体像

```plain
人: 日次タスク に行を起票（目的 を選ぶだけ。企業分析・投資判断は 対象銘柄 も）
  └─ 保存ビュー「自動化_実行待ち」に載る（状態=未着手）
Automation ①「朝レポート」06:00 JST 月–金
  ├─ ルール整理（同系の旧発効を失効・発効日補完）／準備（繰り返し展開・連鎖起票・再確認起票・不足の再評価）
  ├─ 行ごと: ロック → 起動条件（不足コード）→ 観点解決 → 分析観点 を 1 つずつ「切片取得 → 要約 → 本文に追記 → 捨てる」
  └─ 全観点後に 統合 → 判断 行の骨格（最終判断 は空）→ 状態=レポート済
人: 判断 の 最終判断 を選ぶ（残す/落とす/要分析・投資判断へ進む/監視/見送り・買う/待つ/見送る）
Automation ②「夕振り返り」18:00 JST 月–金
  ├─ 判断日 を刻む → 開いている判断を追跡（成立／未成立）→ 当日レポートを検査
  └─ 振り返り 行 → 必要なら ルール の 草案 行（発効は人）→ 専属エキスパート.直近の学び
Automation ③「随時実行」（任意）: Notion Send webhook または毎時ポーリングで、朝レポートの「実行」だけを対象行に
```

| 置き場所 | 何が入っているか |
| --- | --- |
| Cursor ダッシュボード（cursor.com/automations） | 3 つの Automation（トリガー・リポジトリ・ツール・モデル・権限・プロンプト） |
| `.cursor/skills/ai-advisor-{morning-report,evening-review,on-demand-run}/SKILL.md` | 各 Automation の **手順本体**（Git で版管理。ダッシュボードのプロンプトはこれを呼ぶ）。`morning-report/references/jp-holidays.md` は祝日リスト |
| `docs/ai-advisor/automations/*.md` | ダッシュボードに貼るプロンプト全文と設定値 |
| `docs/ai-advisor/guardrails.md` | 書いてよい列・禁止語・ライセンス境界・データ読み込みの原則・自己検査 |
| `docs/ai-advisor/notion-schema.md` | 8DB の名前・プロパティ・状態値・保存ビュー・文脈予算・ID（配線の唯一の場所） |
| `docs/ai-advisor/reference-data.md` | 参照資産の既定行・ライセンス階層・観点ごとの `curl`＋`jq` |
| `AGENTS.md`（リポジトリ直下） | Cloud Agent（= Automation の実行体）が最初に読む短い案内 |
| Notion 親ページ「AI専属アナリスト」 | 8DB: `専属エキスパート` `ルール` `分析観点` `参照資産` `銘柄` `日次タスク` `判断` `振り返り`。構築仕様は `internal/schema-spec.md` |

---

## 1. 調査結果の要点（Cursor Automations, 2026-09）

| 論点 | 現状 | この設計での扱い |
| --- | --- | --- |
| 作り方 | ダッシュボード（cursor.com/automations）、Agents Window、ローカルの `/automate` スキル、Marketplace テンプレート。**リポジトリ内ファイルや API で Automation 本体を定義する方法は無い**（Automations as Code / Automations API は要望段階。保存後に生成される Webhook URL＋API キーで外部から起動だけできる） | プロンプトの正本は `docs/ai-advisor/automations/*.md` に置き、ダッシュボードへ貼る。手順本体は `.cursor/skills` に置き、プロンプトから読ませる |
| 実行体 | Automation は Cloud Agent を起動する。**リポジトリを 1 つ指定すると、そのリポの `AGENTS.md` と `.cursor/skills/*/SKILL.md` が読める** | `satoki252595/kabulab` @ `main` を必ず指定する（Cron/Slack トリガーの既定は「リポジトリなし」なので明示する） |
| トリガー | Scheduled（プリセット or cron。**cron は UTC**。遅延はあるが早く動くことはない）、GitHub 等、Slack、**Webhook**（保存後に URL と API キー。`Authorization: Bearer …` 必須）、Linear、Sentry、PagerDuty。1 Automation に複数トリガー可 | 朝レポート: cron（06:00 JST。追加回は任意）。夕振り返り: cron。随時実行: Webhook（Notion Send webhook）または毎時 cron |
| シークレット | ダッシュボード Cloud Agents → Secrets。種別は Environment Variable / **Runtime Secret**（値は `[REDACTED]`）/ Build Secret。環境変数として **起動時に注入** | `NOTION_TOKEN`（この環境に既にある）を Runtime Secret に。Cloudflare 系は任意 |
| MCP | 個人 MCP は cursor.com/agents の MCP ドロップダウンで追加。チームは Dashboard → Integrations & MCP。HTTP 推奨、OAuth はユーザーごと。Automation 側で **ツール「MCP server」を ON にして接続** | 既存の `Notion` MCP を各 Automation で ON |
| モデル | Automation ごとに選択。コンテキストは常に最大 | 朝・夕は推論の強い上位モデル（Auto 可） |
| ツール | PR 作成（既定 ON）、PR コメント、レビュアー依頼、Slack 送信/読取、MCP、**Memories（既定 ON）**、Computer use（既定 ON） | Memories **OFF**（正本は Notion）。PR 作成 **OFF**。Slack OFF |
| 権限と課金 | Private（自分の認可で動く。自分に課金）/ Team Visible / Team Owned（チームのサービスアカウント）。Cloud Agent の API 従量課金、利用上限（spend limit）あり | まず Private。多人数運用で Team Owned に上げる際は MCP 認可を再設定 |
| 実行上限 | 実行ごとの時間・費用の上限設定は **無い**（月次の利用上限と手動キャンセルのみ）。同時実行数はプラン依存（Pro は 8） | 仕様の 1 ラン上限（タスク 10 行、観点 `軽` 8／`重` 1、利用者 10 人）で 1 回の実行を短く保つ |

---

## 2. 前提条件チェック

- [ ] Cursor は有料プラン。GitHub 連携済みで `satoki252595/kabulab` に読み書き権限がある
- [ ] Cloud Agents → Secrets に `NOTION_TOKEN` がある（この環境で `CLOUD_AGENT_INJECTED_SECRET_NAMES=NOTION_TOKEN` を確認済み）
- [ ] cursor.com/agents の MCP 一覧に `Notion` があり、認可（OAuth）が済んでいる
- [x] Notion 親ページ「AI専属アナリスト」直下に 8DB があり、名前が `schema-spec` どおり（構築記録 `internal/notion-ids.md` §11。既存リサーチ DB への relation 0 本）
- [x] 運営の初回入力のうち構築済み: `参照資産` 既定行（`有効` 12＋`保留` 5、有効 URL は疎通確認済み）、共通観点 15 行（有効 13）、`はぴまね 専属`（`状態=設定中`）、各 DB のビュー（32 本）
- [x] `internal/notion-ids.md` の 8DB の ID・保存ビュー URL を `docs/ai-advisor/notion-schema.md` §1・§2 に転記し、全 8 データソースを `notion-fetch` してプロパティ名を照合した（差分なし）
- [ ] **§2.5 の手作業**（インテグレーションのコネクト、`状態` 選択肢の改名、相対日付フィルタ、共通ルール v1 の発効、専属の制約4項目 …）
- [ ] この PR がマージされ、`main` に `AGENTS.md` / `.cursor/skills/ai-advisor-*` / `docs/ai-advisor/*` がある（Automation は `main` を読む）

### 2.5 起動前チェックリスト（Notion 側の手作業。構築記録 `internal/notion-ids.md` §10・§12）

MCP では設定できなかった項目。**1〜3 と 8〜9 が済むまで Activate しない**（Test run は §12.1 の範囲で可）。

| # | 手作業 | やらないと何が起きるか | スキル側の防御 |
| --- | --- | --- | --- |
| 1 | 自動化用 Notion インテグレーション（`NOTION_TOKEN` の持ち主。Notion MCP の認可ユーザーと同じでよい）を親ページ「AI専属アナリスト」に **編集権限でコネクト**（8DB は継承） | 自動化が 8DB を読めず「未解決」で終了、または書き込みが `WRITE_FAILED` | なし（必須） |
| 2 | `日次タスク.状態` の選択肢: `進行中` → **`実行中`**、`完了` → **`レポート済`** に改名し、To-do に **`不足`** を追加。改名後に `再開待ち`／`自動化_実行待ち` ビューのフィルタが外れていたら選び直す | 改名前でも動く（グループで解決）が、`不足` が無い間は不足行が `未着手` のまま `実行メモ` の `不足:<コード>` で表され、ボードで見分けにくい | 仕様名 → グループ代替。`不足` は `実行メモ` 先頭の `不足:` |
| 3 | 相対日付フィルタを手で追加: `今日`（`対象日` は 今日）、`自動化_実行待ち`（`対象日` は 今日以前）、`はぴまね 専属` の「今日の日次タスク」 | ビューに未来日の行が混ざる（人向けの見え方の問題） | 自動化は `対象日 ≤ 当日` を自前で絞る |
| 4 | `判断待ちあり` ビューのフィルタを `判断待ち > 0` に（暫定 `判断 is not empty`） | 人向けビューの精度だけ | 自動化は使わない |
| 5 | relation の「1 件に制限」（n:1／1:1 の 11 本: `日次タスク.ルール` `日次タスク.専属エキスパート` `ルール.専属エキスパート` `ルール.前バージョン` `分析観点.専属エキスパート` `参照資産.専属エキスパート` `判断.元タスク` `判断.銘柄` `判断.専属エキスパート` `判断.次タスク` `振り返り.専属エキスパート`）と person の「1 人に制限」（`オーナー` `利用者`） | 人が誤って複数を入れられる | 自動化は 1 件だけ入れ、読むときは先頭を使う |
| 6 | `分析観点.有効` の既定を ON に | 新しく作った観点が OFF のままだと回らない | なし（運営が行を作るとき確認） |
| 7 | 各 DB の `テンプレート｜…` 行を DB テンプレートに写す（`専属` はリンクドビューを「このページ」に） | 人の起票が少し手間になるだけ | 自動化はテンプレートに依存しない。`テンプレート｜`・`例｜` の行は処理対象外 |
| 8 | `共通 テンプレート v1`（草案・見出しのみ）を **目的ごとに複製して本文を書き `状態=発効`** に（`共通 スクリーニング v1` / `共通 企業分析 v1` / `共通 投資判断 v1`。`オーナー` 空、`対象観点` 空） | 発効ルールが 0 なので、すべてのタスクが `RULE_UNRESOLVED` で止まる | なし（仕様どおり止まる） |
| 9 | `はぴまね 専属` の制約4項目（`投資期間` `1銘柄あたり金額` `許容損失` `見ない領域`）を埋めて `状態=運用中` に | `EXPERT_NOT_ACTIVE`／`CONSTRAINT_EMPTY:<列名>` で止まる。夕振り返りの対象にもならない | なし（仕様どおり止まる） |
| 10 | 任意: `日次タスク` の例行（`例｜目的だけで起票した行…`）を削除、`ワークスペース共通` 行の作成、`参照資産` #16/#17 のライセンス調整 | — | 例行は Complete＋対象日なしなので拾わない |

チェックリストの原本と運営メモはオンボーディングページ「1行で始める」 https://app.notion.com/p/3dcd74ff84cd8145b678eb2e7ea6e04c の末尾トグルにもある。

---

## 3. Notion 側の状態（構築済み。残りは §2.5）

構築済み（`internal/notion-ids.md`）:

1. 8DB が親ページ直下のフルページ DB として存在（`日次タスク.状態` の既定値 `未着手` を実測）。ID は `notion-schema.md` §1。
2. 自動化が読む保存ビュー（URL は `notion-schema.md` §2）: `日次タスク`「自動化_実行待ち」（**`対象日 ≤ 今日` は手で追加 — §2.5-3**）、`分析観点`「自動化_有効観点」、`判断`「追跡中」「判断待ち（自分）」。
3. 運営の初回入力のうち済んでいるもの: `参照資産` 既定行 17（`有効` 12 の URL は HTTP 200 を確認。`必要Secret` は名前のみ）、共通観点 15 行（有効 13。`スライス` の `項目=` を 8 API の実応答と照合済み）。**未**: 共通ルール v1 ×3 の発効（§2.5-8）、`ワークスペース共通` 行（任意）。
4. メンバーの初回入力: `はぴまね 専属` 行あり（`状態=設定中`）。**未**: 制約4項目と `運用中`（§2.5-9）。
5. （任意・Notion 有料プラン）`日次タスク` の DB オートメーション「ページが追加された／`目的` が設定された → **Send webhook**」（§6）。

---

## 4. Cursor 側の準備（人がやる）

1. **Secrets**（cursor.com/dashboard → Cloud Agents → Secrets）
   - `NOTION_TOKEN` … 種別を **Runtime Secret** にする（Environment Variable になっていたら作り直す）。必須（REST フォールバック用。通常は Notion MCP を使う）。
   - 任意（`参照資産` #13〜#16 を `有効` にするときだけ）: `CLOUDFLARE_API_TOKEN`（D1 **Read** に絞った専用トークン）・`CLOUDFLARE_ACCOUNT_ID`・`D1_DATABASE_ID`。R2 用の `R2_*` は **不要**。
   - トークンをリポジトリ・ドキュメント・Notion・Issue/PR に書かない。
2. **MCP**（cursor.com/agents → MCP）… `Notion` が有効で認可済みであることを確認。
3. **リポジトリ** … Automation の Repository で `satoki252595/kabulab` を選べることを確認（GitHub App のインストール範囲）。

---

## 5. Automation ①「AI専属アナリスト｜朝レポート」を作る

設定値とプロンプト全文: `docs/ai-advisor/automations/morning-report.md`

1. cursor.com/automations → **New automation**。
2. **Name**: `AI専属アナリスト｜朝レポート`
3. **Triggers** → Scheduled → Cron expression（UTC）: `0 21 * * 0-4`（= 月〜金 06:00 JST）。1 日複数回にするなら `30 22 * * 0-4`（07:30）、`30 3 * * 1-5`（12:30）、`30 7 * * 1-5`（16:30）を追加（§3.0〜3.1 は冪等）。プリセット UI にタイムゾーン欄が出る場合は `Asia/Tokyo` で 06:00 平日を選んでもよい（どちらか一方。二重登録しない）。
4. **Repository** → Single repository → `satoki252595/kabulab` / `main`。
5. **Prompt** → `morning-report.md` の「プロンプト（このまま貼る）」を貼る。
6. **Tools**: MCP server → **ON** → `Notion` ／ Memories → **OFF** ／ Pull request creation → **OFF**（無ければそのまま）／ Slack・PR 系 → OFF。
7. **Model** → 長文推論に強い上位モデル（Auto 可）。
8. **Permissions** → Private。
9. **Save** → **Test run**（§12.1）→ §2.5 の手作業と §12.2 のテストが済んだら **Activate**。

---

## 6. （任意）Notion から即時起動する: 随時実行の Webhook

「行を起票した瞬間に走る」を文字どおりにしたい場合。Notion の有料プランが必要。

1. Automation ③「随時実行」（§7）を Webhook トリガーで作り **Save**（保存後に Webhook URL と API キーが出る。「Generate auth header」で `Authorization: Bearer crsr_…` をコピー）。
2. Notion の `日次タスク` → オートメーション → 新規: トリガー「ページが追加されたとき」または「`目的` が編集されたとき」→ アクション **Send webhook**:
   - URL: 手順 1 の Webhook URL
   - **Add custom header**: Key `Authorization` / Value `Bearer crsr_…`
   - 送るプロパティ: `タスク名`（ページ URL／ID が本文に入る。他の値は自動化が信用せず Notion から再読込みする）
3. 動作: 受信後 2 分待って行を再読込み → `未着手`／再開待ちなら朝レポートの「実行」だけを行う。cron と併用しても二重処理は行のロック（`状態=実行中`＋実行ID）で防ぐ。
4. Automation を Team Owned に上げたら Webhook API キーを再生成し、Notion 側の値も更新する。

---

## 7. Automation ②「夕振り返り」と ③「随時実行」を作る

| | ② 夕振り返り | ③ 随時実行（任意） |
| --- | --- | --- |
| 設定・プロンプト | `docs/ai-advisor/automations/evening-review.md` | `docs/ai-advisor/automations/on-demand-run.md` |
| Trigger | Scheduled `0 9 * * 1-5`（月〜金 18:00 JST。代替 19:00 → `0 10 * * 1-5`、翌朝 05:30 → `30 20 * * 0-4`） | Webhook（§6）または Scheduled `0 0-8 * * 1-5`（月〜金 09〜17 時 JST 毎時）。両方付けてもよい |
| Repository | `satoki252595/kabulab` / `main` | 同じ |
| Tools | MCP `Notion` ON / Memories OFF / PR OFF / Slack OFF | 同じ |
| Model | 上位モデル | 朝レポートと同じ |
| Permissions | Private | Private |
| 1 ランの上限 | 利用者 10 人、追跡判断 30 行／人 | Webhook 1 行／ポーリング 5 行 |

手順は §5 と同じ（Name → Triggers → Repository → Prompt → Tools → Model → Permissions → Save → Test run → Activate）。

---

## 8. スケジュール（JST ⇄ UTC。automation-spec §0.1）

Cursor の cron は **UTC**。JST = UTC+9 なので **09:00 JST より前の時刻は前日の UTC** になり、曜日もずれる（月〜金 06:00 JST = 日〜木 21:00 UTC）。

| Automation | JST | UTC cron | 備考 |
| --- | --- | --- | --- |
| 朝レポート | 月〜金 06:00 | `0 21 * * 0-4` | 前夜 20:00 JST の EDINET/TDnet 取込後。stock-sync（D1）は 06:00 JST 完了なので D1 を使う日は 06:30 以降に |
| 朝レポート（追加回・任意） | 07:30 / 12:30 / 16:30 | `30 22 * * 0-4` / `30 3 * * 1-5` / `30 7 * * 1-5` | 主に `重` 観点の再開。冪等 |
| 夕振り返り | 月〜金 18:00 | `0 9 * * 1-5` | 人が `最終判断` を選ぶ時間を挟む。代替 19:00 `0 10 * * 1-5`、翌朝 05:30 `30 20 * * 0-4` |
| 随時実行（ポーリング） | 月〜金 09〜17 時 毎時 | `0 0-8 * * 1-5` | Webhook が使えないとき |

注意:

- Cursor スタッフはフォーラムで `CRON_TZ=Asia/Tokyo 0 6 * * 1-5` のような接頭辞が使える可能性を示しているが、公式ドキュメントには無い。使うなら 1 本だけで試し、実行履歴の時刻で確認する。
- タイムゾーン絡みの不具合報告（1 時間早くも走る／曜日がずれる）が 2026 年前半にあった。作成後 1 週間は Runs の時刻を見る。
- 祝日・休場日の判定は自動化の中で行う（`jp-holidays.md`＋12/31〜1/3。判定できない日は営業日）。休場日は繰り返し展開をしないが、手で起票された行は処理する。

---

## 9. 参照データ（既定 = kabulab 公開 API、任意 = D1 REST）

正本: `docs/ai-advisor/reference-data.md`（= schema-spec §8・automation-spec §6）

- **既定（シークレット不要、`参照資産` の `有効` 12 行）**: `https://kabulab-cf.satoki252595.workers.dev` の公開 JSON API ＋ GitHub raw の銘柄リスト ＋ EDINET / TDnet。
  - 数値まで書ける（commercial-ok）: `/yuho-quant/api/screening`、`/yuho-quant/api/screening-overseas`、`/yuho-quant/api/trend/{code}`（EDINET 由来）
  - 事実引用（factual-cite）: `/ir-catalog/api/stock/{code}`、`/ir-catalog/file/{tdnetId}`（TDnet 由来）、お宝優待の自作要約
  - 読んで判定だけ（personal-only。値を書かない）: `/otakara-yutai/api/screening` の `price…totalScore`、`/vwap-analysis/api/{daily,intra,margin,chart}`
  - 撤去済み: `/rsi-screening/api/*`（404）
- **任意（`参照資産` の `保留` 5 行。後日）**: D1 REST（`CLOUDFLARE_API_TOKEN` D1 Read ＋ `CLOUDFLARE_ACCOUNT_ID` ＋ `D1_DATABASE_ID`）。SELECT のみ、列名を明示、personal-only 列と `yutai_benefits.description` を選ばない。R2 直読は不要。
- 応答形が変わったら `参照資産.提供データ` と `分析観点.スライス` を直す（スキル・プロンプトは変えない）。

---

## 10. データ読み込みの原則（観点単位・全表読み禁止。automation-spec §1）

前提: **データ全体をコンテキストに載せない。** 正本は `guardrails.md` §8。

| 原則 | 具体 |
| --- | --- |
| 読む順 | ① タスク行 → ② 専属（必要列）→ ③ 目的ルール（共通節）→ ④ 観点解決（有効・目的一致・共通または本人、順序昇順）→ 観点ごとに ⑤ 観点ルール＋参照資産 → ⑥ 事実台帳（最新 30 行）・前回タスク統合節・過去判断 20 行 → ⑦ 切片 |
| 観点単位 | `分析観点` 1 行 = 1 問い。`参照資産` の `パス・URL` に `スライス` の `クエリ=` を当て、`項目=`（≤12 列）・`件数=`（`取得上限` 既定 30・最大 100）・`期間=`・`節=` に **シェル（`curl`＋`jq`）で切ってから** 読む |
| 要約して捨てる | 1 観点の出力は 要約 ≤600 字・寄与 1 語・根拠 3 行・確認不能。本文に `## 観点: X` として **追記** したら、生データと一時ファイルを消し、以後参照しない。統合は本文の観点の節だけを読む（再取得しない） |
| 途中で止まる | `重` 1／`軽` 8 ／タスク に達したら `状態=実行中`＋`完了観点` のまま終え、次のラン（随時実行・翌朝）で再開。本文先頭の `作成中（k/m 観点）` が進捗 |
| 全表読みの禁止 | `limit` なしの API 呼び出し・全銘柄ループ・全ページ送り・`SELECT *`・`LIMIT` なし SQL・DB の総なめ・R2/D1 ダンプ・PDF/HTML 全文読み — すべて禁止。DB クエリはフィルタ（状態・対象日・利用者）＋`limit`、ページは `fetch` 1 件ずつ |
| 上限に当たったら | HTTP 5xx・タイムアウト・応答形不一致 → `不足` にせず、その観点を `確認不能` にして次へ。対象コードの系列または IR が 404 / 空 → `データ不足`＋`DATA_MISSING`（スキル §0.1）。応答形の不一致は実行サマリーで `参照資産.提供データ`／`分析観点.スライス` の修正を提案（自動化は変えない） |

---

## 11. ガードレール（AI が絶対にしないこと）と、どこで強制するか（automation-spec §7）

| ガードレール | 強制する場所 |
| --- | --- |
| `判断.最終判断`・`判断メモ` を書かない（骨格だけ作る） | プロンプト・スキル・夕振り返りの検査（`最終更新者` がインテグレーションなら見落としに記録） |
| `ルール.状態` を `発効`・`棄却` にしない。現行本文を書き換えない（草案は新行。同系旧版の自動失効だけ例外） | スキル §3（朝）・§6（夕）・自己検査。人が草案を読んで発効 |
| `分析観点`・`参照資産` を書かない。`専属エキスパート` は `直近の学び` と `NO_EXPERT` 時の `設定中` 行だけ | プロンプト・スキル |
| 禁止語（`買う` `買い` `買い推奨` `今すぐ` `必ず` `絶対` `爆益` `急騰確実`）を書かない。買わない理由 3 つを推論より先に | スキルの統合テンプレ・自己検査・夕の検査 |
| personal-only（Yahoo / JPX / 日証金 由来）の値を書かない。みんかぶ掲載原文は読まない・書かない。業種は EDINET 33 業種だけ | `reference-data.md` §1・スキル・夕の検査（数値パターン走査） |
| 出典 URL と基準日のない数値を書かない。取れなければ `確認不能`。レポート済の数字を書き換えない | スキル・自己検査 |
| データ全体を読まない（観点単位・スライス・上限・全表読み禁止） | `guardrails.md` §8・スキルの観点ループ・実行サマリーの観点別取得件数 |
| 注文・発注しない。リポジトリを変更しない。PR を作らない。Slack へ出さない。Memories に頼らない。シークレット値を出力しない | ツール設定（Notion MCP のみ／PR OFF／Memories OFF／Slack OFF）・Runtime Secret・プロンプト |
| 質問しない（無人）。`確認不能`／`不足` で止める。不足コードを `実行メモ` に残す | スキル §2.2 |
| 存在確認だけの分析をしない（`hasStructuredData` / ping / IR 先頭 3 件）。系列と IR 表題全件。不利語は推論より先。見ない領域は IR も見る。空なら `データ不足` | 朝スキル §0.1・自己検査・夕の検査 |
| 1 ランの上限、行ロック（`実行中`＋実行ID、60 分無進捗で引き継ぎ）、冪等（複製・連鎖・判断行の二重防止） | スキル §4・§5 |

---

## 12. テスト（automation-spec §10 の受け入れテストに沿う）

### 12.1 手作業前（今できる。§2.5-1 のコネクトだけ済ませてから）

1. Automation ① を Save（Activate はしなくてよい）→ **Test run / Run now**。
2. 期待: 8DB が名前で解決され（実行サマリー「解決: 8DB 名前一致 ／ 状態名: グループ代替」）、ルール整理・準備が動き、実行待ちが無ければ「実行待ち 0 行」。発効ルールが無い間に `目的` だけの行を置くと **`RULE_UNRESOLVED`** で止まる（`不足` 選択肢が無ければ `未着手` のまま `実行メモ` に `不足:RULE_UNRESOLVED`）。これは §2.5-8 前の正常な挙動。
3. 失敗するなら: インテグレーションのコネクト（§2.5-1）、MCP 認可（cursor.com/agents → MCP → Notion）、Repository が `kabulab` になっているか、プロンプトがスキルのパスを指しているか。

### 12.2 手作業後（正常系。§2.5 の 1〜3・8・9 が済んでいること）

| # | シナリオ | 期待 |
| --- | --- | --- |
| 1 | `日次タスク` に `目的=スクリーニング` だけの行 → ① Test run | 観点の節（受注トレンド／海外売上比率／制約と既判断 …）＋`## 統合`、一覧 ≤ ウォッチ上限、一覧分の `判断` 行（`AIの結論=通過`、`最終判断` 空）、`状態=レポート済`、`タスク名` が `YYYY-MM-DD スクリーニング` |
| 2 | `目的=企業分析`、`対象銘柄` 1 | 観点の節（一次情報は `重` で次ランに回ってよい → `実行中`＋`完了観点`）→ 再実行で統合。買わない理由 3 つが推論より先。判断行 1 |
| 3 | `目的=投資判断（売買計画）`、`対象銘柄` 1 | 価格条件・需給が 成立／未成立 で書かれ **値が無い**。サイズが金額。判断行 1、`AIの結論` が 4 語のどれか |
| 4 | 制約4項目が空の専属 | `不足`、`実行メモ` に `CONSTRAINT_EMPTY:<列名>`。埋めたら次ランで `未着手` → 実行 |
| 5 | `繰り返し=毎営業日` のスクリーニング | 翌営業日に複製、`変化=なし` なら判断行が増えない |
| 6 | 判断行に `要分析` を人が選ぶ | 翌朝 企業分析タスクが起票され、判断の `次タスク` が埋まる。二重起票なし |
| 7 | ② Test run | `判断日` が刻まれ、振り返り行に 外した観点 と 学び。`ルール対応` が変更ありなら草案行（`状態=草案`） |
| 8 | 草案を人が `発効` | 翌朝 旧版が `失効`、新タスクの `適用ルール` が新版。過去の判断の `適用ルール` は不変 |
| 9 | `参照資産` の URL を壊す（5xx・タイムアウト） | 当該観点が `確認不能`、タスクは `レポート済` まで進む |
| 9b | 対象コードの trend/IR が 404 または `points[]` / `disclosures[]` 空 | 本文に `データ不足`、`不足:DATA_MISSING`。滑らかな統合なし |
| 10 | `重` 観点を含むタスク | 1 ランで `重` 1 つまで。`実行中`＋`完了観点` で止まり、次ランで再開・完成 |
| 11 | 2 人目、`利用者` 空 | `作成者` で専属が解決。他人のルール・観点が適用されない |

共通の確認: 本文・`AIの一言`・事実台帳に禁止語と personal-only の数値が無い。数字に出典 URL＋基準日、または `確認不能`。実行サマリーに観点ごとの取得件数（すべて `取得上限` 以内）。

### 12.3 Webhook（§6 を設定した場合）

```bash
# 値を貼らずに環境変数から。Notion 側設定の前に疎通だけ確認
curl -sS -X POST "$CURSOR_AUTOMATION_WEBHOOK_URL" \
  -H "Authorization: Bearer $CURSOR_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"source":"manual-test"}'
```

Runs に新しい実行が出れば疎通 OK。行を特定できないペイロードなのでポーリング扱い（実行待ち 5 行まで）で動く。

---

## 13. 運用

- **実行履歴**: cursor.com/automations → 各 Automation → Runs。実行サマリーが会話の末尾に出る。失敗時は Cloud Agent の run を開いて MCP 認証エラー（`mcp_auth_error`）や `setup_failed` を見る。
- **費用**: Cloud Agent の API 従量課金。実行待ち 0 行の空実行は短い。Cloud Agents の利用上限（spend limit）を設定する。1 実行の上限はスキルの件数上限で抑える。
- **同時実行**: プラン依存（Pro は 8）。自動化ごとに同時 1 インスタンスの前提なので、同じ Automation の cron を重ねない（06:00 と 07:30 のように離す）。
- **失敗時**: `実行中` のまま 60 分進捗が無い行は次のランが引き継ぐ（`実行メモ` に `引き継ぎ 実行ID`）。人が `状態` を戻す必要はない。`不足` は列を直せば次ランで `未着手` に戻る。
- **トークン**: `NOTION_TOKEN` を更新したら Secrets を更新（新しい実行から反映）。Webhook API キーは Team Owned 昇格時に再生成。
- **Team Owned へ昇格**: 実行主体がチームのサービスアカウントに変わる。Notion MCP の OAuth をそのアカウントで再設定し、Secrets をチーム/環境スコープに置く。
- **Memories は OFF のまま**: 正本は Notion。実行間の記憶が判断を汚染しないようにする。
- **観点・参照資産の見直し**: 実行サマリーの「修正提案」が続く観点は、運営が Notion の `分析観点`（`スライス`・`取得上限`）や `参照資産`（`提供データ`）を直す。自動化は定義を変えない。
- **プロンプトの再貼り付け**: スキルの品質ゲートを変えたあとは、ダッシュボードの 3 Automation に `docs/ai-advisor/automations/*.md` の「プロンプト（このまま貼る）」を貼り直す。Automation は `main` のスキルを読むが、ダッシュボード側の要約が古いと存在確認分析が残る。
- **祝日リスト**: 年 1 回、`.cursor/skills/ai-advisor-morning-report/references/jp-holidays.md` を内閣府の翌年分で更新する。

---

## 14. 配線の記録と残り

- [x] `docs/ai-advisor/notion-schema.md` §1 の `database_id` / `data_source_id`（8DB）— `internal/notion-ids.md` から転記（2026-09-15）
- [x] 同 §2 の保存ビュー URL（`自動化_実行待ち` `自動化_有効観点` `追跡中` `判断待ち（自分）` ほか）
- [x] 同 §4 のプロパティ名を全 8 データソースの `notion-fetch` と突き合わせ — 差分なし（選択肢名の差は `日次タスク.状態` のみ → §2.5-2）
- [x] 引き渡し値（`参照資産` 有効 12／保留 5、共通観点 15／13、専属 1 行）を本書 §2・§3 に反映。インテグレーション名は運営がコネクト時に決める
- [ ] **§2.5 の手作業**（Notion 側。特に 1・2・3・8・9）
- [ ] §12.1 → §12.2 のテストを通す
- [ ] `notion-schema.md` §3.1 の「現状」列を消して `状態: 確定` に
- [ ] 3 Automation を Activate

---

## 15. 参考

- Cursor Automations: https://cursor.com/docs/cloud-agent/automations ／ ヘルプ: https://cursor.com/help/ai-features/automations
- Cloud Agent 設定（Secrets・AGENTS.md）: https://cursor.com/docs/cloud-agent/setup ／ Secrets & Network: https://cursor.com/docs/cloud-agent/security-network
- Cloud Agent の MCP: https://cursor.com/docs/cloud-agent/capabilities#mcp-tools
- Skills（`.cursor/skills`）: https://cursor.com/docs/context/skills ／ Rules・AGENTS.md: https://cursor.com/docs/context/rules
- Notion「Send webhook」: https://www.notion.com/help/webhook-actions
- kabulab 公開 API のライセンス境界: https://github.com/satoki252595/kabulab_tool_cloudflare/blob/main/docs/HANDOFF-2026-09.md
- 仕様（Project store）: `internal/automation-spec.md`、`internal/schema-spec.md`、`internal/kabulab-cf-inventory.md`（GitHub 版 `docs/ai-advisor/plan-and-design.md` が入ればそれが正本）

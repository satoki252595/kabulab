# kabulab — Agent instructions

このリポジトリは番号付きの独立したプロジェクト群（`0001_…` 〜 `0017_…`）と、Cursor Automations 定義から成る。Automations は **2 系統**あり、混ぜない。

1. **旧**: `docs/ai-advisor/` ＋ `.cursor/skills/ai-advisor-*` — 自己成長するAI投資家アドバイザー（親ページ「AI専属アナリスト」、**8DB**）
2. **新**: `docs/ai-expert/` ＋ `.cursor/skills/ai-expert-*` ＋ `0017_ai-expert-web/` — 自己成長するあなただけのAI投資エージェント（親ページ「AI投資エージェント」、**5DB** ＋ CF 私有円帯）

## Cursor Cloud specific instructions

### 旧: AI投資家アドバイザー（8DB・親「AI専属アナリスト」）

- Automation（朝レポート / 夕振り返り / 随時実行）として起動され、ダッシュボードのプロンプトが `.cursor/skills/ai-advisor-*/SKILL.md` を指す場合は、そのスキルを最初に全文読み、その手順どおりに動く。あわせて `docs/ai-advisor/guardrails.md`（書いてよい列・禁止語・ライセンス境界・データ読み込みの原則）、`docs/ai-advisor/notion-schema.md`（8DB の名前・プロパティ・状態値・保存ビュー・文脈予算）、`docs/ai-advisor/reference-data.md`（参照資産・観点ごとの取得形）を読む。仕様の正本は Project の `internal/automation-spec.md` / `internal/schema-spec.md`（GitHub 版 `docs/ai-advisor/plan-and-design.md` が入ればそれ）。
- 投資助言をしない。人の最終判断を代行しない。`判断.最終判断`・`判断メモ` を書かない。`ルール.状態` を `発効`・`棄却` にしない。`分析観点`・`参照資産` を書かない。
- **品質ゲート**（`.cursor/skills/ai-advisor-morning-report/SKILL.md` §0.1）: `hasStructuredData` / エンドポイント ping / IR 表題の先頭 3 件だけでは分析にしない。対象銘柄では `points[]`（または同等の時系列）と IR 表題・タグの全件を読む。不利語は推論より先。見ない領域は IR の監理/整理/上場廃止も宇宙外。系列または IR が無ければ `データ不足` と書いて `不足` にする。`買う` / `今すぐ買う` を書かない。
- **読み手向け**（同スキル §0.2）: 本文の先頭は口語の `## 今日の結論`（2〜4文）。監査用語（`宇宙外` `DATA_MISSING` `hasStructuredData` `points[]` `bars[]`）を先頭に置かない。観点は「分かったこと→だから」。スクリーニングの落とす理由は「上場廃止・整理銘柄」。`要約` は口語 1 文。
- これらの Automation は **Notion 以外に書かない**: リポジトリのファイルを変更しない、PR を作らない、Slack 等へ投稿しない。`NOTION_TOKEN` などシークレットの値を出力しない。
- **データ全体をコンテキストに載せない**。`分析観点` を 1 つずつ、宣言されたスライス（参照資産の URL ＋ `項目=`・`件数=`・`期間=`・`節=`）だけをシェル（`curl`＋`jq`）で切ってから読み、要約を Notion に書いたら生データを捨てて次へ進む。`limit` なしの取得・全表読み・全ページ送りをしない。
- personal-only（Yahoo / JPX / 日証金 由来）の値と、みんかぶ由来の掲載原文を Notion に書かない（`docs/ai-advisor/reference-data.md` §1）。
- 既存プロジェクト（`0001_…` 〜 `0016_…`）のデータやノートは、AI投資家アドバイザーの入力にも relation 先にもしない。

### 新: AI投資エージェント（5DB・親「AI投資エージェント」）

- Automation のプロンプトが `.cursor/skills/ai-expert-*/SKILL.md` を指す場合（朝レポート / 夕振り返り / 随時実行）は、そのスキルを最初に全文読み、その手順どおりに動く。あわせて `docs/ai-expert/guardrails.md`、`docs/ai-expert/notion-schema.md`、`docs/ai-expert/reference-data.md` を読む。モデルは **Grok 4.6**。旧 8DB と `ai-advisor-*` には読み書きしない。親ページ https://app.notion.com/p/3ddd74ff84cd81789abbcf86708626c0 。**状態列は select**（`status` / `status_is` は使わない）。`判断ID` は title。
- 投資助言をしない。人の最終判断を代行しない。発注しない。目的は **スクリーニング** と **売買判断** のみ（日本株）。`判断.最終判断`・`判断メモ` を書かない。`ルール.状態` を `発効`・`棄却` にしない。
- **共有面は Notion（5 DB）だけ**。円（エントリー／損切り／利確／サイズの代入結果／結果％／TOPIX対比）は CF 私有 API（`AI_EXPERT_YEN_API_URL` / `AI_EXPERT_YEN_STORE_SECRET`）に 1 判断 1 回だけ書く。リポジトリ変更・PR・Slack・公開 JSON の更新・発注は禁止。シークレット値を出力しない。
- **データ全体をコンテキストに載せない**。固定切片を 1 つずつ、宣言されたスライスだけをシェル（`curl`＋`jq`）または接続済み jss-api MCP で切ってから読み、要約を Notion に書いたら生データを捨てる。経路: jss-api MCP → 公開 Worker JSON → 地合い Web。Mac のローカル checkout は使わない。
- personal-only の値とみんかぶ原文を Notion に書かない。業種は EDINET 33 業種だけ。`market` を書かない。
- `0001_…` 〜 `0016_…` および旧 8DB は入力にも relation 先にもしない。

## Repository notes

- 旧 Automations のセットアップ: `docs/ai-advisor/automations-setup.md`。ダッシュボードに貼るプロンプトは `docs/ai-advisor/automations/*.md`。
- 新 Automations のセットアップ: `docs/ai-expert/automations-setup.md`。プロンプトは `docs/ai-expert/automations/*.md`。会員向け Web は `0017_ai-expert-web/`（既存 kabulab-cf データ Worker とは別。公開 JSON はデータ面として再利用）。
- 上記以外のディレクトリは各プロジェクト固有の README に従う。

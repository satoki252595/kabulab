# kabulab — Agent instructions

このリポジトリは番号付きの独立したプロジェクト群（`0001_…` 〜 `0016_…`）と、`docs/ai-advisor/` ＋ `.cursor/skills/ai-advisor-*` に置いた **自己成長するAI投資家アドバイザー（Notion 駆動の日次ループ）の Cursor Automations 定義** から成る。

## Cursor Cloud specific instructions

- Automation（朝レポート / 夕振り返り / 随時実行）として起動された場合は、ダッシュボードのプロンプトが指す `.cursor/skills/ai-advisor-*/SKILL.md` を最初に全文読み、その手順どおりに動く。あわせて `docs/ai-advisor/guardrails.md`（書いてよい列・禁止語・ライセンス境界・データ読み込みの原則）、`docs/ai-advisor/notion-schema.md`（8DB の名前・プロパティ・状態値・保存ビュー・文脈予算）、`docs/ai-advisor/reference-data.md`（参照資産・観点ごとの取得形）を読む。仕様の正本は Project の `internal/automation-spec.md` / `internal/schema-spec.md`（GitHub 版 `docs/ai-advisor/plan-and-design.md` が入ればそれ）。
- 投資助言をしない。人の最終判断を代行しない。`判断.最終判断`・`判断メモ` を書かない。`ルール.状態` を `発効`・`棄却` にしない。`分析観点`・`参照資産` を書かない。
- **品質ゲート**（`.cursor/skills/ai-advisor-morning-report/SKILL.md` §0.1）: `hasStructuredData` / エンドポイント ping / IR 表題の先頭 3 件だけでは分析にしない。対象銘柄では `points[]`（または同等の時系列）と IR 表題・タグの全件を読む。不利語は推論より先。見ない領域は IR の監理/整理/上場廃止も宇宙外。系列または IR が無ければ `データ不足` と書いて `不足` にする。`買う` / `今すぐ買う` を書かない。
- これらの Automation は **Notion 以外に書かない**: リポジトリのファイルを変更しない、PR を作らない、Slack 等へ投稿しない。`NOTION_TOKEN` などシークレットの値を出力しない。
- **データ全体をコンテキストに載せない**。`分析観点` を 1 つずつ、宣言されたスライス（参照資産の URL ＋ `項目=`・`件数=`・`期間=`・`節=`）だけをシェル（`curl`＋`jq`）で切ってから読み、要約を Notion に書いたら生データを捨てて次へ進む。`limit` なしの取得・全表読み・全ページ送りをしない。
- personal-only（Yahoo / JPX / 日証金 由来）の値と、みんかぶ由来の掲載原文を Notion に書かない（`docs/ai-advisor/reference-data.md` §1）。
- 既存プロジェクト（`0001_…` 〜 `0016_…`）のデータやノートは、AI投資家アドバイザーの入力にも relation 先にもしない。

## Repository notes

- `docs/ai-advisor/automations-setup.md` が Automations のセットアップ手順（日本語）。ダッシュボードに貼るプロンプトは `docs/ai-advisor/automations/*.md`。
- 上記以外のディレクトリは各プロジェクト固有の README に従う。

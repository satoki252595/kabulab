# kabulab — Agent instructions

このリポジトリは番号付きの独立したプロジェクト群（`0001_…` 〜 `0016_…`）と、`docs/ai-advisor/` ＋ `.cursor/skills/ai-advisor-*` に置いた **AI専属アナリスト（Notion 駆動の日次ループ）の Cursor Automations 定義** から成る。

## Cursor Cloud specific instructions

- Automation（日次ループ / 日次振り返り / オンボーディング確認）として起動された場合は、ダッシュボードのプロンプトが指す `.cursor/skills/ai-advisor-*/SKILL.md` を最初に全文読み、その手順どおりに動く。あわせて `docs/ai-advisor/guardrails.md`（絶対ルール）、`docs/ai-advisor/notion-schema.md`（DB ID・ビュー・プロパティ名・上限）、`docs/ai-advisor/reference-data.md`（参照データ源・出典タグ・分析観点）を読む。
- これらの Automation は **Notion 以外に書かない**: リポジトリのファイルを変更しない、PR を作らない、Slack 等へ投稿しない。`NOTION_TOKEN` などシークレットの値を出力しない。
- **データ全体をコンテキストに載せない**。分析観点を 1 つずつ、宣言されたスライス（エンドポイント / フィールド / 銘柄 / 期間 / 件数上限）だけ取り、要約を Notion に書いてから次へ進む。`limit` なしの取得・全表読み・全ページ送りをしない。
- personal-only（Yahoo / JPX / 日証金 由来）の値と、みんかぶ由来の掲載文を Notion に書かない（`docs/ai-advisor/reference-data.md` §1）。
- 既存プロジェクト（`0001_…` 〜 `0016_…`）のデータやノートは、AI専属アナリストの入力にも relation 先にもしない。

## Repository notes

- `docs/ai-advisor/automations-setup.md` が Automations のセットアップ手順（日本語）。ダッシュボードに貼るプロンプトは `docs/ai-advisor/automations/*.md`。
- 上記以外のディレクトリは各プロジェクト固有の README に従う。

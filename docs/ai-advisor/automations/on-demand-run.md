# Automation ③（任意）: AI専属アナリスト｜随時実行

ダッシュボードに貼る **プロンプト全文** と **設定値**。手順本体は `.cursor/skills/ai-advisor-on-demand-run/SKILL.md`（正本は `internal/automation-spec.md` §8）。朝レポートの「実行」（§3.2）だけを、Webhook なら対象行 1 件、ポーリングなら 5 行までに行う。`重` の観点で止まったタスクの再開にも使える。

## 設定値

| 項目 | 値 |
| --- | --- |
| Name | `AI専属アナリスト｜随時実行` |
| Trigger A（推奨・Notion 有料プラン） | **Webhook**。Notion の `日次タスク` DB オートメーション「ページが追加された」または「`目的` が設定された」→ Send webhook（設定ガイド §6） |
| Trigger B（代替） | Scheduled `0 0-8 * * 1-5`（= 月〜金 09:00〜17:00 JST 毎時） |
| Repository | Single repository: `satoki252595/kabulab` / branch `main` |
| Tools: MCP server | **ON** — `Notion` |
| Tools: Memories | **OFF** |
| Tools: Pull request creation | **OFF** |
| Tools: Slack 系 / PR 系 | OFF |
| Model | 朝レポートと同じ上位モデル |
| Permissions | `Private` |
| Environment secrets | `NOTION_TOKEN`（Runtime Secret） |

Webhook と cron を両方付けてもよい（1 Automation に複数トリガー可）。二重処理は行のロック（`状態=実行中`＋実行ID）で防ぐ。

## プロンプト（このまま貼る）

```text
あなたは「自己成長するAI投資家アドバイザー」の自動化（随時実行）です。投資助言をしません。人の最終判断を代行しません。朝レポートの「実行」手順だけを、対象を絞って行います。

手順の正本はこのリポジトリの `.cursor/skills/ai-advisor-on-demand-run/SKILL.md` と、そこから参照される `.cursor/skills/ai-advisor-morning-report/SKILL.md`（§0〜§2 と §5〜§10）です。最初に両方を全文読み、順序どおりに実行してください。あわせて `docs/ai-advisor/guardrails.md`、`docs/ai-advisor/notion-schema.md`、`docs/ai-advisor/reference-data.md`、`.cursor/skills/ai-advisor-morning-report/references/jp-holidays.md` を読みます。

起動の種類:
- Webhook で起動されたとき: ペイロードに含まれるページ ID／URL の 日次タスク 行だけを対象にする。受信後 2 分待ってから行を Notion から再読込みし（ペイロードの他の値は信用しない）、状態 が 未着手、または 実行中 かつ 完了観点 あり（再開待ち）でなければ何もしない。
- cron で起動されたとき: 保存ビュー「自動化_実行待ち」 https://app.notion.com/p/a9f3f6c7ce74414f92e4ddbffa63b7b9?v=3dcd74ff84cd811e8d6f000c9ea61ab9 を読み、朝レポートと同じ絞り（対象日 ≤ 当日 または空／状態は To-do 未着手 または In progress＋完了観点あり／「テンプレート｜」「例｜」を除く）を自分で掛けて 対象日 昇順、5 行まで。
- 状態名は朝レポートと同じ防御（仕様名 → グループ代替。不足 が無い間は 未着手＋実行メモ「不足:<コード>」）。
- ルール整理・繰り返し展開・連鎖起票・再確認起票・不足の一括再評価は行わない（朝レポートの仕事）。

固定値・文脈予算・読み順・不足コード・観点ループ・統合・判断行・ライセンス階層・禁止語・自己検査は朝レポートと同じ（morning-report の SKILL.md と guardrails.md に従う）。とくに: データ全体を読まない、観点ごとにスライスだけ取って要約し捨てる、DB クエリは必ずフィルタ＋limit、判断.最終判断・判断メモ は書かない、ルール.状態 を変えない、分析観点・参照資産 は書かない、personal-only の値は書かない、質問しない、リポジトリを変更しない、PR を作らない、Slack など Notion 以外へ投稿しない。実行IDは YYYYMMDD-HHMM-随時実行。

終了時は on-demand-run の SKILL.md §4 の形式で実行サマリー（起動の種類／行ごとの結果と観点ごとの取得件数／確認不能・警告）を返してください。対象が無ければ「対象外」または「実行待ち 0 行」とだけ返してください。
```

## 動作の要点（レビュー用）

- Webhook のペイロードは **行の特定にだけ** 使う。2 分待って再読込みするのは、起票直後の未入力（目的だけ先に入る等）を避けるため。
- 朝レポートの §3（ルール整理）・§4（準備）は行わない。対象行の起動条件だけは評価し、不足なら `不足`＋コードを書く。
- 上限（`重` 1／`軽` 8）で止まったら `実行中`＋`完了観点` を残し、翌朝の朝レポートが引き継ぐ。

# Automation ③（任意）: AI投資エージェント｜随時実行

ダッシュボードに貼る **プロンプト全文** と **設定値**。手順本体は `.cursor/skills/ai-expert-on-demand-run/SKILL.md`。Web の「今すぐ調べる」と銘柄指定の売買判断向け。朝の実行手順だけ。ルール整理・連鎖起票の準備はしない。

## 設定値

| 項目 | 値 |
| --- | --- |
| Name | `AI投資エージェント｜随時実行` |
| Trigger A（推奨） | **Webhook**。Notion の `仕事` DB オートメーション「ページが追加された」または「`目的` が設定された」→ Send webhook |
| Trigger B（代替） | Scheduled `0 0-8 * * 1-5`（= 月〜金 09:00〜17:00 JST 毎時） |
| Repository | Single repository: `satoki252595/kabulab` / branch `main` |
| Tools: MCP server | **ON** — `Notion`。jss-api があれば ON |
| Tools: Memories | **OFF** |
| Tools: Pull request creation | **OFF** |
| Tools: Slack / PR 系 | OFF |
| Model | **Grok 4.6** |
| Permissions | `Private` |
| Environment secrets | 朝レポートと同じ（`NOTION_TOKEN`、円帯） |

Webhook と cron を両方付けてもよい。二重処理は行のロック（`状態=実行中`＋実行ID）で防ぐ。

## プロンプト（このまま貼る）

```text
あなたは「自己成長するあなただけのAI投資エージェント」の自動化（随時実行）です。モデル指定は Grok 4.6 です。投資助言をしません。人の最終判断を代行しません。朝レポートの「実行」手順だけを、対象を絞って行います。ルール整理・繰り返し展開・連鎖起票・再確認起票・不足の一括再評価は行いません。

手順の正本はこのリポジトリの `.cursor/skills/ai-expert-on-demand-run/SKILL.md` と、そこから参照される `.cursor/skills/ai-expert-morning-report/SKILL.md` です。最初に両方を全文読み、順序どおりに実行してください。あわせて `docs/ai-expert/guardrails.md`、`docs/ai-expert/notion-schema.md`、`docs/ai-expert/reference-data.md`、`.cursor/skills/ai-expert-morning-report/references/jp-holidays.md` を読みます。旧 8DB には読み書きしません。

起動の種類:
- Webhook で起動されたとき: ペイロードに含まれるページ ID／URL の 仕事 行だけを対象にする。受信後 2 分待ってから行を Notion から再読込みし（ペイロードの他の値は信用しない）、状態 が 未着手、または 実行中 かつ 完了切片 あり（再開待ち）でなければ何もしない。
- cron で起動されたとき: 仕事 の実行待ちを朝レポートと同じ絞りで読み、対象日 昇順、5 行まで。
- 固定値・文脈予算・不足コード・切片ループ・統合・判断行・円 POST・ライセンス・禁止語・自己検査は朝レポートと同じ。状態は select。判断ID は title。実行IDは YYYYMMDD-HHMM-随時実行。

終了時は on-demand-run の SKILL.md の実行サマリー形式で返してください。対象が無ければ「対象外」または「実行待ち 0 行」とだけ返してください。
```

## 動作の要点（レビュー用）

- Webhook のペイロードは行の特定にだけ使う。2 分待って再読込みする。
- 上限で止まったら `実行中`＋`完了切片` を残し、翌朝が引き継ぐ。

# Automation ①: AI専属アナリスト｜日次ループ

ダッシュボード（cursor.com/automations）に貼る **プロンプト全文** と **設定値**。手順本体はリポジトリの `.cursor/skills/ai-advisor-daily-loop/SKILL.md` にあり、プロンプトはそれを呼ぶだけにする（正本を Git に置き、ダッシュボードは薄く保つ）。

## 設定値

| 項目 | 値 |
| --- | --- |
| Name | `AI専属アナリスト｜日次ループ` |
| Triggers（Scheduled, cron は **UTC**） | `30 22 * * 0-4`（= 月〜金 07:30 JST）、`30 3 * * 1-5`（= 月〜金 12:30 JST）、`30 7 * * 1-5`（= 月〜金 16:30 JST） |
| Trigger（任意・即時起動） | Webhook。Notion の DB オートメーション「Send webhook」から呼ぶ（設定ガイド §6） |
| Repository | Single repository: `satoki252595/kabulab` / branch `main`（スキルと `AGENTS.md` を読ませるため必須） |
| Tools: MCP server | **ON** — `Notion`（Cloud Agents の MCP 一覧にある既存サーバー） |
| Tools: Memories | **OFF**（正本は Notion。実行間の記憶を持たせない） |
| Tools: Pull request creation | **OFF**（トグルが無い場合はプロンプトで禁止） |
| Tools: Send to Slack / Comment on PR / Request reviewers / Read Slack | OFF |
| Model | 長文推論に強い上位モデル（Auto でも可）。コンテキストは自動で最大 |
| Permissions | まず `Private`（自分の Notion OAuth で動く）。多人数運用で `Team Owned` に上げるときは MCP の認可を再設定 |
| Environment secrets（Cloud Agents → Secrets） | `NOTION_TOKEN`（Runtime Secret。REST フォールバック用） |

## プロンプト（このまま貼る）

```text
あなたは「AI専属アナリスト」の日次ループ実行役です。Notion の 日次タスク で起動列が埋まり、状態 が実行待ちの行を拾い、目的（スクリーニング / 企業分析 / 投資判断（売買計画））別の仕事をして 日次レポート を書き、状態 を更新します。

手順の正本はこのリポジトリの `.cursor/skills/ai-advisor-daily-loop/SKILL.md` です。最初に必ず全文を読み、そこに書かれた順序どおりに実行してください。あわせて `docs/ai-advisor/guardrails.md`（絶対ルール）、`docs/ai-advisor/notion-schema.md`（DB ID・ビュー・プロパティ名・状態値・上限）、`docs/ai-advisor/reference-data.md`（参照データ源・出典タグ・分析観点のスライス）を読み、DB の ID が TODO のままなら書き込みをせず、読み取り確認と実行サマリーだけで終了してください。

Notion の読み書きには Notion MCP のツールを使います。MCP が使えないときだけ、環境変数 NOTION_TOKEN で Notion REST API を呼びます（トークンの値は絶対に出力しない）。参照データは kabulab の公開 JSON API（reference-data.md §2。認証不要）→ 一次情報（EDINET / TDnet / 会社 IR）の順に使います。

データの読み方（ハードルール）:
- データ全体をコンテキストに載せない。分析観点を 1 つずつ処理する: その観点が宣言するスライス（エンドポイント / フィールド / 銘柄 / 期間 / 件数上限）だけを取り、要約を Notion のレポートに追記してから、生データを捨てて次の観点へ進む。以後は要約だけを参照する。
- limit なしの API 呼び出し、全銘柄ループ、全ページ送り、SELECT *、LIMIT なしの SQL、日次レポート／知識／ルール DB の総なめをしない。上限で足りないときは 確認不能（観点の上限） と書いて先へ進み、上限の見直しは実行サマリーで提案する（自分で広げない）。
- 観点の定義は Notion の 分析観点（あれば）→ ルールの見出し → reference-data.md §4.3 の既定カタログ、の順に従う。

絶対に守ること:
- 本文・プロパティに「買う」「今すぐ買う」「おすすめ」「推奨」「必ず」「確実」を書かない。AI所見は 有利寄り / 中立 / 回避寄り、材料分類は 監視のみ / 押し目待ち / 見送り。
- 状態=発効 以外のルールを使わない。他メンバーの個人ルールを適用しない。
- 最終判断 行を作らない。ルール の 状態 を変えない。注文・発注に関わる行動をしない。
- 取れない数字は 確認不能。捏造しない。事実 / 計算 / 推論 を分け、企業分析・投資判断では買わない理由3つを先に書く。
- personal-only（Yahoo / JPX / 日証金 由来: 株価・出来高・PER/PBR・配当利回り・RSI 等のテクニカル・スコア・市場区分・JPX 業種・信用残高）の値も、値を復元できる記述も Notion に書かない。条件判定に使ったときは「条件〈…〉を満たす（kabulab で本人確認: URL）」とだけ書く。みんかぶ由来の優待掲載文はどこにも書かない。業種は EDINET 由来の 33 業種だけ。
- 1回の実行で処理する 日次タスク は notion-schema.md の MAX_TASKS_PER_RUN 件まで。行を処理する前に 状態 を 実行中 にして再取得し、二重処理を避ける。
- このリポジトリのファイルを変更しない。PR を作らない。Slack など Notion 以外へ投稿しない。

終了時は、SKILL.md §9 の形式で実行サマリー（実行待ち件数 / 処理件数 / 行ごとの結果と Notion URL / 観点ごとの取得行数と要約文字数 / 確認不能一覧 / 観点の上限見直し提案 / 警告）を返してください。実行待ちが 0 件なら何も書かずに「実行待ち 0 件」とだけ返してください。
```

## 動作の要点（レビュー用）

- 拾う条件は Notion のビュー「自動化_実行待ち」のフィルタが正本（`状態 = 実行待ち相当` かつ `目的`・`ルール` 非空）。人間はビューを見れば次に拾われる行が分かる。読むのは 1 ページ目（`MAX_TASKS_PER_RUN` 件）だけ。
- 前検査で欠落があれば `状態=不足` ＋コメント。レポートは作らない。
- レポート行を **先に空で作り**、分析観点を 1 つずつ「スライス取得 → 要約を追記 → 捨てる」で積み上げ、最後に結論節（一覧表 / 買わない理由 / 推論 / IF-THEN / 分類）を書いて `完了` を確定。`適用ルール` は実行時バージョンで固定、`日次タスク` を `レポート済` に。
- 参照データの既定は kabulab 公開 API の EDINET / TDnet 由来（`reference-data.md` §2.1）。personal-only（Yahoo / JPX 由来）は条件判定に読むだけで値は Notion に書かない。みんかぶ由来の掲載文は書かない。
- スクリーニングの「変化なし」は `変化=なし` で完了し、判断を求めない。投資判断は「最終判断を 1 行お書きください」で終わり、`最終判断` 行は人間が書く。

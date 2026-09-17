# Cursor Automations セットアップ — 自己成長するあなただけのAI投資エージェント

- 日付: 2026-09-16
- 対象: このリポジトリ（`satoki252595/kabulab`）と Notion 親ページ「AI投資エージェント」（**新 5 DB**）
- 旧製品（親「AI専属アナリスト」8DB）のセットアップは `docs/ai-advisor/automations-setup.md`。**混ぜない。** 3 本の Automation は名前を分けて別途作る
- モデル: **Grok 4.6**
- 発注・証券口座連携はしない

---

## 0. 全体像

```plain
人（Web オンボーディング）: 制約 4・ウォッチ → Notion エージェント（設定中→運用中）
人 / Web: 仕事 を未着手で起票（目的=スクリーニング｜売買判断。売買は対象コードと方向）
Automation ①「AI投資エージェント｜朝レポート」06:00 JST 月–金（Grok 4.6）
  ├─ 運用中エージェント・制約4・ルール整理（旧発効を失効）／準備（繰り返し・連鎖・再確認）
  ├─ 仕事ごと: 固定切片を 1 つずつ「取得 → 切る → 要約 → 本文に追記 → 捨てる」
  └─ 統合 → 判断 骨格（最終判断 は空）→ 円帯だけ CF 私有 API に 1 回 POST → レポート済
人: 判断 の 最終判断（残す/落とす・買う/売る/待つ/見送る）。Web のボタンでも可
Automation ②「夕振り返り」18:00 JST 月–金
  └─ 判断日 → 追跡（成立／未成立。結果％は私有面）→ 振り返り → 草案（発効は人）
Automation ③「随時実行」: Web の「今すぐ調べる」＝ Webhook 1 行、または毎時 5 行。朝の実行だけ
```

| 置き場所 | 何が入っているか |
| --- | --- |
| Cursor ダッシュボード | 3 つの **新しい** Automation（旧 8DB 用とは別名） |
| `.cursor/skills/ai-expert-{morning-report,evening-review,on-demand-run}/SKILL.md` | 手順本体 |
| `docs/ai-expert/automations/*.md` | ダッシュボードに貼るプロンプト |
| `docs/ai-expert/guardrails.md` ほか | 書いてよい列・5DB・固定切片 |
| `0017_ai-expert-web/` | Google ログイン必須の CF Worker（レポート閲覧・円は本人だけ） |
| `AGENTS.md` | Cloud Agent 向け。旧 8DB 節は残し、本製品は別節 |

---

## 1. 前提

- [ ] Cursor 有料プラン。`satoki252595/kabulab` に読み書き
- [ ] Cloud Agents Secrets: `NOTION_TOKEN`（Runtime Secret）
- [ ] 円帯用（朝レポート・夕）: `AI_EXPERT_YEN_API_URL`（Worker の origin。末尾スラッシュなし）、`AI_EXPERT_YEN_STORE_SECRET`（Worker と同じ値）。値を repo / Notion / 実行ログに書かない
- [ ] MCP: `Notion` 必須。**jss-api** を Notion と並べて接続する（未接続なら公開 JSON フォールバック）
- [x] Notion 親「AI投資エージェント」直下に 5 DB。ID / ビュー URL / **状態は select** / **判断ID は title** は `docs/ai-expert/notion-schema.md`（2026-09-16 照合）。CF Worker の `wrangler.jsonc` `vars` にも同じ database_id を入れてある
- [ ] 自動化用インテグレーションを親ページに **編集権限でコネクト**
- [ ] 共通ルールを目的ごとに `状態=発効`（スクリーニング / 売買判断。本文に円を書かない）
- [ ] 少なくとも 1 人の `エージェント` が制約4を埋めて `運用中`（Web オンボーディングでも可）
- [ ] この PR が `main` に入っている（Automation は `main` のスキルを読む）
- [ ] CF Web は `0017_ai-expert-web/README.md` のデプロイ手順（Google OAuth・D1・シークレット）。未デプロイでも Automations の Notion 面は回せる（円 POST は `YEN_STORE_FAILED`）

### 1.1 起動前の Notion 手作業

| # | 手作業 |
| --- | --- |
| 1 | 親ページへインテグレーションをコネクト |
| 2 | 状態は **select**（status 型にしない）。語彙は仕様どおり。自動化は `select_equals` |
| 3 | 保存ビュー: `自動化_実行待ち` `再開待ち` `今日のレポート`（`仕事`）、`追跡中` `判断待ち（自分）`（`判断`） |
| 4 | 共通ルール v1 を `発効`（円なしの条件文） |
| 5 | エージェントの制約4と `運用中`。`オーナー` person は運営が WebユーザーID と紐づける |

---

## 2. Automation の作り方（3 本とも同じ型）

1. cursor.com/automations → **New automation**（旧「AI専属アナリスト｜…」は触らない）
2. Name / Trigger / Repository / Prompt は各 `docs/ai-expert/automations/*.md`
3. **Repository**: `satoki252595/kabulab` / `main`
4. **Model**: **Grok 4.6**（ダッシュボードで明示。Auto にしない）
5. **Tools**: MCP `Notion` ON。jss-api があれば ON。Memories **OFF**。PR 作成 **OFF**。Slack OFF
6. **Permissions**: まず Private
7. Save → Test run → 手作業のあと Activate

---

## 3. スケジュール（cron は UTC。JST=UTC+9）

| Automation | JST | UTC cron |
| --- | --- | --- |
| 朝レポート | 月〜金 06:00 | `0 21 * * 0-4` |
| 夕振り返り | 月〜金 18:00 | `0 9 * * 1-5` |
| 随時（ポーリング） | 月〜金 09〜17 時毎時 | `0 0-8 * * 1-5` |
| 随時（Webhook） | `仕事` にページ追加 / `目的` 設定 → Send webhook | 保存後の URL + Bearer |

祝日・12/31〜1/3 はスキル内で判定（`.cursor/skills/ai-expert-morning-report/references/jp-holidays.md`）。休場日は繰り返し展開をしないが、手/Web 起票は処理する。

---

## 4. データ面

正本: `docs/ai-expert/reference-data.md`

- 切片を 1 つずつ。切ってから読む。書いたら捨てる
- 既定フォールバックは `https://kabulab-cf.satoki252595.workers.dev` の公開 JSON
- 円は `0017_ai-expert-web` の `POST /api/internal/yen` のみ
- 旧 8DB・`0001_…`〜`0016_…` は入力にも relation 先にもしない

---

## 5. テスト（受け入れの最小）

| # | シナリオ | 期待 |
| --- | --- | --- |
| 1 | 5DB がまだ無い Test run | 書き込みせず「未解決: 〈DB名〉」 |
| 2 | 発効ルール 0 でスクリーニング仕事 | `RULE_UNRESOLVED` |
| 3 | 制約4が空 | `CONSTRAINT_EMPTY:<列>` |
| 4 | スクリーニング 1 行（運用中・発効あり） | 切片の節＋統合。残した銘柄と判断行。`最終判断` 空。personal-only の値なし |
| 5 | 売買判断 1 コード | 入らない理由 3 が推論より前。IF-THEN は条件文。円は Notion に無く、円帯 API が生きていれば 1 POST |
| 6 | 人が `残す` | 翌朝 同じコードの売買判断が連鎖起票 |
| 7 | 夕 Test run | 判断日、振り返り、草案は `草案` のみ |
| 8 | Web 未ログイン | 全ページが Google へ。匿名面なし |
| 9 | 他人のレポート | 円列なし。ルール本文の円はマスク |

---

## 6. 参考

- 計画書: Project store `docs/ai-expert-plan.md`
- 旧 8DB セットアップ: `docs/ai-advisor/automations-setup.md`
- CF Web: `0017_ai-expert-web/README.md`
- Cursor Automations: https://cursor.com/docs/cloud-agent/automations

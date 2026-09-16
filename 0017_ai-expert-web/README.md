# 自己成長するあなただけのAI投資エージェント — Web

会員向け Cloudflare Worker。**既存の kabulab-cf（データ Worker）とは別アプリ**。公開 JSON はデータ面として再利用するが、UI をそのサイトの延長にしない。Mac の `/Users/satoki252595/projects/kabulab-cf` は参照もデプロイ元にもしない。

- Google OAuth **必須**（匿名なし）
- オンボーディング → Notion `エージェント`
- 今日の入力 → Notion `仕事`（`未着手`、起票元=`Web`）
- レポート一覧（他人のも読める。**円なし**）
- 他人の **発効** ルール（`ルール公開` または共通）
- 本人だけ D1 `decision_yen` の円・結果％・TOPIX対比
- 最終判断ボタンは本人のみ（AI は呼ばない）
- 発注・証券 API・ペーパートレード約定は置かない

Automations（Grok 4.6）は `.cursor/skills/ai-expert-*`。セットアップは `docs/ai-expert/automations-setup.md`。

## まだデプロイしていない場合

このディレクトリは **コードと D1 スキーマの足場**。Google OAuth クライアント、Notion トークン、D1 ID が無ければデプロイしない。下の手順を人が埋めてから `wrangler deploy` する。

## ローカル

```bash
cd 0017_ai-expert-web
npm install
cp .dev.vars.example .dev.vars   # 値は git に載せない
npx wrangler d1 migrations apply ai-expert-web --local
npm test
npx wrangler dev
```

`.dev.vars` が空のままだと `/login` は出せるが Google コールバックと Notion 書き込みは失敗する。OAuth なしの会員フロー（オンボーディング → 仕事 → レポート → 他人の円が隠れること）は **この環境では未検証**（シークレット未配布）。単体テストは `mask` / yen ACL / ルートガード / 公開 JSON の切片 URL を固定している。

## デプロイ手順（人がやる）

1. Cloudflare アカウントでこのディレクトリをデプロイ元にする（kabulab-cf リポではない）。
2. D1 を作る:

   ```bash
   npx wrangler d1 create ai-expert-web
   ```

   返った `database_id` を `wrangler.jsonc` の `d1_databases[0].database_id` に入れる（プレースホルダ UUID を置換）。

3. マイグレーション:

   ```bash
   npx wrangler d1 migrations apply ai-expert-web --remote
   ```

4. Google Cloud Console で OAuth クライアント（Web アプリケーション）。承認済みリダイレクト URI: `https://<worker-host>/auth/callback`。スコープ `openid email profile`。

5. シークレット（値をチャット・git・README に貼らない）:

   ```bash
   npx wrangler secret put GOOGLE_CLIENT_ID
   npx wrangler secret put GOOGLE_CLIENT_SECRET
   npx wrangler secret put SESSION_SECRET
   npx wrangler secret put NOTION_TOKEN
   npx wrangler secret put YEN_STORE_SECRET
   ```

6. Notion 5DB の `database_id` / `data_source_id` は **`wrangler.jsonc` の `vars` に配線済み**（親 `3ddd74ff-84cd-8178-9abb-cf86708626c0`）。状態列は **select**。判断ID は **title**。インテグレーションを親ページ「AI投資エージェント」にコネクトする。`オーナー` person は運営が初回だけ紐づける（Web は `WebユーザーID`＝Google `sub` だけ書く）。`ルール公開` は作成時に ON。

7. Cursor Automations の Secrets に `AI_EXPERT_YEN_API_URL`（Worker origin、末尾スラッシュなし）と、同じ `YEN_STORE_SECRET` を `AI_EXPERT_YEN_STORE_SECRET` として入れる。

8. `npx wrangler deploy`

9. 疎通: `GET /healthz` が `{ "ok": true }`。未ログインの `/` は `/login`。`POST /api/internal/yen` は Bearer 無しで 401。

## 円帯 API（Automations 専用）

`POST /api/internal/yen`  
`Authorization: Bearer <YEN_STORE_SECRET>`

1 判断 1 回。既存の `notion_decision_id` は 409（円は変えない）。

結果列だけ（夕）: `PATCH /api/internal/yen/:notion_decision_id/result` 同じ Bearer。`entry_yen` 等は更新しない。

## 公開範囲

| 見る人 | 見えるもの |
| --- | --- |
| 他人 | 発効ルール（公開）、レポート本文（円マスク）、分類と成立／未成立、入らない理由、他人の最終判断（閲覧のみ） |
| 本人 | 上記＋自分の `decision_yen`。最終判断の編集 |

## ライセンス

Yahoo / JPX / 日証金由来の数値を他人向け HTML に出さない。ルール本文に円が混ざっていたら表示側でマスクする。

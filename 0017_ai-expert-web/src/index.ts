import { Hono } from "hono";
import { deleteCookie, getCookie, setCookie } from "hono/cookie";
import {
  buildGoogleAuthUrl,
  cookieHeader,
  exchangeGoogleCode,
  OAUTH_COOKIE,
  parseCookies,
  randomUrlToken,
  SESSION_COOKIE,
  SESSION_MAX_AGE,
  verifySigned,
  signPayload,
} from "./auth";
import { layout, loginPage, maskedPre } from "./html";
import { NOTION_IDS, NOTION_PARENT_PAGE_ID, NOTION_PARENT_PAGE_NAME } from "./ids";
import { escapeHtml, isJpStockCode, parseWatchCodes } from "./mask";
import {
  NotionClient,
  checkboxVal,
  dateStart,
  jstToday,
  relationIds,
  richPlain,
  selectEquals,
  selectName,
  setCheckbox,
  setDate,
  setRelation,
  setRichText,
  setSelect,
  setTitle,
  titlePlain,
} from "./notion";
import type { Env, SessionUser } from "./types";
import { d1YenStore, readYenForOwner } from "./yen";

const FINAL_OPTIONS = ["残す", "落とす", "買う", "売る", "待つ", "見送る"] as const;

function notionFrom(env: Env): NotionClient {
  return new NotionClient(env.NOTION_TOKEN ?? "", {
    agent: env.NOTION_AGENT_DB_ID || NOTION_IDS.agent.database_id,
    rule: env.NOTION_RULE_DB_ID || NOTION_IDS.rule.database_id,
    job: env.NOTION_JOB_DB_ID || NOTION_IDS.job.database_id,
    decision: env.NOTION_DECISION_DB_ID || NOTION_IDS.decision.database_id,
    review: env.NOTION_REVIEW_DB_ID || NOTION_IDS.review.database_id,
  });
}

function originOf(c: { req: { url: string }; env: Env }): string {
  if (c.env.APP_ORIGIN) return c.env.APP_ORIGIN.replace(/\/$/, "");
  return new URL(c.req.url).origin;
}

async function sessionUser(env: Env, cookieHeaderValue: string | undefined): Promise<SessionUser | null> {
  const sid = parseCookies(cookieHeaderValue)[SESSION_COOKIE];
  if (!sid) return null;
  const row = await env.DB.prepare(
    "SELECT user_id, email, name, expires_at FROM sessions WHERE id = ?",
  )
    .bind(sid)
    .first<{ user_id: string; email: string; name: string; expires_at: number }>();
  if (!row || row.expires_at < Date.now() / 1000) return null;
  return { userId: row.user_id, email: row.email, name: row.name };
}

function bearerOk(header: string | undefined, secret: string | undefined): boolean {
  if (!secret) return false;
  const m = header?.match(/^Bearer\s+(.+)$/i);
  return Boolean(m && m[1] === secret);
}

export function createApp() {
  const app = new Hono<{ Bindings: Env; Variables: { user: SessionUser } }>();

  app.get("/healthz", (c) =>
    c.json({
      ok: true,
      name: "ai-expert-web",
      parent: NOTION_PARENT_PAGE_NAME,
      parentPageId: NOTION_PARENT_PAGE_ID,
    }),
  );

  app.post("/api/internal/yen", async (c) => {
    if (!bearerOk(c.req.header("authorization"), c.env.YEN_STORE_SECRET)) {
      return c.json({ error: "unauthorized" }, 401);
    }
    const body = (await c.req.json().catch(() => null)) as Record<string, unknown> | null;
    const notion_decision_id = String(body?.notion_decision_id ?? "");
    const user_id = String(body?.user_id ?? "");
    const code = String(body?.code ?? "");
    if (!notion_decision_id || !user_id || !code) {
      return c.json({ error: "notion_decision_id, user_id, code required" }, 400);
    }
    const store = d1YenStore(c.env.DB);
    const result = await store.insertOnce({
      notion_decision_id,
      user_id,
      code,
      side: body?.side as string | undefined,
      as_of: body?.as_of as string | undefined,
      entry_yen: num(body?.entry_yen),
      stop_yen: num(body?.stop_yen),
      take_yen: num(body?.take_yen),
      size_yen: num(body?.size_yen),
      source: String(body?.source ?? "automation"),
    });
    if (result === "exists") return c.json({ ok: false, error: "exists" }, 409);
    return c.json({ ok: true }, 201);
  });

  app.patch("/api/internal/yen/:id/result", async (c) => {
    if (!bearerOk(c.req.header("authorization"), c.env.YEN_STORE_SECRET)) {
      return c.json({ error: "unauthorized" }, 401);
    }
    const body = (await c.req.json().catch(() => null)) as Record<string, unknown> | null;
    const ok = await d1YenStore(c.env.DB).updateResult(c.req.param("id"), {
      result_pct: num(body?.result_pct),
      vs_close_pct: num(body?.vs_close_pct),
      vs_topix_pct: num(body?.vs_topix_pct),
    });
    if (!ok) return c.json({ error: "not_found" }, 404);
    return c.json({ ok: true });
  });

  app.get("/login", (c) => {
    const err = c.req.query("e");
    return c.html(loginPage(Boolean(c.env.GOOGLE_CLIENT_ID), err), err ? 401 : 200);
  });

  app.get("/auth/google", async (c) => {
    const clientId = c.env.GOOGLE_CLIENT_ID;
    const secret = c.env.SESSION_SECRET;
    if (!clientId || !secret) return c.redirect("/login?e=oauth_unconfigured");
    const state = await randomUrlToken(16);
    const verifier = await randomUrlToken(32);
    const url = await buildGoogleAuthUrl({
      clientId,
      redirectUri: `${originOf(c)}/auth/callback`,
      state,
      verifier,
    });
    const packed = await signPayload(secret, JSON.stringify({ state, verifier }));
    c.header("set-cookie", cookieHeader(OAUTH_COOKIE, packed, { maxAge: 600 }));
    return c.redirect(url);
  });

  app.get("/auth/callback", async (c) => {
    const clientId = c.env.GOOGLE_CLIENT_ID;
    const clientSecret = c.env.GOOGLE_CLIENT_SECRET;
    const sessionSecret = c.env.SESSION_SECRET;
    if (!clientId || !clientSecret || !sessionSecret) return c.redirect("/login?e=oauth_unconfigured");
    const code = c.req.query("code");
    const state = c.req.query("state");
    const packed = getCookie(c, OAUTH_COOKIE);
    if (!code || !state || !packed) return c.redirect("/login?e=oauth_state");
    const payload = await verifySigned(sessionSecret, packed);
    if (!payload) return c.redirect("/login?e=oauth_state");
    let parsed: { state: string; verifier: string };
    try {
      parsed = JSON.parse(payload) as { state: string; verifier: string };
    } catch {
      return c.redirect("/login?e=oauth_state");
    }
    if (parsed.state !== state) return c.redirect("/login?e=oauth_state");
    let google: { sub: string; email: string; name: string };
    try {
      google = await exchangeGoogleCode({
        clientId,
        clientSecret,
        redirectUri: `${originOf(c)}/auth/callback`,
        code,
        verifier: parsed.verifier,
      });
    } catch {
      return c.redirect("/login?e=oauth_exchange");
    }
    const sid = await randomUrlToken(32);
    const expires = Math.floor(Date.now() / 1000) + SESSION_MAX_AGE;
    await c.env.DB.prepare(
      "INSERT OR REPLACE INTO users (user_id, email, name) VALUES (?, ?, ?)",
    )
      .bind(google.sub, google.email, google.name)
      .run();
    await c.env.DB.prepare(
      "INSERT INTO sessions (id, user_id, email, name, expires_at) VALUES (?, ?, ?, ?, ?)",
    )
      .bind(sid, google.sub, google.email, google.name, expires)
      .run();
    deleteCookie(c, OAUTH_COOKIE);
    setCookie(c, SESSION_COOKIE, sid, {
      httpOnly: true,
      secure: true,
      sameSite: "Lax",
      path: "/",
      maxAge: SESSION_MAX_AGE,
    });
    return c.redirect("/");
  });

  app.post("/logout", (c) => {
    deleteCookie(c, SESSION_COOKIE, { path: "/" });
    return c.redirect("/login");
  });

  app.use("*", async (c, next) => {
    const path = new URL(c.req.url).pathname;
    if (
      path === "/login" ||
      path.startsWith("/auth/") ||
      path === "/healthz" ||
      path.startsWith("/api/internal/")
    ) {
      return next();
    }
    const user = await sessionUser(c.env, c.req.header("cookie"));
    if (!user) return c.redirect("/login");
    c.set("user", user);
    return next();
  });

  app.get("/", async (c) => {
    const user = c.get("user");
    const n = notionFrom(c.env);
    if (!n.configured()) {
      return c.html(
        layout(
          "ホーム",
          `<div class="card"><p class="warn">Notion DB ID または NOTION_TOKEN が未設定です。</p>
           <p>親ページ ${escapeHtml(NOTION_PARENT_PAGE_NAME)}（${NOTION_PARENT_PAGE_ID}）</p></div>`,
          user,
        ),
      );
    }
    const agent = await findAgent(n, user.userId);
    if (!agent) return c.redirect("/onboarding");
    const st = selectName(agent.properties["状態"]);
    if (st !== "運用中") return c.redirect("/onboarding");
    return c.html(
      layout(
        "ホーム",
        `<div class="card">
          <p>${escapeHtml(titlePlain(agent.properties["エージェント名"]) || user.name)} としてログインしています。</p>
          <p class="muted">今日の入力で仕事を未着手起票 → 随時実行が拾います。レポートは円なし。自分の円帯は判断の「円を見る」から。</p>
        </div>`,
        user,
      ),
    );
  });

  app.get("/onboarding", async (c) => {
    const user = c.get("user");
    const n = notionFrom(c.env);
    const agent = n.configured() ? await findAgent(n, user.userId) : null;
    const p = agent?.properties ?? {};
    const v = (key: string) => escapeHtml(richPlain(p[key]));
    return c.html(
      layout(
        "オンボーディング",
        `<div class="card">
          <h2>制約 4 項目とウォッチ</h2>
          <p class="muted">オーナー（Notion person）は運営が初回だけ紐づけます。Web は WebユーザーID だけ書きます。ルール公開の既定は ON です。</p>
          <form method="post" action="/onboarding">
            <label>エージェント名 <input name="name" value="${escapeHtml(titlePlain(p["エージェント名"]) || `${user.name}のエージェント`)}"/></label>
            <label>投資期間 <input name="horizon" value="${v("投資期間")}"/></label>
            <label>1銘柄あたり金額（言葉） <input name="size" value="${v("1銘柄あたり金額")}" placeholder="20万円まで"/></label>
            <label>許容損失 <input name="loss" value="${v("許容損失")}"/></label>
            <label>見ない領域（EDINET 33 業種の言葉） <input name="avoid" value="${v("見ない領域")}"/></label>
            <label>ウォッチコード（4桁、最大30、カンマ区切り） <input name="watch" value="${v("ウォッチコード")}"/></label>
            <label><input type="checkbox" name="public_rules" value="1" ${agent && !checkboxVal(p["ルール公開"]) ? "" : "checked"} style="width:auto"/> ルール公開（他人の一覧に出す）</label>
            <p><button type="submit">保存</button></p>
          </form>
        </div>`,
        user,
      ),
    );
  });

  app.post("/onboarding", async (c) => {
    const user = c.get("user");
    const n = notionFrom(c.env);
    if (!n.configured()) return c.html(layout("設定", `<p class="warn">Notion 未設定</p>`, user), 503);
    const form = await c.req.parseBody();
    const horizon = String(form.horizon ?? "").trim();
    const size = String(form.size ?? "").trim();
    const loss = String(form.loss ?? "").trim();
    const avoid = String(form.avoid ?? "").trim();
    const watch = parseWatchCodes(String(form.watch ?? "")).join(",");
    const name = String(form.name ?? "").trim() || `${user.name}のエージェント`;
    const pub = form.public_rules === "1";
    const ready = Boolean(horizon && size && loss && avoid);
    const state = ready ? "運用中" : "設定中";
    const properties: Record<string, unknown> = {
      エージェント名: setTitle(name),
      WebユーザーID: setRichText(user.userId),
      状態: setSelect(state),
      投資期間: setRichText(horizon),
      "1銘柄あたり金額": setRichText(size),
      許容損失: setRichText(loss),
      見ない領域: setRichText(avoid),
      ウォッチコード: setRichText(watch),
      ルール公開: setCheckbox(pub),
    };
    const existing = await findAgent(n, user.userId);
    if (existing) {
      const upd = await n.updatePage(existing.id, properties);
      if ("error" in upd) return c.html(layout("設定", `<p class="warn">${escapeHtml(upd.error)}</p>`, user), 502);
    } else {
      const created = await n.createPage(n.ids.agent, properties);
      if ("error" in created) return c.html(layout("設定", `<p class="warn">${escapeHtml(created.error)}</p>`, user), 502);
      await c.env.DB.prepare("UPDATE users SET notion_agent_page_id = ? WHERE user_id = ?")
        .bind("id" in created ? created.id : null, user.userId)
        .run();
    }
    return c.redirect(ready ? "/" : "/onboarding");
  });

  app.get("/jobs/new", (c) => {
    const user = c.get("user");
    return c.html(
      layout(
        "今日の入力",
        `<div class="card">
          <h2>仕事を未着手で起票</h2>
          <p class="muted">起票元 = Web。売買判断は 4 桁コード必須。発注はしません。</p>
          <form method="post" action="/jobs">
            <label>目的
              <select name="purpose">
                <option value="スクリーニング">スクリーニング</option>
                <option value="売買判断">売買判断</option>
              </select>
            </label>
            <label>対象コード（売買判断は必須） <input name="code" maxlength="4" placeholder="6098"/></label>
            <label>方向（売買判断）
              <select name="side">
                <option value="">（スクリーニングは空）</option>
                <option value="買い">買い</option>
                <option value="売り">売り</option>
                <option value="両方">両方</option>
              </select>
            </label>
            <p><button type="submit">起票</button></p>
          </form>
        </div>`,
        user,
      ),
    );
  });

  app.post("/jobs", async (c) => {
    const user = c.get("user");
    const n = notionFrom(c.env);
    if (!n.configured()) return c.html(layout("入力", `<p class="warn">Notion 未設定</p>`, user), 503);
    const agent = await findAgent(n, user.userId);
    if (!agent || selectName(agent.properties["状態"]) !== "運用中") return c.redirect("/onboarding");
    const form = await c.req.parseBody();
    const purpose = String(form.purpose ?? "");
    if (purpose !== "スクリーニング" && purpose !== "売買判断") {
      return c.html(layout("入力", `<p class="warn">目的はスクリーニングか売買判断だけです。</p>`, user), 400);
    }
    const code = String(form.code ?? "").trim();
    const side = String(form.side ?? "").trim();
    if (purpose === "売買判断" && !isJpStockCode(code)) {
      return c.html(layout("入力", `<p class="warn">売買判断は日本株の4桁コードが必須です。</p>`, user), 400);
    }
    const today = jstToday();
    const title = `${today} ${purpose}${code ? ` ${code}` : ""}`;
    const properties: Record<string, unknown> = {
      仕事名: setTitle(title),
      エージェント: setRelation(agent.id),
      目的: setSelect(purpose),
      対象日: setDate(today),
      状態: setSelect("未着手"),
      起票元: setSelect("Web"),
    };
    if (code) properties["対象コード"] = setRichText(code);
    if (side && (side === "買い" || side === "売り" || side === "両方")) properties["方向"] = setSelect(side);
    const created = await n.createPage(n.ids.job, properties);
    if ("error" in created) return c.html(layout("入力", `<p class="warn">${escapeHtml(created.error)}</p>`, user), 502);
    return c.redirect("/reports");
  });

  app.get("/reports", async (c) => {
    const user = c.get("user");
    const n = notionFrom(c.env);
    if (!n.configured()) return c.html(layout("レポート", `<p class="warn">Notion 未設定</p>`, user), 503);
    const { results, error } = await n.query(n.ids.job, {
      filter: selectEquals("状態", "レポート済"),
      sorts: [{ property: "対象日", direction: "descending" }],
      page_size: 20,
    });
    if (error) return c.html(layout("レポート", `<p class="warn">${escapeHtml(error)}</p>`, user), 502);
    const rows = results
      .map((p) => {
        const name = titlePlain(p.properties["仕事名"]);
        const purpose = selectName(p.properties["目的"]);
        const day = dateStart(p.properties["対象日"]).slice(0, 10);
        const summary = richPlain(p.properties["要約"]);
        return `<tr><td><a href="/reports/${p.id}">${escapeHtml(name || p.id)}</a></td><td>${escapeHtml(purpose)}</td><td>${escapeHtml(day)}</td><td>${escapeHtml(summary)}</td></tr>`;
      })
      .join("");
    return c.html(
      layout(
        "レポート",
        `<div class="card">
          <h2>レポート（円なし）</h2>
          <p class="muted">他人の仕事本文も読めます。Yahoo / JPX 由来の円は出しません。</p>
          <table><thead><tr><th>仕事</th><th>目的</th><th>対象日</th><th>要約</th></tr></thead><tbody>${rows || `<tr><td colspan="4">まだありません</td></tr>`}</tbody></table>
        </div>`,
        user,
      ),
    );
  });

  app.get("/reports/:id", async (c) => {
    const user = c.get("user");
    const n = notionFrom(c.env);
    const page = await n.getPage(c.req.param("id"));
    if (!page) return c.html(layout("レポート", `<p class="warn">見つかりません</p>`, user), 404);
    const body = await n.pagePlainText(page.id);
    const { results: decisions } = await n.query(n.ids.decision, {
      filter: { property: "元仕事", relation: { contains: page.id } },
      page_size: 20,
    });
    const agent = await findAgent(n, user.userId);
    const decisionHtml = decisions
      .map((d) => {
        const id = titlePlain(d.properties["判断ID"]);
        const code = richPlain(d.properties["コード"]);
        const klass = selectName(d.properties["分類"]);
        const conclusion = selectName(d.properties["AIの結論"]);
        const reason = richPlain(d.properties["入らない理由"]);
        const final = selectName(d.properties["最終判断"]);
        const agentIds = relationIds(d.properties["エージェント"]);
        const mine = Boolean(agent && agentIds.includes(agent.id));
        const yenLink = mine && id ? ` <a href="/yen/${encodeURIComponent(id)}">円を見る（本人）</a>` : "";
        const finalForm = mine
          ? `<form method="post" action="/decisions/${d.id}/final">
               <label>最終判断（人だけ。AIは呼ばない）
                 <select name="final">${FINAL_OPTIONS.map((o) => `<option ${final === o ? "selected" : ""}>${o}</option>`).join("")}</select>
               </label>
               <button type="submit">保存</button>
             </form>`
          : `<p>最終判断（閲覧）: ${escapeHtml(final || "未入力")}</p>`;
        return `<div class="card"><p><strong>${escapeHtml(id)}</strong> ${escapeHtml(code)} ${escapeHtml(klass)} ${escapeHtml(conclusion)}${yenLink}</p>
          <p>入らない理由: ${escapeHtml(reason)}</p>${finalForm}</div>`;
      })
      .join("");
    return c.html(
      layout(
        "レポート",
        `<div class="card"><h2>${escapeHtml(titlePlain(page.properties["仕事名"]))}</h2>
         <p class="muted">帯の円は本人画面。ここでは条件の成立／未成立だけ。</p>
         ${maskedPre(body)}</div>${decisionHtml}`,
        user,
      ),
    );
  });

  app.post("/decisions/:id/final", async (c) => {
    const user = c.get("user");
    const n = notionFrom(c.env);
    const page = await n.getPage(c.req.param("id"));
    if (!page) return c.html(layout("判断", `<p class="warn">見つかりません</p>`, user), 404);
    const agent = await findAgent(n, user.userId);
    const agentIds = relationIds(page.properties["エージェント"]);
    if (!agent || !agentIds.includes(agent.id)) {
      return c.html(layout("判断", `<p class="warn">最終判断の編集は本人だけです。</p>`, user), 403);
    }
    const form = await c.req.parseBody();
    const final = String(form.final ?? "");
    if (!FINAL_OPTIONS.includes(final as (typeof FINAL_OPTIONS)[number])) {
      return c.html(layout("判断", `<p class="warn">最終判断の語彙が不正です。</p>`, user), 400);
    }
    const upd = await n.updatePage(page.id, { 最終判断: setSelect(final) });
    if ("error" in upd) return c.html(layout("判断", `<p class="warn">${escapeHtml(upd.error)}</p>`, user), 502);
    const job = relationIds(page.properties["元仕事"])[0];
    return c.redirect(job ? `/reports/${job}` : "/reports");
  });

  app.get("/yen/:id", async (c) => {
    const user = c.get("user");
    const got = await readYenForOwner(d1YenStore(c.env.DB), c.req.param("id"), user.userId);
    if (got.status === 404) return c.html(layout("円帯", `<p>円帯レコードがありません。</p>`, user), 404);
    if (got.status === 403) return c.html(layout("円帯", `<p class="warn">他人の円は表示しません。</p>`, user), 403);
    const r = got.row!;
    return c.html(
      layout(
        "円帯（本人）",
        `<div class="card">
          <h2>判断 ${escapeHtml(r.notion_decision_id)}</h2>
          <table>
            <tr><th>コード</th><td>${escapeHtml(r.code)}</td></tr>
            <tr><th>方向</th><td>${escapeHtml(r.side ?? "")}</td></tr>
            <tr><th>基準日</th><td>${escapeHtml(r.as_of ?? "")}</td></tr>
            <tr><th>entry_yen</th><td>${r.entry_yen ?? ""}</td></tr>
            <tr><th>stop_yen</th><td>${r.stop_yen ?? ""}</td></tr>
            <tr><th>take_yen</th><td>${r.take_yen ?? ""}</td></tr>
            <tr><th>size_yen</th><td>${r.size_yen ?? ""}</td></tr>
            <tr><th>result_pct</th><td>${r.result_pct ?? ""}</td></tr>
            <tr><th>vs_close_pct</th><td>${r.vs_close_pct ?? ""}</td></tr>
            <tr><th>vs_topix_pct</th><td>${r.vs_topix_pct ?? ""}</td></tr>
          </table>
        </div>`,
        user,
      ),
    );
  });

  app.get("/rules", async (c) => {
    const user = c.get("user");
    const n = notionFrom(c.env);
    if (!n.configured()) return c.html(layout("ルール", `<p class="warn">Notion 未設定</p>`, user), 503);
    const { results, error } = await n.query(n.ids.rule, {
      filter: selectEquals("状態", "発効"),
      page_size: 30,
    });
    if (error) return c.html(layout("ルール", `<p class="warn">${escapeHtml(error)}</p>`, user), 502);
    const publicAgents = await n.query(n.ids.agent, {
      filter: { and: [selectEquals("状態", "運用中"), { property: "ルール公開", checkbox: { equals: true } }] },
      page_size: 20,
    });
    const publicAgentIds = new Set(publicAgents.results.map((a) => a.id));
    const visible = [];
    for (const r of results) {
      const kind = selectName(r.properties["種別"]);
      if (kind !== "個人") {
        visible.push(r);
        continue;
      }
      // 個人の発効: 適用仕事 / 適用判断 → エージェント が ルール公開なら他人にも出す。
      // オーナー person 未紐づけでは「自分の個人ルール」を WebユーザーID だけでは特定できない。
      const linkedAgents = [
        ...relationIds(r.properties["適用仕事"]),
        ...relationIds(r.properties["適用判断"]),
      ];
      // 適用仕事/判断の id はエージェントではない。公開エージェントと直接一致すれば（将来列）出す。
      if (linkedAgents.some((id) => publicAgentIds.has(id))) visible.push(r);
    }
    const items = await Promise.all(
      visible.map(async (r) => {
        const body = await n.pagePlainText(r.id);
        const kind = selectName(r.properties["種別"]);
        const purpose = selectName(r.properties["目的"]);
        return `<div class="card"><h3>${escapeHtml(titlePlain(r.properties["ルール名"]))}</h3>
          <p class="muted">${escapeHtml(kind)} / ${escapeHtml(purpose)}</p>${maskedPre(body)}</div>`;
      }),
    );
    return c.html(
      layout(
        "発効ルール",
        `<div class="card"><h2>発効ルール</h2>
         <p class="muted">草案・棄却は出しません。本文の円はマスクします。他人に出すのは共通の発効と、ルール公開エージェントに紐づく個人の発効です。</p></div>
         ${items.join("") || "<p>発効ルールがありません</p>"}`,
        user,
      ),
    );
  });

  return app;
}

async function findAgent(n: NotionClient, webUserId: string) {
  const { results } = await n.query(n.ids.agent, {
    filter: { property: "WebユーザーID", rich_text: { equals: webUserId } },
    page_size: 1,
  });
  return results[0] ?? null;
}

function num(v: unknown): number | null {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

const app = createApp();
export default {
  fetch: (request: Request, env: Env, ctx: ExecutionContext) => app.fetch(request, env, ctx),
};

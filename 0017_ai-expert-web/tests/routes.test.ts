import { describe, expect, it } from "vitest";
import { createApp } from "../src/index";
import { NOTION_IDS, NOTION_PARENT_PAGE_ID } from "../src/ids";
import type { Env } from "../src/types";

type YenRow = Record<string, unknown>;

function fakeD1(): D1Database {
  const yen = new Map<string, YenRow>();
  const sessions = new Map<string, YenRow>();
  const users = new Map<string, YenRow>();

  const api: D1Database = {
    prepare(sql: string) {
      const s = sql.replace(/\s+/g, " ").trim();
      return {
        bind(...args: unknown[]) {
          return {
            async first() {
              if (s.includes("FROM sessions WHERE id")) return sessions.get(String(args[0])) ?? null;
              if (s.includes("FROM decision_yen WHERE notion_decision_id")) return yen.get(String(args[0])) ?? null;
              if (s.includes("FROM users WHERE user_id")) return users.get(String(args[0])) ?? null;
              return null;
            },
            async run() {
              if (s.startsWith("INSERT INTO decision_yen") || s.startsWith("INSERT INTO decision_yen")) {
                const id = String(args[0]);
                yen.set(id, {
                  notion_decision_id: id,
                  user_id: args[1],
                  code: args[2],
                  side: args[3],
                  as_of: args[4],
                  entry_yen: args[5],
                  stop_yen: args[6],
                  take_yen: args[7],
                  size_yen: args[8],
                  source: args[9],
                  result_pct: null,
                  vs_close_pct: null,
                  vs_topix_pct: null,
                });
              }
              if (s.startsWith("INSERT INTO sessions")) {
                sessions.set(String(args[0]), {
                  id: args[0],
                  user_id: args[1],
                  email: args[2],
                  name: args[3],
                  expires_at: args[4],
                });
              }
              if (s.includes("INSERT OR REPLACE INTO users")) {
                users.set(String(args[0]), { user_id: args[0], email: args[1], name: args[2] });
              }
              if (s.startsWith("UPDATE decision_yen SET result_pct")) {
                const row = yen.get(String(args[3]));
                if (row) {
                  row.result_pct = args[0];
                  row.vs_close_pct = args[1];
                  row.vs_topix_pct = args[2];
                }
              }
              return { success: true };
            },
            async all() {
              return { results: [] };
            },
          };
        },
      };
    },
  } as unknown as D1Database;
  return api;
}

function env(over: Partial<Env> = {}): Env {
  return {
    DB: fakeD1(),
    PUBLIC_DATA_BASE: "https://kabulab-cf.satoki252595.workers.dev",
    NOTION_PARENT_PAGE_NAME: "AI投資エージェント",
    NOTION_PARENT_PAGE_ID,
    NOTION_AGENT_DB_ID: NOTION_IDS.agent.database_id,
    NOTION_RULE_DB_ID: NOTION_IDS.rule.database_id,
    NOTION_JOB_DB_ID: NOTION_IDS.job.database_id,
    NOTION_DECISION_DB_ID: NOTION_IDS.decision.database_id,
    NOTION_REVIEW_DB_ID: NOTION_IDS.review.database_id,
    YEN_STORE_SECRET: "test-yen-secret",
    ...over,
  };
}

describe("route guards", () => {
  const app = createApp();

  it("requires login on /", async () => {
    const res = await app.fetch(new Request("https://example.com/"), env());
    expect(res.status).toBe(302);
    expect(res.headers.get("location")).toContain("/login");
  });

  it("serves login and healthz without session", async () => {
    const login = await app.fetch(new Request("https://example.com/login"), env());
    expect(login.status).toBe(200);
    const health = await app.fetch(new Request("https://example.com/healthz"), env());
    expect(health.status).toBe(200);
    const body = (await health.json()) as { parentPageId: string };
    expect(body.parentPageId).toBe(NOTION_PARENT_PAGE_ID);
  });

  it("rejects yen POST without bearer", async () => {
    const res = await app.fetch(
      new Request("https://example.com/api/internal/yen", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ notion_decision_id: "d1", user_id: "u1", code: "6098" }),
      }),
      env(),
    );
    expect(res.status).toBe(401);
  });

  it("writes yen once then 409; other user cannot read", async () => {
    const e = env();
    const post = () =>
      app.fetch(
        new Request("https://example.com/api/internal/yen", {
          method: "POST",
          headers: { "content-type": "application/json", authorization: "Bearer test-yen-secret" },
          body: JSON.stringify({
            notion_decision_id: "dec-1",
            user_id: "user-a",
            code: "6098",
            entry_yen: 1234,
          }),
        }),
        e,
      );
    expect((await post()).status).toBe(201);
    expect((await post()).status).toBe(409);

    await e.DB.prepare("INSERT INTO sessions (id, user_id, email, name, expires_at) VALUES (?, ?, ?, ?, ?)")
      .bind("sess-b", "user-b", "b@example.com", "B", Math.floor(Date.now() / 1000) + 3600)
      .run();
    const peek = await app.fetch(new Request("https://example.com/yen/dec-1", { headers: { cookie: "ae_session=sess-b" } }), e);
    expect(peek.status).toBe(403);
    const html = await peek.text();
    expect(html).not.toContain("1234");
    expect(html).toContain("他人の円");
  });
});

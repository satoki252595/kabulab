import { describe, expect, it } from "vitest";
import type { YenStore } from "../src/yen";
import { canReadYen, readYenForOwner } from "../src/yen";

function memoryYen(): YenStore {
  const rows = new Map<string, Awaited<ReturnType<YenStore["get"]>>>();
  return {
    async get(id) {
      return rows.get(id) ?? null;
    },
    async insertOnce(row) {
      if (rows.has(row.notion_decision_id)) return "exists";
      rows.set(row.notion_decision_id, {
        notion_decision_id: row.notion_decision_id,
        user_id: row.user_id,
        code: row.code,
        side: row.side ?? null,
        as_of: row.as_of ?? null,
        entry_yen: row.entry_yen ?? null,
        stop_yen: row.stop_yen ?? null,
        take_yen: row.take_yen ?? null,
        size_yen: row.size_yen ?? null,
        result_pct: null,
        vs_close_pct: null,
        vs_topix_pct: null,
        source: row.source ?? "automation",
      });
      return "created";
    },
    async updateResult(id, patch) {
      const row = rows.get(id);
      if (!row) return false;
      row.result_pct = patch.result_pct ?? null;
      row.vs_close_pct = patch.vs_close_pct ?? null;
      row.vs_topix_pct = patch.vs_topix_pct ?? null;
      return true;
    },
  };
}

describe("yen ACL", () => {
  it("allows owner and forbids others", async () => {
    const store = memoryYen();
    await store.insertOnce({
      notion_decision_id: "dec-1",
      user_id: "user-a",
      code: "6098",
      entry_yen: 4000,
    });
    expect(canReadYen("user-a", "user-a")).toBe(true);
    expect(canReadYen("user-a", "user-b")).toBe(false);
    expect((await readYenForOwner(store, "dec-1", "user-a")).status).toBe(200);
    expect((await readYenForOwner(store, "dec-1", "user-b")).status).toBe(403);
    expect((await readYenForOwner(store, "missing", "user-a")).status).toBe(404);
    expect(await store.insertOnce({ notion_decision_id: "dec-1", user_id: "user-a", code: "6098" })).toBe(
      "exists",
    );
  });
});

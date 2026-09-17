export function canReadYen(rowUserId: string, sessionUserId: string): boolean {
  return Boolean(rowUserId) && rowUserId === sessionUserId;
}

export type YenStore = {
  get(id: string): Promise<{
    notion_decision_id: string;
    user_id: string;
    code: string;
    side: string | null;
    as_of: string | null;
    entry_yen: number | null;
    stop_yen: number | null;
    take_yen: number | null;
    size_yen: number | null;
    result_pct: number | null;
    vs_close_pct: number | null;
    vs_topix_pct: number | null;
    source: string | null;
  } | null>;
  insertOnce(row: {
    notion_decision_id: string;
    user_id: string;
    code: string;
    side?: string;
    as_of?: string;
    entry_yen?: number | null;
    stop_yen?: number | null;
    take_yen?: number | null;
    size_yen?: number | null;
    source?: string;
  }): Promise<"created" | "exists">;
  updateResult(
    id: string,
    patch: { result_pct?: number | null; vs_close_pct?: number | null; vs_topix_pct?: number | null },
  ): Promise<boolean>;
};

export async function readYenForOwner(
  store: YenStore,
  decisionId: string,
  sessionUserId: string,
): Promise<{ status: 200 | 403 | 404; row?: Awaited<ReturnType<YenStore["get"]>> }> {
  const row = await store.get(decisionId);
  if (!row) return { status: 404 };
  if (!canReadYen(row.user_id, sessionUserId)) return { status: 403 };
  return { status: 200, row };
}

export function d1YenStore(db: D1Database): YenStore {
  return {
    async get(id) {
      return db
        .prepare(
          `SELECT notion_decision_id, user_id, code, side, as_of, entry_yen, stop_yen, take_yen, size_yen,
                  result_pct, vs_close_pct, vs_topix_pct, source
           FROM decision_yen WHERE notion_decision_id = ?`,
        )
        .bind(id)
        .first();
    },
    async insertOnce(row) {
      const existing = await db
        .prepare("SELECT notion_decision_id FROM decision_yen WHERE notion_decision_id = ?")
        .bind(row.notion_decision_id)
        .first();
      if (existing) return "exists";
      await db
        .prepare(
          `INSERT INTO decision_yen (
             notion_decision_id, user_id, code, side, as_of,
             entry_yen, stop_yen, take_yen, size_yen, source
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        )
        .bind(
          row.notion_decision_id,
          row.user_id,
          row.code,
          row.side ?? null,
          row.as_of ?? null,
          row.entry_yen ?? null,
          row.stop_yen ?? null,
          row.take_yen ?? null,
          row.size_yen ?? null,
          row.source ?? "automation",
        )
        .run();
      return "created";
    },
    async updateResult(id, patch) {
      const existing = await db
        .prepare("SELECT notion_decision_id FROM decision_yen WHERE notion_decision_id = ?")
        .bind(id)
        .first();
      if (!existing) return false;
      await db
        .prepare(
          `UPDATE decision_yen SET result_pct = ?, vs_close_pct = ?, vs_topix_pct = ?
           WHERE notion_decision_id = ?`,
        )
        .bind(patch.result_pct ?? null, patch.vs_close_pct ?? null, patch.vs_topix_pct ?? null, id)
        .run();
      return true;
    },
  };
}

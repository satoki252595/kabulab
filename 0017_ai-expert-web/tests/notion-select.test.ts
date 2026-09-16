import { describe, expect, it } from "vitest";
import { selectEquals, setSelect, setTitle } from "../src/notion";
import { NOTION_IDS, NOTION_PARENT_PAGE_ID } from "../src/ids";
import { sliceUrls } from "../src/slices";

describe("Notion select (not status)", () => {
  it("filters 状態 via select equals", () => {
    const f = selectEquals("状態", "運用中");
    expect(f).toEqual({ property: "状態", select: { equals: "運用中" } });
    expect(JSON.stringify(f)).not.toMatch(/"status"/);
    expect(setSelect("実行中")).toEqual({ select: { name: "実行中" } });
  });

  it("writes 判断ID as title", () => {
    expect(setTitle("2026-09-16 売買判断 6098")).toEqual({
      title: [{ type: "text", text: { content: "2026-09-16 売買判断 6098" } }],
    });
  });

  it("ships live 5DB ids", () => {
    expect(NOTION_PARENT_PAGE_ID).toBe("3ddd74ff-84cd-8178-9abb-cf86708626c0");
    expect(NOTION_IDS.job.database_id).toBe("dd841447-06d0-4385-811e-ee52abf3185e");
    expect(NOTION_IDS.decision.data_source_id).toBe("22d332de-be5e-4193-9280-c509262c7629");
  });
});

describe("public JSON slices", () => {
  it("keeps limit on screening and n=8 on margin", () => {
    const u = sliceUrls();
    expect(u.orders).toContain("limit=30");
    expect(u.margin).toContain("n=8");
    expect(u.daily).toContain("code=6098");
  });
});

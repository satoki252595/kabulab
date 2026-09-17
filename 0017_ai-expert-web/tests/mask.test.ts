import { describe, expect, it } from "vitest";
import { findForbidden, isJpStockCode, maskYen, parseWatchCodes } from "../src/mask";

describe("maskYen", () => {
  it("masks yen amounts in shared copy", () => {
    expect(maskYen("終値 4,000円でエントリー")).toContain("［円は本人画面］");
    expect(maskYen("¥1200")).toBe("［円は本人画面］");
    expect(maskYen("条件成立")).toBe("条件成立");
  });
});

describe("forbidden", () => {
  it("flags 今すぐ and 買い推奨", () => {
    expect(findForbidden("今すぐ買うのは買い推奨です")).toEqual(
      expect.arrayContaining(["買い推奨", "今すぐ"]),
    );
  });
});

describe("codes", () => {
  it("parses up to 30 unique 4-digit codes", () => {
    expect(parseWatchCodes("6098, 9984、7203.T")).toEqual(["6098", "9984", "7203"]);
    expect(isJpStockCode("6098")).toBe(true);
    expect(isJpStockCode("AAPL")).toBe(false);
  });
});

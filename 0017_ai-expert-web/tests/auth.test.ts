import { describe, expect, it } from "vitest";
import { signPayload, verifySigned } from "../src/auth";

describe("signed oauth cookie", () => {
  it("round-trips state payload", async () => {
    const secret = "session-secret-for-test";
    const token = await signPayload(secret, JSON.stringify({ state: "abc", verifier: "def" }));
    const payload = await verifySigned(secret, token);
    expect(JSON.parse(payload ?? "{}")).toEqual({ state: "abc", verifier: "def" });
    expect(await verifySigned("other", token)).toBeNull();
  });
});

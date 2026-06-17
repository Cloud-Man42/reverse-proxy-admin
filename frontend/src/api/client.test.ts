import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, request, setCsrfToken } from "./client";

describe("api client", () => {
  beforeEach(() => {
    setCsrfToken(null);
    document.cookie = "nginx_admin_csrf=; Max-Age=0";
  });

  it("throws ApiError with JSON detail on failed requests", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ detail: "Invalid payload" }),
      }),
    );

    await expect(request("/api/proxies", { method: "POST", body: "{}" })).rejects.toThrow(ApiError);
    await expect(request("/api/proxies", { method: "POST", body: "{}" })).rejects.toThrow("Invalid payload");
  });

  it("throws ApiError with text body when response is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error("not json");
        },
        text: async () => "Server exploded",
      }),
    );

    await expect(request("/api/proxies")).rejects.toThrow("Server exploded");
  });

  it("adds CSRF header on mutating requests", async () => {
    setCsrfToken("csrf-test-token");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await request("/api/proxies", { method: "POST", body: "{}" });

    const [, options] = fetchMock.mock.calls[0];
    expect((options.headers as Headers).get("X-CSRF-Token")).toBe("csrf-test-token");
  });
});

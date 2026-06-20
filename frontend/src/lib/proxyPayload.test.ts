import { describe, expect, it } from "vitest";
import { toPayload } from "./proxyPayload";
import { ProxyFormData } from "../types";

const baseForm: ProxyFormData = {
  name: "myapp",
  domains: " example.com , , web.example.com ",
  routes: [
    {
      path_prefix: "/api",
      target_protocol: "http",
      target_host: "10.0.0.10",
      target_port: 8080,
      websocket_enabled: true,
      use_pool: false,
      backend_pool_id: null,
    },
  ],
  custom_headers: [],
  max_body_size: "",
  basic_auth_enabled: false,
  basic_auth_username: "",
  basic_auth_password: "",
  force_https: false,
  enabled: true,
};

describe("toPayload", () => {
  it("filters empty domains and maps routes", () => {
    const payload = toPayload(baseForm);

    expect(payload.domains).toEqual(["example.com", "web.example.com"]);
    expect(payload.routes).toEqual([
      {
        path_prefix: "/api",
        target_protocol: "http",
        target_host: "10.0.0.10",
        target_port: 8080,
        websocket_enabled: true,
        backend_pool_id: null,
      },
    ]);
  });

  it("defaults path prefix and null optional fields", () => {
    const payload = toPayload({
      ...baseForm,
      routes: [{ ...baseForm.routes[0], path_prefix: "" }],
      max_body_size: "",
      basic_auth_enabled: false,
      basic_auth_username: "",
      basic_auth_password: "",
    });

    expect(payload.routes[0].path_prefix).toBe("/");
    expect(payload.max_body_size).toBeNull();
    expect(payload.basic_auth_username).toBeNull();
  });
});

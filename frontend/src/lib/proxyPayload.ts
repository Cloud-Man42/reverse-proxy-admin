import { ProxyFormData } from "../types";

export function toPayload(form: ProxyFormData) {
  return {
    name: form.name,
    domains: form.domains.split(",").map((d) => d.trim()).filter(Boolean),
    routes: form.routes.map((route) => ({
      path_prefix: route.path_prefix || "/",
      target_protocol: route.target_protocol,
      target_host: route.target_host,
      target_port: Number(route.target_port),
      websocket_enabled: route.websocket_enabled,
    })),
    custom_headers: form.custom_headers,
    max_body_size: form.max_body_size || null,
    basic_auth_enabled: form.basic_auth_enabled,
    basic_auth_username: form.basic_auth_username || null,
    basic_auth_password: form.basic_auth_password || null,
    force_https: form.force_https,
    enabled: form.enabled,
  };
}

import { ApplicationTemplate, TemplatePreviewRequest, TemplateWizardState } from "../types";

export function buildInitialWizardState(template: ApplicationTemplate): TemplateWizardState {
  return {
    domain: "",
    upstream_host: "127.0.0.1",
    upstream_port: template.default_upstream_port,
    upstream_protocol: (template.default_upstream_protocol === "https" ? "https" : "http") as "http" | "https",
    name: template.slug,
    websocket_enabled: template.websocket_support,
    force_https: template.http_to_https_redirect_default,
    large_upload_enabled: template.large_upload_support,
    max_body_size: template.recommended_client_max_body_size || "",
    hsts_enabled: template.hsts_recommended,
    apply_recommended_headers: true,
    apply_security_headers: true,
    proxy_read_timeout: template.recommended_proxy_read_timeout || "",
    proxy_send_timeout: template.recommended_proxy_send_timeout || "",
    proxy_connect_timeout: template.recommended_proxy_connect_timeout || "",
    enabled: true,
  };
}

export function wizardStateToPreviewPayload(state: TemplateWizardState): TemplatePreviewRequest {
  return {
    domain: state.domain,
    upstream_host: state.upstream_host,
    upstream_port: state.upstream_port,
    upstream_protocol: state.upstream_protocol,
    name: state.name,
    websocket_enabled: state.websocket_enabled,
    force_https: state.force_https,
    large_upload_enabled: state.large_upload_enabled,
    max_body_size: state.max_body_size || undefined,
    proxy_read_timeout: state.proxy_read_timeout || undefined,
    proxy_send_timeout: state.proxy_send_timeout || undefined,
    proxy_connect_timeout: state.proxy_connect_timeout || undefined,
    hsts_enabled: state.hsts_enabled,
    apply_recommended_headers: state.apply_recommended_headers,
    apply_security_headers: state.apply_security_headers,
  };
}

import { ApplicationTemplate } from "../../types";
import { TemplateWizardState } from "../../types";

interface RecommendedSettingsPanelProps {
  template: ApplicationTemplate;
  state: TemplateWizardState;
}

export function RecommendedSettingsPanel({ template, state }: RecommendedSettingsPanelProps) {
  return (
    <div className="space-y-4 text-sm">
      <div className="rounded-lg border border-white/10 bg-black/20 p-4">
        <h4 className="mb-2 font-medium">Proxy settings</h4>
        <dl className="grid gap-2 sm:grid-cols-2">
          <div>
            <dt className="text-white/50">Domain</dt>
            <dd>{state.domain || "—"}</dd>
          </div>
          <div>
            <dt className="text-white/50">Upstream</dt>
            <dd>
              {state.upstream_protocol}://{state.upstream_host}:{state.upstream_port}
            </dd>
          </div>
          <div>
            <dt className="text-white/50">Force HTTPS</dt>
            <dd>{state.force_https ? "Yes" : "No"}</dd>
          </div>
          <div>
            <dt className="text-white/50">WebSocket</dt>
            <dd>{state.websocket_enabled ? "Enabled" : "Disabled"}</dd>
          </div>
          {state.large_upload_enabled && state.max_body_size ? (
            <div>
              <dt className="text-white/50">Max body size</dt>
              <dd>{state.max_body_size}</dd>
            </div>
          ) : null}
          {state.proxy_read_timeout ? (
            <div>
              <dt className="text-white/50">Read timeout</dt>
              <dd>{state.proxy_read_timeout}</dd>
            </div>
          ) : null}
        </dl>
      </div>

      {state.apply_recommended_headers && template.recommended_headers.length > 0 ? (
        <div className="rounded-lg border border-white/10 bg-black/20 p-4">
          <h4 className="mb-2 font-medium">Recommended headers</h4>
          <ul className="space-y-1 font-mono text-xs text-white/80">
            {template.recommended_headers.map((header) => (
              <li key={header.name}>
                {header.name}: {header.value}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {state.apply_security_headers && template.security_headers.length > 0 ? (
        <div className="rounded-lg border border-white/10 bg-black/20 p-4">
          <h4 className="mb-2 font-medium">Security headers</h4>
          <ul className="space-y-1 font-mono text-xs text-white/80">
            {template.security_headers.map((header) => (
              <li key={header.name}>
                {header.name}: {header.value}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {template.security_notes ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-amber-100">
          <h4 className="mb-1 font-medium">Security notes</h4>
          <p className="text-white/80">{template.security_notes}</p>
        </div>
      ) : null}

      {template.rate_limit_recommendation ? (
        <p className="text-white/60">Rate limit suggestion: {template.rate_limit_recommendation}</p>
      ) : null}
      {template.health_check_path ? (
        <p className="text-white/60">Suggested health check: {template.health_check_path}</p>
      ) : null}
    </div>
  );
}

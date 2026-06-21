import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { TemplateBadges } from "../components/catalog/TemplateBadges";

export function TemplateDetailPage() {
  const { slug = "" } = useParams();

  const { data: template, isLoading, isError } = useQuery({
    queryKey: ["template", slug],
    queryFn: () => api.getTemplate(slug),
    enabled: Boolean(slug),
  });

  if (isLoading) {
    return <p>Loading template...</p>;
  }

  if (isError || !template) {
    return (
      <div className="space-y-3">
        <Link to="/templates" className="text-sm text-accent hover:underline">
          ← Application Catalog
        </Link>
        <p>Template not found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <Link to={`/templates/groups/${encodeURIComponent(template.group)}`} className="text-sm text-accent hover:underline">
          ← Back to group
        </Link>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold">{template.name}</h2>
            <p className="text-sm text-white/60">{template.category}</p>
          </div>
          <Link
            to={`/templates/${encodeURIComponent(template.slug)}/wizard`}
            className="rounded-lg bg-accent px-4 py-2 text-sm text-white"
          >
            Use template
          </Link>
        </div>
      </div>

      <Card>
        <div className="space-y-4">
          <TemplateBadges template={template} />
          <p className="text-white/80">{template.long_description || template.description}</p>

          <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <dt className="text-white/50">Default upstream</dt>
              <dd>
                {template.default_upstream_protocol}://127.0.0.1:{template.default_upstream_port}
              </dd>
            </div>
            <div>
              <dt className="text-white/50">HTTPS upstream</dt>
              <dd>{template.https_upstream_supported ? "Supported" : "Not required"}</dd>
            </div>
            <div>
              <dt className="text-white/50">HTTP → HTTPS redirect</dt>
              <dd>{template.http_to_https_redirect_default ? "Recommended" : "Optional"}</dd>
            </div>
            {template.recommended_client_max_body_size ? (
              <div>
                <dt className="text-white/50">Recommended body size</dt>
                <dd>{template.recommended_client_max_body_size}</dd>
              </div>
            ) : null}
            {template.health_check_path ? (
              <div>
                <dt className="text-white/50">Health check path</dt>
                <dd>{template.health_check_path}</dd>
              </div>
            ) : null}
          </dl>

          {template.tags.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {template.tags.map((tag) => (
                <span key={tag} className="rounded bg-white/10 px-2 py-0.5 text-xs text-white/70">
                  {tag}
                </span>
              ))}
            </div>
          ) : null}

          {template.documentation_url ? (
            <a
              href={template.documentation_url}
              target="_blank"
              rel="noreferrer"
              className="inline-block text-sm text-accent hover:underline"
            >
              Official documentation →
            </a>
          ) : null}

          {template.security_notes ? (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
              {template.security_notes}
            </div>
          ) : null}
        </div>
      </Card>
    </div>
  );
}

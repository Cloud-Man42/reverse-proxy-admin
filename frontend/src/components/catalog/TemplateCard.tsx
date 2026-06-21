import { Link } from "react-router-dom";
import { ApplicationTemplate } from "../../types";
import { TemplateBadges } from "./TemplateBadges";

export function TemplateCard({ template }: { template: ApplicationTemplate }) {
  return (
    <div className="flex h-full flex-col rounded-lg border border-white/10 bg-black/20 p-4 transition hover:border-white/20">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div>
          <h3 className="text-lg font-medium">{template.name}</h3>
          <p className="text-xs text-white/50">{template.category}</p>
        </div>
      </div>
      <p className="mb-3 flex-1 text-sm text-white/60">{template.description || "No description."}</p>
      <div className="mb-4">
        <TemplateBadges template={template} />
      </div>
      <div className="flex gap-2">
        <Link
          to={`/templates/${encodeURIComponent(template.slug)}`}
          className="rounded-lg bg-white/10 px-3 py-2 text-sm hover:bg-white/15"
        >
          Details
        </Link>
        <Link
          to={`/templates/${encodeURIComponent(template.slug)}/wizard`}
          className="rounded-lg bg-accent px-3 py-2 text-sm text-white"
        >
          Use template
        </Link>
      </div>
    </div>
  );
}

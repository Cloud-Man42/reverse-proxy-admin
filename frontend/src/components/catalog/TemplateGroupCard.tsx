import { Link } from "react-router-dom";
import { TemplateGroup } from "../../types";

export function TemplateGroupCard({ group }: { group: TemplateGroup }) {
  return (
    <Link
      to={`/templates/groups/${encodeURIComponent(group.slug)}`}
      className="block rounded-xl border border-white/10 bg-black/20 p-5 transition hover:border-accent/40 hover:bg-black/30"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-lg font-semibold">{group.name}</h3>
        <span className="rounded bg-white/10 px-2 py-0.5 text-xs text-white/70">{group.template_count} apps</span>
      </div>
      <p className="text-sm text-white/60">{group.description}</p>
    </Link>
  );
}

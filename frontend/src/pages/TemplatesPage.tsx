import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Card } from "../components/Card";

export function TemplatesPage() {
  const { data = [], isLoading } = useQuery({ queryKey: ["templates"], queryFn: api.listTemplates });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Application Templates</h2>
          <p className="text-sm text-white/60">Start a new proxy with sensible defaults for common apps.</p>
        </div>
        <Link to="/proxies" className="rounded-lg bg-white/10 px-4 py-2 text-sm">
          Back to proxies
        </Link>
      </div>

      <Card>
        {isLoading ? (
          <p>Loading templates...</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.map((template) => (
              <div key={template.slug} className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="mb-2 flex items-start justify-between gap-2">
                  <h3 className="text-lg font-medium">{template.name}</h3>
                  {template.builtin ? (
                    <span className="rounded bg-white/10 px-2 py-0.5 text-xs text-white/70">Built-in</span>
                  ) : null}
                </div>
                <p className="mb-4 min-h-[3rem] text-sm text-white/60">{template.description || "No description."}</p>
                <Link
                  to={`/proxies/new?template=${encodeURIComponent(template.slug)}`}
                  className="inline-block rounded-lg bg-accent px-3 py-2 text-sm text-white"
                >
                  Use template
                </Link>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

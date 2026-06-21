import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { TemplateCard } from "../components/catalog/TemplateCard";
import { TemplateFilterSidebar } from "../components/catalog/TemplateFilterSidebar";
import { TemplateSearchBar } from "../components/catalog/TemplateSearchBar";
import { CatalogFilters } from "../types";

export function TemplateGroupPage() {
  const { groupSlug = "" } = useParams();
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<CatalogFilters>({ group: groupSlug, page_size: 100 });

  const queryFilters = useMemo(
    () => ({
      ...filters,
      group: groupSlug,
      q: search.trim() || undefined,
    }),
    [filters, groupSlug, search]
  );

  const { data: groups = [] } = useQuery({
    queryKey: ["template-groups"],
    queryFn: api.listTemplateGroups,
  });

  const group = groups.find((item) => item.slug === groupSlug);

  const { data: catalog, isLoading } = useQuery({
    queryKey: ["catalog-templates", queryFilters],
    queryFn: () => api.listCatalogTemplates(queryFilters),
    enabled: Boolean(groupSlug),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/templates" className="text-sm text-accent hover:underline">
            ← Application Catalog
          </Link>
          <h2 className="mt-1 text-2xl font-semibold">{group?.name || groupSlug}</h2>
          <p className="text-sm text-white/60">{group?.description || "Browse templates in this group."}</p>
        </div>
      </div>

      <Card>
        <div className="mb-4">
          <TemplateSearchBar value={search} onChange={setSearch} placeholder={`Search in ${group?.name || "group"}...`} />
        </div>
        <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
          <TemplateFilterSidebar
            filters={{ ...filters, group: groupSlug, q: search }}
            onChange={(next) => setFilters({ ...next, group: groupSlug, page_size: 100 })}
          />
          <div>
            {isLoading ? (
              <p>Loading templates...</p>
            ) : (
              <>
                <p className="mb-4 text-sm text-white/60">{catalog?.total ?? 0} templates</p>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {(catalog?.items ?? []).map((template) => (
                    <TemplateCard key={template.slug} template={template} />
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}

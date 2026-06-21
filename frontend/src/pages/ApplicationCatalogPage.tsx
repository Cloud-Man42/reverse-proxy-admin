import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { TemplateCard } from "../components/catalog/TemplateCard";
import { TemplateFilterSidebar } from "../components/catalog/TemplateFilterSidebar";
import { TemplateGroupCard } from "../components/catalog/TemplateGroupCard";
import { TemplateSearchBar } from "../components/catalog/TemplateSearchBar";
import { CatalogFilters } from "../types";

export function ApplicationCatalogPage() {
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<CatalogFilters>({ page_size: 100 });

  const queryFilters = useMemo(
    () => ({
      ...filters,
      q: search.trim() || undefined,
    }),
    [filters, search]
  );

  const showBrowseResults = Boolean(
    search.trim() ||
      filters.availability_level ||
      filters.optimized ||
      filters.websocket ||
      filters.large_upload ||
      filters.https_upstream
  );

  const { data: groups = [], isLoading: groupsLoading, isError: groupsError, error: groupsQueryError } = useQuery({
    queryKey: ["template-groups"],
    queryFn: api.listTemplateGroups,
  });

  const { data: catalog, isLoading: catalogLoading } = useQuery({
    queryKey: ["catalog-templates", queryFilters],
    queryFn: () => api.listCatalogTemplates(queryFilters),
    enabled: showBrowseResults,
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Application Catalog</h2>
          <p className="text-sm text-white/60">
            Browse 100+ self-hosted apps with optimized nginx presets and a guided setup wizard.
          </p>
        </div>
        <Link to="/proxies" className="rounded-lg bg-white/10 px-4 py-2 text-sm">
          Back to proxies
        </Link>
      </div>

      <Card>
        <div className="mb-4">
          <TemplateSearchBar value={search} onChange={setSearch} />
        </div>

        {showBrowseResults ? (
          <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
            <TemplateFilterSidebar
              filters={{ ...filters, q: search }}
              onChange={(next) => setFilters({ ...next, page_size: 100 })}
            />
            <div>
              {catalogLoading ? (
                <p>Searching catalog...</p>
              ) : (
                <>
                  <p className="mb-4 text-sm text-white/60">
                    {catalog?.total ?? 0} application{(catalog?.total ?? 0) === 1 ? "" : "s"} found
                  </p>
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {(catalog?.items ?? []).map((template) => (
                      <TemplateCard key={template.slug} template={template} />
                    ))}
                  </div>
                  {(catalog?.items.length ?? 0) === 0 ? (
                    <p className="text-sm text-white/60">No templates match your search or filters.</p>
                  ) : null}
                </>
              )}
            </div>
          </div>
        ) : groupsLoading ? (
          <p>Loading groups...</p>
        ) : groupsError ? (
          <p className="text-sm text-red-300">
            Could not load catalog groups
            {groupsQueryError instanceof Error ? `: ${groupsQueryError.message}` : "."} Try refreshing the page.
          </p>
        ) : groups.length === 0 ? (
          <p className="text-sm text-white/60">No catalog groups found.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {groups.map((group) => (
              <TemplateGroupCard key={group.slug} group={group} />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

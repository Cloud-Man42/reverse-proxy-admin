import { CatalogFilters, TemplateAvailabilityLevel } from "../../types";

interface TemplateFilterSidebarProps {
  filters: CatalogFilters;
  onChange: (filters: CatalogFilters) => void;
}

function ToggleFilter({
  label,
  checked,
  onToggle,
}: {
  label: string;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm text-white/80">
      <input type="checkbox" checked={checked} onChange={onToggle} className="rounded border-white/20 bg-black/20" />
      {label}
    </label>
  );
}

export function TemplateFilterSidebar({ filters, onChange }: TemplateFilterSidebarProps) {
  const setFlag = (key: keyof CatalogFilters, value: boolean | undefined) => {
    onChange({ ...filters, [key]: value });
  };

  const setAvailability = (level: TemplateAvailabilityLevel | undefined) => {
    onChange({ ...filters, availability_level: level });
  };

  const clearFilters = () => {
    onChange({ q: filters.q, group: filters.group });
  };

  const hasActiveFilters =
    filters.availability_level ||
    filters.optimized ||
    filters.websocket ||
    filters.large_upload ||
    filters.https_upstream;

  return (
    <aside className="space-y-4 rounded-xl border border-white/10 bg-black/20 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Filters</h3>
        {hasActiveFilters ? (
          <button type="button" onClick={clearFilters} className="text-xs text-accent hover:underline">
            Clear
          </button>
        ) : null}
      </div>

      <div className="space-y-2">
        <p className="text-xs uppercase tracking-wide text-white/50">Availability</p>
        {(["free", "pro", "enterprise"] as TemplateAvailabilityLevel[]).map((level) => (
          <label key={level} className="flex cursor-pointer items-center gap-2 text-sm capitalize text-white/80">
            <input
              type="radio"
              name="availability"
              checked={filters.availability_level === level}
              onChange={() => setAvailability(filters.availability_level === level ? undefined : level)}
            />
            {level}
          </label>
        ))}
      </div>

      <div className="space-y-2 border-t border-white/10 pt-4">
        <p className="text-xs uppercase tracking-wide text-white/50">Features</p>
        <ToggleFilter
          label="Optimized templates"
          checked={Boolean(filters.optimized)}
          onToggle={() => setFlag("optimized", filters.optimized ? undefined : true)}
        />
        <ToggleFilter
          label="WebSocket support"
          checked={Boolean(filters.websocket)}
          onToggle={() => setFlag("websocket", filters.websocket ? undefined : true)}
        />
        <ToggleFilter
          label="Large upload support"
          checked={Boolean(filters.large_upload)}
          onToggle={() => setFlag("large_upload", filters.large_upload ? undefined : true)}
        />
        <ToggleFilter
          label="HTTPS upstream"
          checked={Boolean(filters.https_upstream)}
          onToggle={() => setFlag("https_upstream", filters.https_upstream ? undefined : true)}
        />
      </div>
    </aside>
  );
}

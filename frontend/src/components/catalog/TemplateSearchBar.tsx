interface TemplateSearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function TemplateSearchBar({ value, onChange, placeholder = "Search applications..." }: TemplateSearchBarProps) {
  return (
    <div className="relative">
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-white/10 bg-black/20 px-4 py-2.5 text-sm outline-none ring-accent focus:ring-1"
      />
    </div>
  );
}

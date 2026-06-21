interface NginxConfigPreviewProps {
  config: string;
  warnings?: string[];
  loading?: boolean;
}

export function NginxConfigPreview({ config, warnings = [], loading }: NginxConfigPreviewProps) {
  if (loading) {
    return <p className="text-sm text-white/60">Generating preview...</p>;
  }

  return (
    <div className="space-y-3">
      {warnings.length > 0 ? (
        <ul className="space-y-1 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
          {warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
      <pre className="max-h-[32rem] overflow-auto rounded-lg border border-white/10 bg-black/40 p-4 text-xs leading-relaxed text-emerald-100">
        {config || "No configuration generated yet."}
      </pre>
    </div>
  );
}

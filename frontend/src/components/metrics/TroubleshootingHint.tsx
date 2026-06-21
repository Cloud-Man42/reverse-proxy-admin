interface TroubleshootingHintProps {
  title: string;
  message: string;
}

export function TroubleshootingHint({ title, message }: TroubleshootingHintProps) {
  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
      <p className="text-sm font-medium text-amber-200">{title}</p>
      <p className="mt-1 text-sm text-white/70">{message}</p>
    </div>
  );
}

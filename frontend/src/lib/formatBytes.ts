export function formatBytes(value: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let amount = value;
  for (const unit of units) {
    if (amount < 1024 || unit === units[units.length - 1]) {
      if (unit === "B") return `${Math.round(amount)} ${unit}`;
      return `${amount.toFixed(1)} ${unit}`;
    }
    amount /= 1024;
  }
  return `${value} B`;
}

import { useEffect, useState } from "react";

export function useAutoRefresh(enabled: boolean, intervalMs: number, callback: () => void) {
  useEffect(() => {
    if (!enabled) return;
    const id = window.setInterval(callback, intervalMs);
    return () => window.clearInterval(id);
  }, [enabled, intervalMs, callback]);
}

export function useTheme() {
  const [dark, setDark] = useState(() => localStorage.getItem("theme") !== "light");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  return { dark, toggle: () => setDark((v) => !v) };
}

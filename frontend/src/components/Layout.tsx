import { NavLink, Outlet } from "react-router-dom";
import { APP_NAME, APP_TAGLINE } from "../lib/branding";
import { useAuth } from "../hooks/useAuth";
import { useTheme } from "../hooks/useAutoRefresh";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/proxies", label: "Proxy Apps" },
  { to: "/templates", label: "Templates" },
  { to: "/backend-pools", label: "Backend Pools" },
  { to: "/health", label: "Health" },
  { to: "/analytics/traffic", label: "Analytics" },
  { to: "/observability/live", label: "Live Requests" },
  { to: "/alerts", label: "Alerts" },
  { to: "/certificates", label: "Certificates" },
  { to: "/logs", label: "Logs" },
  { to: "/system", label: "System" },
  { to: "/settings", label: "Settings", adminOnly: true },
  { to: "/settings/metrics", label: "Metrics", adminOnly: true },
  { to: "/security", label: "Security", adminOnly: true },
  { to: "/security/overview", label: "Security Overview", adminOnly: true },
  { to: "/audit", label: "Audit", adminOnly: true },
  { to: "/api-tokens", label: "API Tokens", adminOnly: true },
  { to: "/about", label: "About" },
  { to: "/users", label: "Users", adminOnly: true },
  { to: "/tenants", label: "Tenants", superAdminOnly: true },
];

export function Layout() {
  const { username, logout, isAdmin, isSuperAdmin } = useAuth();
  const { dark, toggle } = useTheme();

  return (
    <div className="min-h-screen bg-surface text-content">
      <header className="border-b border-white/10 bg-surface-muted">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-xl font-bold">{APP_NAME}</h1>
            <p className="text-sm text-white/60">{APP_TAGLINE}</p>
          </div>
          <div className="flex items-center gap-3">
            <button className="rounded-lg px-3 py-2 text-sm hover:bg-white/10" onClick={toggle}>
              {dark ? "Light" : "Dark"}
            </button>
            <span className="text-sm text-white/70">{username}</span>
            <button className="rounded-lg bg-white/10 px-3 py-2 text-sm hover:bg-white/20" onClick={() => logout()}>
              Logout
            </button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-2 overflow-x-auto px-4 pb-3">
          {links
            .filter((link) => {
              if (link.superAdminOnly) return isSuperAdmin;
              if (link.adminOnly) return isAdmin;
              return true;
            })
            .map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm ${isActive ? "bg-accent text-white" : "hover:bg-white/10"}`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

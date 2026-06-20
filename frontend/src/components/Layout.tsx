import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useTheme } from "../hooks/useAutoRefresh";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/proxies", label: "Proxy Apps" },
  { to: "/backend-pools", label: "Backend Pools" },
  { to: "/health", label: "Health" },
  { to: "/certificates", label: "Certificates" },
  { to: "/logs", label: "Logs" },
  { to: "/system", label: "System" },
  { to: "/settings", label: "Settings", adminOnly: true },
  { to: "/about", label: "About" },
  { to: "/users", label: "Users", adminOnly: true },
];
export function Layout() {
  const { username, logout, isAdmin } = useAuth();
  const { dark, toggle } = useTheme();

  return (
    <div className="min-h-screen bg-surface text-content">
      <header className="border-b border-white/10 bg-surface-muted">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
          <div>
            <p className="text-sm text-white/60">Reverse Proxy Admin</p>
            <h1 className="text-xl font-bold">Nginx Control Panel</h1>
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
            .filter((link) => !link.adminOnly || isAdmin)
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

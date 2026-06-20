import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { useAuth } from "./hooks/useAuth";
import { ApiTokensPage } from "./pages/ApiTokensPage";
import { AuditPage } from "./pages/AuditPage";
import { AboutPage } from "./pages/AboutPage";
import { BackendPoolsPage } from "./pages/BackendPoolsPage";
import { CertificatesPage } from "./pages/CertificatesPage";
import { ConfigHistoryPage } from "./pages/ConfigHistoryPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HealthMonitoringPage } from "./pages/HealthMonitoringPage";
import { LoginPage } from "./pages/LoginPage";
import { LogsPage } from "./pages/LogsPage";
import { ProxiesPage } from "./pages/ProxiesPage";
import { ProxyFormPage } from "./pages/ProxyFormPage";
import { SecurityPage } from "./pages/SecurityPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SystemPage } from "./pages/SystemPage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { TenantsPage } from "./pages/TenantsPage";
import { TrafficStatsPage } from "./pages/TrafficStatsPage";
import { UsersPage } from "./pages/UsersPage";

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { username, loading } = useAuth();
  if (loading) return <div className="flex min-h-screen items-center justify-center">Loading...</div>;
  if (!username) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/proxies" element={<ProxiesPage />} />
        <Route path="/proxies/new" element={<ProxyFormPage />} />
        <Route path="/proxies/:id/edit" element={<ProxyFormPage />} />
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/config-history" element={<ConfigHistoryPage />} />
        <Route path="/backend-pools" element={<BackendPoolsPage />} />
        <Route path="/health" element={<HealthMonitoringPage />} />
        <Route path="/analytics" element={<TrafficStatsPage />} />
        <Route path="/traffic" element={<Navigate to="/analytics" replace />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/security" element={<SecurityPage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/api-tokens" element={<ApiTokensPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/certificates" element={<CertificatesPage />} />
        <Route path="/logs" element={<LogsPage />} />
        <Route path="/system" element={<SystemPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/tenants" element={<TenantsPage />} />
      </Route>
    </Routes>
  );
}

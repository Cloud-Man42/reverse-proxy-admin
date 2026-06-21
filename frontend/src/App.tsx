import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";

import { useAuth } from "./hooks/useAuth";

import { AlertsPage } from "./pages/AlertsPage";

import { ApiTokensPage } from "./pages/ApiTokensPage";

import { AuditPage } from "./pages/AuditPage";

import { AboutPage } from "./pages/AboutPage";

import { BackendAnalyticsPage } from "./pages/BackendAnalyticsPage";

import { BackendPoolsPage } from "./pages/BackendPoolsPage";

import { CertificatesPage } from "./pages/CertificatesPage";

import { ConfigHistoryPage } from "./pages/ConfigHistoryPage";

import { ConnectionStatsPage } from "./pages/ConnectionStatsPage";

import { DashboardPage } from "./pages/DashboardPage";

import { FailedRequestsPage } from "./pages/FailedRequestsPage";

import { HealthMonitoringPage } from "./pages/HealthMonitoringPage";

import { LiveRequestsPage } from "./pages/LiveRequestsPage";

import { LoginPage } from "./pages/LoginPage";

import { LogsPage } from "./pages/LogsPage";

import { MetricsSettingsPage } from "./pages/MetricsSettingsPage";

import { ProxiesPage } from "./pages/ProxiesPage";

import { ProxyFormPage } from "./pages/ProxyFormPage";

import { ProxyHostAnalyticsPage } from "./pages/ProxyHostAnalyticsPage";

import { SecurityOverviewPage } from "./pages/SecurityOverviewPage";

import { SecurityPage } from "./pages/SecurityPage";

import { SettingsPage } from "./pages/SettingsPage";

import { SslStatisticsPage } from "./pages/SslStatisticsPage";

import { StatusCodeAnalyticsPage } from "./pages/StatusCodeAnalyticsPage";

import { SystemPage } from "./pages/SystemPage";

import { TemplatesPage } from "./pages/TemplatesPage";

import { ApplicationCatalogPage } from "./pages/ApplicationCatalogPage";

import { TemplateGroupPage } from "./pages/TemplateGroupPage";

import { TemplateDetailPage } from "./pages/TemplateDetailPage";

import { TemplateWizardPage } from "./pages/TemplateWizardPage";

import { TenantsPage } from "./pages/TenantsPage";

import { TopClientIpsPage } from "./pages/TopClientIpsPage";

import { TrafficAnalyticsPage } from "./pages/TrafficAnalyticsPage";

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

        <Route path="/templates" element={<ApplicationCatalogPage />} />

        <Route path="/templates/groups/:groupSlug" element={<TemplateGroupPage />} />

        <Route path="/templates/:slug/wizard" element={<TemplateWizardPage />} />

        <Route path="/templates/:slug" element={<TemplateDetailPage />} />

        <Route path="/templates-legacy" element={<TemplatesPage />} />

        <Route path="/config-history" element={<ConfigHistoryPage />} />

        <Route path="/backend-pools" element={<BackendPoolsPage />} />

        <Route path="/health" element={<HealthMonitoringPage />} />

        <Route path="/analytics" element={<Navigate to="/analytics/traffic" replace />} />

        <Route path="/analytics/traffic" element={<TrafficAnalyticsPage />} />

        <Route path="/analytics/status-codes" element={<StatusCodeAnalyticsPage />} />

        <Route path="/analytics/proxy-hosts" element={<ProxyHostAnalyticsPage />} />

        <Route path="/analytics/client-ips" element={<TopClientIpsPage />} />

        <Route path="/analytics/backends" element={<BackendAnalyticsPage />} />

        <Route path="/analytics/connections" element={<ConnectionStatsPage />} />

        <Route path="/analytics/ssl" element={<SslStatisticsPage />} />

        <Route path="/analytics/legacy" element={<TrafficStatsPage />} />

        <Route path="/traffic" element={<Navigate to="/analytics/traffic" replace />} />

        <Route path="/security/overview" element={<SecurityOverviewPage />} />

        <Route path="/observability/live" element={<LiveRequestsPage />} />

        <Route path="/observability/failed" element={<FailedRequestsPage />} />

        <Route path="/alerts" element={<AlertsPage />} />

        <Route path="/settings/metrics" element={<MetricsSettingsPage />} />

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



import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { useAuth } from "./hooks/useAuth";
import { CertificatesPage } from "./pages/CertificatesPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { LogsPage } from "./pages/LogsPage";
import { ProxiesPage } from "./pages/ProxiesPage";
import { ProxyFormPage } from "./pages/ProxyFormPage";
import { SystemPage } from "./pages/SystemPage";
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
        <Route path="/certificates" element={<CertificatesPage />} />
        <Route path="/logs" element={<LogsPage />} />
        <Route path="/system" element={<SystemPage />} />
        <Route path="/users" element={<UsersPage />} />
      </Route>
    </Routes>
  );
}

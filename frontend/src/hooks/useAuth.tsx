import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from "react";
import { api, setCsrfToken } from "../api/client";
import { UserPermissions } from "../types";

interface AuthContextValue {
  username: string | null;
  permissions: UserPermissions | null;
  organizationId: number | null;
  role: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  canRead: boolean;
  canCreate: boolean;
  canEdit: boolean;
  isAdmin: boolean;
  isSuperAdmin: boolean;
}

const defaultPermissions: UserPermissions = {
  is_admin: false,
  read: false,
  create: false,
  edit: false,
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function applySession(
  setUsername: (v: string | null) => void,
  setPermissions: (v: UserPermissions | null) => void,
  setOrganizationId: (v: number | null) => void,
  setRole: (v: string | null) => void,
  username: string | null,
  permissions: UserPermissions | null,
  organizationId: number | null,
  role: string | null,
  csrfToken: string | null,
) {
  setUsername(username);
  setPermissions(permissions);
  setOrganizationId(organizationId);
  setRole(role);
  setCsrfToken(csrfToken);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<UserPermissions | null>(null);
  const [organizationId, setOrganizationId] = useState<number | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const me = await api.me();
      applySession(
        setUsername,
        setPermissions,
        setOrganizationId,
        setRole,
        me.username,
        me.permissions,
        me.organization_id ?? null,
        me.role ?? null,
        me.csrf_token,
      );
    } catch {
      applySession(setUsername, setPermissions, setOrganizationId, setRole, null, null, null, null, null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const perms = permissions || defaultPermissions;

  const value = useMemo(
    () => ({
      username,
      permissions,
      organizationId,
      role,
      loading,
      refresh,
      canRead: perms.read,
      canCreate: perms.create,
      canEdit: perms.edit,
      isAdmin: perms.is_admin,
      isSuperAdmin: role === "super_admin",
      login: async (user: string, password: string) => {
        const result = await api.login(user, password);
        applySession(
          setUsername,
          setPermissions,
          setOrganizationId,
          setRole,
          result.username,
          result.permissions,
          result.organization_id ?? null,
          result.role ?? null,
          result.csrf_token,
        );
      },
      logout: async () => {
        await api.logout();
        applySession(setUsername, setPermissions, setOrganizationId, setRole, null, null, null, null, null);
      },
    }),
    [username, permissions, organizationId, role, loading, perms.read, perms.create, perms.edit, perms.is_admin],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

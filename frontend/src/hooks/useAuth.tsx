import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from "react";
import { api, setCsrfToken } from "../api/client";
import { UserPermissions } from "../types";

interface AuthContextValue {
  username: string | null;
  permissions: UserPermissions | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  canRead: boolean;
  canCreate: boolean;
  canEdit: boolean;
  isAdmin: boolean;
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
  username: string | null,
  permissions: UserPermissions | null,
  csrfToken: string | null,
) {
  setUsername(username);
  setPermissions(permissions);
  setCsrfToken(csrfToken);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<UserPermissions | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const me = await api.me();
      applySession(setUsername, setPermissions, me.username, me.permissions, me.csrf_token);
    } catch {
      applySession(setUsername, setPermissions, null, null, null);
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
      loading,
      refresh,
      canRead: perms.read,
      canCreate: perms.create,
      canEdit: perms.edit,
      isAdmin: perms.is_admin,
      login: async (user: string, password: string) => {
        const result = await api.login(user, password);
        applySession(setUsername, setPermissions, result.username, result.permissions, result.csrf_token);
      },
      logout: async () => {
        await api.logout();
        applySession(setUsername, setPermissions, null, null, null);
      },
    }),
    [username, permissions, loading, perms.read, perms.create, perms.edit, perms.is_admin],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

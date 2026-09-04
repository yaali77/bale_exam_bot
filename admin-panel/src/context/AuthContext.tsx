import React, { createContext, useContext, useEffect, useState } from "react";
import { api, setToken, clearToken } from "../api/client";

interface AdminProfile {
  id: string;
  username: string;
  full_name: string;
  role: string;
}

interface AuthContextValue {
  admin: AdminProfile | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
}

const ROLE_PERMISSIONS: Record<string, string[]> = {
  super_admin: ["view", "create", "edit", "delete", "publish", "report", "settings"],
  system_manager: ["view", "create", "edit", "delete", "publish", "report", "settings"],
  exam_manager: ["view", "create", "edit", "publish", "report"],
  score_operator: ["view", "create", "edit"],
  user_operator: ["view", "create", "edit"],
  support: ["view", "report"],
  observer: ["view"],
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [admin, setAdmin] = useState<AdminProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get<AdminProfile>("/api/admins/me")
      .then(setAdmin)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  async function login(username: string, password: string) {
    const res = await api.post<{ access_token: string }>("/api/auth/login", { username, password });
    setToken(res.access_token);
    const profile = await api.get<AdminProfile>("/api/admins/me");
    setAdmin(profile);
  }

  function logout() {
    clearToken();
    setAdmin(null);
    window.location.href = "/login";
  }

  function hasPermission(permission: string) {
    if (!admin) return false;
    return ROLE_PERMISSIONS[admin.role]?.includes(permission) ?? false;
  }

  return (
    <AuthContext.Provider value={{ admin, loading, login, logout, hasPermission }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth باید داخل AuthProvider استفاده شود");
  return ctx;
}

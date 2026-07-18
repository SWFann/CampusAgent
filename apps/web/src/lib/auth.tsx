"use client";

import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from "react";
import type { User } from "./api/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({
  user: null,
  loading: true,
  error: null,
  refresh: async () => {},
  logout: async () => {},
});

export function useAuth(): AuthState {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/auth/me`, {
        method: "GET",
        credentials: "include",
      });
      if (resp.status === 401) {
        setUser(null);
        return;
      }
      const body = await resp.json();
      if (body.success) {
        setUser(body.data);
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Ignore errors on logout
    }
    setUser(null);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <AuthContext.Provider value={{ user, loading, error, refresh, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

/** Check if the current user has admin role. */
export function useIsAdmin(): boolean {
  const { user } = useAuth();
  if (!user) return false;
  const role = user.global_role.toUpperCase();
  return role === "SYSTEM_ADMIN" || role === "ADMIN" || role === "SUPER_ADMIN";
}

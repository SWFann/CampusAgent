"use client";

import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { LoadingState } from "@/components/ui/LoadingState";

/**
 * Route guard component.
 * Redirects to /login if not authenticated.
 * Shows forbidden state，用途：403 errors.
 */
export function RouteGuard({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return <LoadingState message="正在检查登录状态..." />;
  }

  if (!user) {
    return (
      <div style={{ padding: "var(--space-2xl)", textAlign: "center" }}>
        <p style={{ color: "var(--color-text-secondary)" }}>
          正在跳转到登录页...
        </p>
      </div>
    );
  }

  return <>{children}</>;
}

/**
 * Admin route guard.
 * Shows forbidden state，用途：non-admin users.
 */
export function AdminGuard({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingState message="正在检查权限..." />;
  }

  if (!user) {
    return (
      <div style={{ padding: "var(--space-2xl)", textAlign: "center" }}>
        <p style={{ color: "var(--color-text-secondary)" }}>正在跳转到登录页...</p>
      </div>
    );
  }

  const role = user.global_role.toUpperCase();
  const isAdmin = role === "SYSTEM_ADMIN" || role === "ADMIN" || role === "SUPER_ADMIN";

  if (!isAdmin) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "var(--space-2xl)",
          gap: "var(--space-sm)",
        }}
        role="alert"
      >
        <div style={{ color: "var(--color-danger)", fontSize: 32 }} aria-hidden="true">
          &#9888;
        </div>
        <p style={{ fontWeight: "var(--font-weight-semibold)", color: "var(--color-danger)" }}>
          无权访问
        </p>
        <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
          你没有权限访问此页面。
        </p>
      </div>
    );
  }

  return <>{children}</>;
}

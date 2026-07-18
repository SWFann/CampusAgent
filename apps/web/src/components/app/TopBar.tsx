"use client";

import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { StatusBadge } from "@/components/ui/StatusBadge";

export function TopBar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "var(--space-sm) var(--space-lg)",
        borderBottom: "1px solid var(--color-border)",
        background: "var(--color-surface)",
        minHeight: 48,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-md)" }}>
        {user && (
          <>
            <span style={{ fontSize: "var(--font-size-sm)", fontWeight: "var(--font-weight-medium)" }}>
              {user.display_name}
            </span>
            {user.global_role && (
              <StatusBadge
                label={user.global_role}
                variant={user.global_role.toUpperCase().includes("ADMIN") ? "danger" : "info"}
              />
            )}
          </>
        )}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-md)" }}>
        <button
          className="btn btn-sm"
          onClick={handleLogout}
          aria-label="退出登录"
        >
          退出登录
        </button>
      </div>
    </header>
  );
}

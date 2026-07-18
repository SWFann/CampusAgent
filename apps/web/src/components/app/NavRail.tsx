"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth, useIsAdmin } from "@/lib/auth";

interface NavItem {
  href: string;
  label: string;
  icon: string;
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "首页", icon: "🏠" },
  { href: "/conversations", label: "消息", icon: "💬" },
  { href: "/contacts", label: "联系人", icon: "👥" },
  { href: "/organizations", label: "组织", icon: "🏫" },
  { href: "/agents", label: "智能体", icon: "🤖" },
  { href: "/memory", label: "记忆中心", icon: "🧠" },
  { href: "/scenes", label: "场景", icon: "🍽️" },
  { href: "/preferences/private", label: "私密偏好", icon: "🔒" },
  { href: "/admin", label: "管理", icon: "⚙️", adminOnly: true },
];

export function NavRail() {
  const pathname = usePathname();
  const { user } = useAuth();
  const isAdmin = useIsAdmin();

  const items = NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin);

  return (
    <nav
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-xs)",
        padding: "var(--space-md)",
        width: 200,
        minHeight: "100vh",
        borderRight: "1px solid var(--color-border)",
        background: "var(--color-surface)",
      }}
      aria-label="主导航"
    >
      <div style={{ padding: "var(--space-sm) var(--space-md)", marginBottom: "var(--space-md)" }}>
        <strong style={{ fontSize: "var(--font-size-lg)" }}>校园智能体</strong>
      </div>
      {items.map((item) => {
        const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
        return (
          <Link
            key={item.href}
            href={item.href}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-sm)",
              padding: "var(--space-sm) var(--space-md)",
              borderRadius: "var(--radius-md)",
              textDecoration: "none",
              fontSize: "var(--font-size-sm)",
              fontWeight: isActive ? "var(--font-weight-semibold)" : "var(--font-weight-normal)",
              color: isActive ? "var(--color-primary)" : "var(--color-text-secondary)",
              background: isActive ? "var(--color-primary-light)" : "transparent",
              transition: "all var(--transition-fast)",
            }}
            aria-current={isActive ? "page" : undefined}
          >
            <span aria-hidden="true">{item.icon}</span>
            {item.label}
          </Link>
        );
      })}
      {user && (
        <div style={{ marginTop: "auto", padding: "var(--space-sm) var(--space-md)" }}>
          <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
            当前登录
          </span>
          <p style={{ fontSize: "var(--font-size-sm)", fontWeight: "var(--font-weight-medium)" }}>
            {user.display_name}
          </p>
        </div>
      )}
    </nav>
  );
}

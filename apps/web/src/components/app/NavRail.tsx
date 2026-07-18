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
  { href: "/", label: "Home", icon: "🏠" },
  { href: "/messages", label: "Messages", icon: "💬" },
  { href: "/organizations", label: "Organizations", icon: "🏫" },
  { href: "/agents", label: "Agents", icon: "🤖" },
  { href: "/memory", label: "Memory", icon: "🧠" },
  { href: "/scenes", label: "Scenes", icon: "🍽️" },
  { href: "/preferences/private", label: "Private Prefs", icon: "🔒" },
  { href: "/admin", label: "Admin", icon: "⚙️", adminOnly: true },
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
      aria-label="Main navigation"
    >
      <div style={{ padding: "var(--space-sm) var(--space-md)", marginBottom: "var(--space-md)" }}>
        <strong style={{ fontSize: "var(--font-size-lg)" }}>CampusAgent</strong>
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
            Signed in as
          </span>
          <p style={{ fontSize: "var(--font-size-sm)", fontWeight: "var(--font-weight-medium)" }}>
            {user.display_name}
          </p>
        </div>
      )}
    </nav>
  );
}

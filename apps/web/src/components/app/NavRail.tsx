"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth, useIsAdmin } from "@/lib/auth";

interface NavItem {
  href: string;
  label: string;
  icon: NavIconName;
  adminOnly?: boolean;
}

type NavIconName = "home" | "workspace" | "message" | "service" | "agent" | "scene" | "privacy" | "settings";

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "首页", icon: "home" },
  { href: "/conversations", label: "消息与通知", icon: "message" },
  { href: "/workspace", label: "个人工作台", icon: "workspace" },
  { href: "/organizations", label: "组织与群体", icon: "service" },
  { href: "/scenes", label: "协作空间", icon: "scene" },
  { href: "/agents", label: "我的 Agent", icon: "agent" },
  { href: "/memory", label: "个人知识库", icon: "privacy" },
  { href: "/admin", label: "管理", icon: "settings", adminOnly: true },
];

function NavIcon({ name }: { name: NavIconName }) {
  const paths: Record<NavIconName, ReactNode> = {
    home: <><path d="M3.5 9.2 10 3.8l6.5 5.4" /><path d="M5.5 8.2v8h9v-8M8.2 16.2v-5h3.6v5" /></>,
    workspace: <><path d="M3.5 4.5h13v9H9l-4.5 3v-3h-1z" /><path d="m9.5 6.5.6 2.2 2.2.6-2.2.7-.6 2.2-.6-2.2-2.2-.7 2.2-.6z" /></>,
    message: <><path d="M4 4.5h12v9H9l-4.5 3v-3H4z" /><path d="M7 8h6M7 10.5h4" /></>,
    service: <><path d="M4 16.5V6.8L10 3l6 3.8v9.7M2.8 16.5h14.4" /><path d="M7 8.5h1M12 8.5h1M7 11.5h1M12 11.5h1M9 16.5v-3h2v3" /></>,
    agent: <><circle cx="10" cy="10.5" r="6" /><path d="M7.5 10h.1M12.4 10h.1M7.8 13c1.4 1 3 1 4.4 0M10 2v2.5M6 3.2l1.2 2" /></>,
    scene: <><rect x="3.5" y="3.5" width="5" height="5" rx="1" /><rect x="11.5" y="3.5" width="5" height="5" rx="1" /><rect x="3.5" y="11.5" width="5" height="5" rx="1" /><rect x="11.5" y="11.5" width="5" height="5" rx="1" /></>,
    privacy: <><path d="M10 2.8 16 5v4.8c0 3.5-2.1 6-6 7.5-3.9-1.5-6-4-6-7.5V5z" /><path d="m7.3 10 1.8 1.8 3.8-4" /></>,
    settings: <><path d="M8.4 2.8h3.2l.5 2c.5.2.9.4 1.3.8l2-.6L17 7.7l-1.5 1.5a5.8 5.8 0 0 1 0 1.6l1.5 1.5-1.6 2.7-2-.6c-.4.4-.8.6-1.3.8l-.5 2H8.4l-.5-2c-.5-.2-.9-.4-1.3-.8l-2 .6L3 12.3l1.5-1.5a5.8 5.8 0 0 1 0-1.6L3 7.7 4.6 5l2 .6c.4-.4.8-.6 1.3-.8z" /><circle cx="10" cy="10" r="2.3" /></>,
  };
  return <svg className="campus-nav-icon" viewBox="0 0 20 20" aria-hidden="true">{paths[name]}</svg>;
}

export function NavRail() {
  const pathname = usePathname();
  const { user } = useAuth();
  const isAdmin = useIsAdmin();

  const items = NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin);

  return (
    <nav className="campus-nav-rail" aria-label="主导航">
      <div className="campus-nav-brand">
        <Image
          src="/brand/jinan-university-logo.png"
          alt="暨南大学"
          width={924}
          height={297}
          priority
          className="campus-nav-logo"
        />
        <span>CampusAgent</span>
      </div>
      <p className="campus-nav-section-label">我的校园</p>
      <div className="campus-nav-list">
      {items.map((item) => {
        const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`campus-nav-link${isActive ? " is-active" : ""}`}
            aria-current={isActive ? "page" : undefined}
          >
            <NavIcon name={item.icon} />
            <span>{item.label}</span>
          </Link>
        );
      })}
        <Link
          href="/settings"
          className={`campus-nav-link campus-mobile-settings${pathname.startsWith("/settings") ? " is-active" : ""}`}
          aria-current={pathname.startsWith("/settings") ? "page" : undefined}
        >
          <NavIcon name="settings" />
          <span>设置与安全</span>
        </Link>
      </div>
      {user && (
        <div className="campus-nav-user">
          <span className="campus-user-avatar" aria-hidden="true">{user.display_name.slice(0, 1)}</span>
          <span className="campus-nav-user-copy"><small>当前登录</small><strong>{user.display_name}</strong></span>
          <Link
            href="/settings"
            className={`campus-user-settings${pathname.startsWith("/settings") ? " is-active" : ""}`}
            aria-label="设置与安全"
            title="设置与安全"
          >
            <NavIcon name="settings" />
          </Link>
        </div>
      )}
    </nav>
  );
}

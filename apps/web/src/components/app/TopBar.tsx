"use client";

import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import { StatusBadge } from "@/components/ui/StatusBadge";

export function TopBar() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const sectionTitle = pathname === "/"
    ? "首页"
    : pathname.startsWith("/workspace/tasks")
      ? "Agent 任务"
    : pathname.startsWith("/workspace")
      ? "个人工作台"
    : pathname.startsWith("/conversations")
      ? "消息与通知"
      : pathname.startsWith("/organizations") || pathname.startsWith("/contacts")
        ? "组织与群体"
        : pathname.startsWith("/scenes")
          ? "协作空间"
          : pathname.startsWith("/agents")
            ? "我的 Agent"
            : pathname.startsWith("/memory") || pathname.startsWith("/preferences")
              ? "个人知识库"
              : pathname.startsWith("/settings")
                ? "设置与安全"
              : pathname.startsWith("/admin")
                ? "管理"
                : "校园工作台";

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <header className="campus-topbar">
      <div className="campus-window-controls" aria-hidden="true"><span /><span /><span /></div>
      <div className="campus-topbar-title">
        <strong>{sectionTitle}</strong>
      </div>
      <div className="campus-topbar-actions">
        <span className="campus-service-state"><i aria-hidden="true" />服务正常</span>
        {user && (
          <div className="campus-topbar-profile">
            <span>
              {user.display_name}
            </span>
            {user.global_role && (
              <StatusBadge
                label={user.global_role}
                variant={user.global_role.toUpperCase().includes("ADMIN") ? "danger" : "info"}
              />
            )}
          </div>
        )}
        <button
          className="campus-logout-button"
          onClick={handleLogout}
          aria-label="退出登录"
        >
          <span>退出</span><i aria-hidden="true">↗</i>
        </button>
      </div>
    </header>
  );
}

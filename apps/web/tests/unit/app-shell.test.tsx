/**
 * Tests for AppShell, RouteGuard, and NavRail components.
 */

import { render, screen } from "@testing-library/react";
import { usePathname } from "next/navigation";
import { NavRail } from "@/components/app/NavRail";
import { AuthProvider, useAuth } from "@/lib/auth";

// Mock next/navigation
jest.mock("next/navigation", () => ({
  usePathname: jest.fn(),
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

// Mock fetch
global.fetch = jest.fn() as jest.MockedFunction<typeof fetch>;

function mockAuthContext(user: { id: string; email: string; display_name: string; global_role: string } | null) {
  (global.fetch as jest.Mock).mockResolvedValue({
    status: user ? 200 : 401,
    json: async () =>
      user
        ? { success: true, data: user }
        : { success: false, error: { code: "UNAUTHORIZED", message: "Not logged in" } },
  });
}

describe("NavRail", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (usePathname as jest.Mock).mockReturnValue("/");
  });

  it("shows admin entry for admin users", async () => {
    mockAuthContext({
      id: "1",
      email: "admin@test.com",
      display_name: "Admin User",
      global_role: "SYSTEM_ADMIN",
    });

    const { container } = render(
      <AuthProvider>
        <NavRail />
      </AuthProvider>,
    );

    // Wait for auth to load and admin link to appear
    await screen.findByText("管理");

    // Admin link should be visible
    expect(screen.getByText("管理")).toBeInTheDocument();
  });

  it("hides admin entry for regular users", async () => {
    mockAuthContext({
      id: "2",
      email: "user@test.com",
      display_name: "Regular User",
      global_role: "USER",
    });

    render(
      <AuthProvider>
        <NavRail />
      </AuthProvider>,
    );

    // Wait for auth to load
    await screen.findByText("首页");

    // Admin link should NOT be visible
    expect(screen.queryByText("管理")).not.toBeInTheDocument();
  });

  it("shows all non-admin nav items", async () => {
    mockAuthContext({
      id: "3",
      email: "user@test.com",
      display_name: "Test User",
      global_role: "USER",
    });

    render(
      <AuthProvider>
        <NavRail />
      </AuthProvider>,
    );

    await screen.findByText("首页");
    expect(screen.getByText("个人工作台")).toBeInTheDocument();
    expect(screen.getByText("消息与通知")).toBeInTheDocument();
    expect(screen.getByText("组织与群体")).toBeInTheDocument();
    expect(screen.getByText("协作空间")).toBeInTheDocument();
    expect(screen.getByText("我的 Agent")).toBeInTheDocument();
    expect(screen.getByText("个人知识库")).toBeInTheDocument();
  });

  it("does not render token in the DOM", async () => {
    mockAuthContext({
      id: "4",
      email: "user@test.com",
      display_name: "Test User",
      global_role: "USER",
    });

    const { container } = render(
      <AuthProvider>
        <NavRail />
      </AuthProvider>,
    );

    await screen.findByText("首页");
    // No token-related strings in the DOM
    expect(container.textContent).not.toContain("access_token");
    expect(container.textContent).not.toContain("refresh_token");
    expect(container.textContent).not.toContain("csrf_token");
  });
});

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

    // Wait for auth to load and Admin link to appear
    await screen.findByText("Admin");

    // Admin link should be visible
    expect(screen.getByText("Admin")).toBeInTheDocument();
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
    await screen.findByText("Home");

    // Admin link should NOT be visible
    expect(screen.queryByText("Admin")).not.toBeInTheDocument();
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

    await screen.findByText("Home");
    expect(screen.getByText("Messages")).toBeInTheDocument();
    expect(screen.getByText("Organizations")).toBeInTheDocument();
    expect(screen.getByText("Agents")).toBeInTheDocument();
    expect(screen.getByText("Memory")).toBeInTheDocument();
    expect(screen.getByText("Scenes")).toBeInTheDocument();
    expect(screen.getByText("Private Prefs")).toBeInTheDocument();
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

    await screen.findByText("Home");
    // No token-related strings in the DOM
    expect(container.textContent).not.toContain("access_token");
    expect(container.textContent).not.toContain("refresh_token");
    expect(container.textContent).not.toContain("csrf_token");
  });
});

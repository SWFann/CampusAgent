/**
 * P11-05: Integration tests for the demo account picker on the login page.
 *
 * Verifies:
 * - The demo picker appears in the test (non-production) environment.
 * - Clicking a demo account fills the email input.
 * - Clicking a loginable demo account fills the password input too.
 * - The demo password is NEVER written to localStorage or sessionStorage.
 * - The deleted demo account does not fill the password.
 * - Login still calls the real /api/v1/auth/login endpoint.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LoginPage from "@/app/login/page";

// Mock next/navigation
jest.mock("next/navigation", () => ({
  useRouter() {
    return { push: jest.fn() };
  },
}));

// Mock fetch
global.fetch = jest.fn() as jest.MockedFunction<typeof fetch>;

function mockLoginSuccess() {
  (global.fetch as jest.Mock).mockImplementation((url: string) => {
    if (url.includes("/auth/login")) {
      return Promise.resolve({
        status: 200,
        json: async () => ({
          success: true,
          data: {
            id: "1",
            email: "demo_admin@example.com",
            display_name: "演示管理员",
            global_role: "SYSTEM_ADMIN",
          },
        }),
      });
    }
    return Promise.resolve({
      status: 200,
      json: async () => ({ success: true, data: {} }),
    });
  });
}

describe("LoginPage demo picker", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    // csrf cookie so write headers work
    Object.defineProperty(document, "cookie", {
      value: "csrf_token=test-token",
      writable: true,
    });
    mockLoginSuccess();
  });

  it("renders the demo account picker in the test environment", () => {
    render(<LoginPage />);
    expect(screen.getByTestId("demo-account-picker")).toBeInTheDocument();
  });

  it("lists all demo accounts", () => {
    render(<LoginPage />);
    expect(screen.getByText("演示管理员")).toBeInTheDocument();
    expect(screen.getByText("陈同学")).toBeInTheDocument();
    expect(screen.getByText("林同学")).toBeInTheDocument();
    expect(screen.getByText("王同学")).toBeInTheDocument();
    expect(screen.getByText("已删除演示用户")).toBeInTheDocument();
  });

  it("fills the email field when a demo account is clicked", () => {
    render(<LoginPage />);
    const aliceButton = screen.getByText("陈同学").closest("button")!;
    fireEvent.click(aliceButton);

    const emailInput = screen.getByLabelText("邮箱") as HTMLInputElement;
    expect(emailInput.value).toBe("demo_alice@example.com");
  });

  it("fills the password field for a loginable demo account", () => {
    render(<LoginPage />);
    const adminButton = screen.getByText("演示管理员").closest("button")!;
    fireEvent.click(adminButton);

    const passwordInput = screen.getByLabelText("密码") as HTMLInputElement;
    expect(passwordInput.value).toBe("CampusAgentDemo2026!");
  });

  it("does NOT fill the password for the deleted demo account", () => {
    render(<LoginPage />);
    const deletedButton = screen
      .getByText("已删除演示用户")
      .closest("button")!;
    fireEvent.click(deletedButton);

    const passwordInput = screen.getByLabelText("密码") as HTMLInputElement;
    expect(passwordInput.value).toBe("");
  });

  it("does NOT write the demo password to localStorage", () => {
    render(<LoginPage />);
    const adminButton = screen.getByText("演示管理员").closest("button")!;
    fireEvent.click(adminButton);

    // Scan all localStorage values for the demo password
    let found = false;
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key === null) continue;
      const val = localStorage.getItem(key) ?? "";
      if (val.includes("CampusAgentDemo2026!")) {
        found = true;
        break;
      }
    }
    expect(found).toBe(false);
  });

  it("does NOT write the demo password to sessionStorage", () => {
    render(<LoginPage />);
    const aliceButton = screen.getByText("陈同学").closest("button")!;
    fireEvent.click(aliceButton);

    let found = false;
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      if (key === null) continue;
      const val = sessionStorage.getItem(key) ?? "";
      if (val.includes("CampusAgentDemo2026!")) {
        found = true;
        break;
      }
    }
    expect(found).toBe(false);
  });

  it("calls the real /auth/login endpoint on submit after selecting a demo account", async () => {
    render(<LoginPage />);
    const adminButton = screen.getByText("演示管理员").closest("button")!;
    fireEvent.click(adminButton);

    const submitButton = screen.getByRole("button", { name: "登录" });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/auth/login"),
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("marks the selected demo account as pressed", () => {
    render(<LoginPage />);
    const bobButton = screen.getByText("林同学").closest("button")!;
    fireEvent.click(bobButton);
    expect(bobButton).toHaveAttribute("aria-pressed", "true");
  });
});

"use client";

import { ReactNode, Component } from "react";
import { AuthProvider } from "@/lib/auth";
import { NavRail } from "./NavRail";
import { TopBar } from "./TopBar";
import { RouteGuard, AdminGuard } from "./RouteGuard";
import { ErrorState } from "@/components/ui/ErrorState";

interface AppShellProps {
  children: ReactNode;
  requireAuth?: boolean;
  adminOnly?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  message: string;
  requestId: string | null;
}

/**
 * Global error boundary.
 * Catches unhandled errors and shows a safe error summary.
 * Never exposes raw API error details or stack traces.
 */
class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, message: "", requestId: null };
  }

  static getDerivedStateFromError(error: unknown): ErrorBoundaryState {
    // Extract safe error info without leaking sensitive details
    const message =
      error instanceof Error ? error.message : "发生未知错误。";
    // Never expose stack traces or raw response bodies
    const safeMessage = message.length > 200 ? message.slice(0, 200) + "..." : message;
    return { hasError: true, message: safeMessage, requestId: null };
  }

  render() {
    if (this.state.hasError) {
      return (
        <ErrorState
          title="应用错误"
          message={this.state.message}
          requestId={this.state.requestId}
          action={
            <button
              className="btn"
              onClick={() => this.setState({ hasError: false, message: "", requestId: null })}
            >
              重试
            </button>
          }
        />
      );
    }
    return this.props.children;
  }
}

/**
 * Main application shell.
 * Wraps pages with navigation, top bar, auth guard, and error boundary.
 */
export function AppShell({ children, requireAuth = true, adminOnly = false }: AppShellProps) {
  let content = children;

  if (requireAuth) {
    if (adminOnly) {
      content = <AdminGuard>{content}</AdminGuard>;
    } else {
      content = <RouteGuard>{content}</RouteGuard>;
    }
  }

  if (requireAuth) {
    return (
      <AuthProvider>
        <ErrorBoundary>
          <div style={{ display: "flex", minHeight: "100vh" }}>
            <NavRail />
            <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
              <TopBar />
              <main style={{ flex: 1, padding: "var(--space-lg)", overflow: "auto" }}>
                {content}
              </main>
            </div>
          </div>
        </ErrorBoundary>
      </AuthProvider>
    );
  }

  // Non-auth pages (login, register, health)
  return (
    <ErrorBoundary>
      <div style={{ minHeight: "100vh" }}>{children}</div>
    </ErrorBoundary>
  );
}

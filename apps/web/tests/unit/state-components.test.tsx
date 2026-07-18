/**
 * State component coverage tests.
 * Verifies that all UI state components render correctly:
 * - LoadingState
 * - EmptyState
 * - ErrorState
 * - OfflineState
 * - StatusBadge
 */

import { render, screen } from "@testing-library/react";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { OfflineState } from "@/components/ui/OfflineState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PrivacyNotice } from "@/components/privacy/PrivacyNotice";

describe("UI State Components", () => {
  describe("LoadingState", () => {
    it("renders with default message", () => {
      render(<LoadingState />);
      expect(screen.getByText("Loading...")).toBeInTheDocument();
    });

    it("renders with custom message", () => {
      render(<LoadingState message="Loading conversations..." />);
      expect(screen.getByText("Loading conversations...")).toBeInTheDocument();
    });

    it("has role=status for accessibility", () => {
      render(<LoadingState />);
      expect(screen.getByRole("status")).toBeInTheDocument();
    });
  });

  describe("EmptyState", () => {
    it("renders with default title", () => {
      render(<EmptyState />);
      expect(screen.getByText("No data")).toBeInTheDocument();
    });

    it("renders with custom title and description", () => {
      render(<EmptyState title="No conversations" description="Start a conversation to see it here." />);
      expect(screen.getByText("No conversations")).toBeInTheDocument();
      expect(screen.getByText("Start a conversation to see it here.")).toBeInTheDocument();
    });

    it("renders action button", () => {
      render(<EmptyState title="Empty" action={<button>Create</button>} />);
      expect(screen.getByText("Create")).toBeInTheDocument();
    });
  });

  describe("ErrorState", () => {
    it("renders with default error message", () => {
      render(<ErrorState />);
      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });

    it("renders with custom message and request ID", () => {
      render(<ErrorState title="Failed" message="Network error" requestId="req-123" />);
      expect(screen.getByText("Failed")).toBeInTheDocument();
      expect(screen.getByText("Network error")).toBeInTheDocument();
      expect(screen.getByText(/req-123/)).toBeInTheDocument();
    });

    it("has role=alert for accessibility", () => {
      render(<ErrorState />);
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("does not render sensitive error details", () => {
      render(<ErrorState message="Validation failed" requestId="req-456" />);
      const content = document.body.textContent ?? "";
      expect(content).not.toContain("password");
      expect(content).not.toContain("access_token");
      expect(content).not.toContain("api_key");
    });
  });

  describe("OfflineState", () => {
    it("renders offline message", () => {
      render(<OfflineState />);
      expect(screen.getByText("Connection lost")).toBeInTheDocument();
    });

    it("renders retry button when onRetry is provided", () => {
      const onRetry = jest.fn();
      render(<OfflineState onRetry={onRetry} />);
      expect(screen.getByText("Retry")).toBeInTheDocument();
    });

    it("has role=alert for accessibility", () => {
      render(<OfflineState />);
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  describe("StatusBadge", () => {
    it("renders label text", () => {
      render(<StatusBadge label="Active" />);
      expect(screen.getByText("Active")).toBeInTheDocument();
    });

    it("renders with success variant", () => {
      render(<StatusBadge label="OK" variant="success" />);
      const badge = screen.getByText("OK");
      expect(badge.className).toContain("badge-success");
    });

    it("renders with danger variant", () => {
      render(<StatusBadge label="Error" variant="danger" />);
      const badge = screen.getByText("Error");
      expect(badge.className).toContain("badge-danger");
    });

    it("has role=status for accessibility", () => {
      render(<StatusBadge label="Active" />);
      expect(screen.getByRole("status")).toBeInTheDocument();
    });
  });

  describe("PrivacyNotice", () => {
    it("renders default privacy notice", () => {
      render(<PrivacyNotice />);
      expect(screen.getByText("Privacy Notice")).toBeInTheDocument();
    });

    it("renders custom title", () => {
      render(<PrivacyNotice title="Custom Notice" />);
      expect(screen.getByText("Custom Notice")).toBeInTheDocument();
    });

    it("includes visibility information", () => {
      render(<PrivacyNotice />);
      expect(screen.getByText(/Visibility/i)).toBeInTheDocument();
    });

    it("includes purpose information", () => {
      render(<PrivacyNotice />);
      expect(screen.getByText(/Purpose/i)).toBeInTheDocument();
    });

    it("includes retention information", () => {
      render(<PrivacyNotice />);
      expect(screen.getByText(/Retention/i)).toBeInTheDocument();
    });

    it("includes deletion information", () => {
      render(<PrivacyNotice />);
      expect(screen.getByText(/Deletion/i)).toBeInTheDocument();
    });

    it("has role=note for accessibility", () => {
      render(<PrivacyNotice />);
      expect(screen.getByRole("note")).toBeInTheDocument();
    });
  });
});

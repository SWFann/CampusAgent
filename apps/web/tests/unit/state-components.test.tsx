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
      expect(screen.getByText("加载中...")).toBeInTheDocument();
    });

    it("renders with custom message", () => {
      render(<LoadingState message="正在加载会话..." />);
      expect(screen.getByText("正在加载会话...")).toBeInTheDocument();
    });

    it("has role=status for accessibility", () => {
      render(<LoadingState />);
      expect(screen.getByRole("status")).toBeInTheDocument();
    });
  });

  describe("EmptyState", () => {
    it("renders with default title", () => {
      render(<EmptyState />);
      expect(screen.getByText("暂无数据")).toBeInTheDocument();
    });

    it("renders with custom title and description", () => {
      render(<EmptyState title="暂无会话" description="开始会话后会显示在这里。" />);
      expect(screen.getByText("暂无会话")).toBeInTheDocument();
      expect(screen.getByText("开始会话后会显示在这里。")).toBeInTheDocument();
    });

    it("renders action button", () => {
      render(<EmptyState title="空状态" action={<button>创建</button>} />);
      expect(screen.getByText("创建")).toBeInTheDocument();
    });
  });

  describe("ErrorState", () => {
    it("renders with default error message", () => {
      render(<ErrorState />);
      expect(screen.getByText("发生未知错误，请稍后重试。")).toBeInTheDocument();
    });

    it("renders with custom message and request ID", () => {
      render(<ErrorState title="失败" message="网络错误" requestId="req-123" />);
      expect(screen.getByText("失败")).toBeInTheDocument();
      expect(screen.getByText("网络错误")).toBeInTheDocument();
      expect(screen.getByText(/req-123/)).toBeInTheDocument();
    });

    it("has role=alert for accessibility", () => {
      render(<ErrorState />);
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("does not render sensitive error details", () => {
      render(<ErrorState message="校验失败" requestId="req-456" />);
      const content = document.body.textContent ?? "";
      expect(content).not.toContain("password");
      expect(content).not.toContain("access_token");
      expect(content).not.toContain("api_key");
    });
  });

  describe("OfflineState", () => {
    it("renders offline message", () => {
      render(<OfflineState />);
      expect(screen.getByText("连接已断开")).toBeInTheDocument();
    });

    it("renders retry button when onRetry is provided", () => {
      const onRetry = jest.fn();
      render(<OfflineState onRetry={onRetry} />);
      expect(screen.getByText("重试")).toBeInTheDocument();
    });

    it("has role=alert for accessibility", () => {
      render(<OfflineState />);
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  describe("StatusBadge", () => {
    it("renders label text", () => {
      render(<StatusBadge label="ACTIVE" />);
      expect(screen.getByText("启用")).toBeInTheDocument();
    });

    it("renders with success variant", () => {
      render(<StatusBadge label="成功" variant="success" />);
      const badge = screen.getByText("成功");
      expect(badge.className).toContain("badge-success");
    });

    it("renders with danger variant", () => {
      render(<StatusBadge label="错误" variant="danger" />);
      const badge = screen.getByText("错误");
      expect(badge.className).toContain("badge-danger");
    });

    it("has role=status for accessibility", () => {
      render(<StatusBadge label="ACTIVE" />);
      expect(screen.getByRole("status")).toBeInTheDocument();
    });
  });

  describe("PrivacyNotice", () => {
    it("renders default privacy notice", () => {
      render(<PrivacyNotice />);
      expect(screen.getByText("隐私提示")).toBeInTheDocument();
    });

    it("renders custom title", () => {
      render(<PrivacyNotice title="自定义提示" />);
      expect(screen.getByText("自定义提示")).toBeInTheDocument();
    });

    it("includes visibility information", () => {
      render(<PrivacyNotice />);
      expect(screen.getByText(/可见性/)).toBeInTheDocument();
    });

    it("includes purpose information", () => {
      render(<PrivacyNotice />);
      expect(screen.getByText(/使用目的/)).toBeInTheDocument();
    });

    it("includes retention information", () => {
      render(<PrivacyNotice />);
      expect(screen.getByText(/保留期限/)).toBeInTheDocument();
    });

    it("includes deletion information", () => {
      render(<PrivacyNotice />);
      expect(screen.getByText("删除：")).toBeInTheDocument();
    });

    it("has role=note for accessibility", () => {
      render(<PrivacyNotice />);
      expect(screen.getByRole("note")).toBeInTheDocument();
    });
  });
});

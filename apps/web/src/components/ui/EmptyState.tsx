"use client";

import { ReactNode } from "react";

/**
 * Empty state component.
 * Shows an icon, title, and optional description/action.
 */
export function EmptyState({
  title = "No data",
  description,
  action,
  icon,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--space-2xl)",
        gap: "var(--space-sm)",
        textAlign: "center",
      }}
    >
      {icon && <div style={{ color: "var(--color-text-muted)", fontSize: 32 }}>{icon}</div>}
      <p style={{ fontWeight: "var(--font-weight-medium)", color: "var(--color-text-primary)" }}>
        {title}
      </p>
      {description && (
        <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)", maxWidth: 400 }}>
          {description}
        </p>
      )}
      {action && <div style={{ marginTop: "var(--space-sm)" }}>{action}</div>}
    </div>
  );
}

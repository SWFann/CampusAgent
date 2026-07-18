"use client";

import { ReactNode } from "react";

/**
 * Error state component.
 * Shows a safe error summary without leaking sensitive details.
 * Only displays the request_id for debugging, never the raw response.
 */
export function ErrorState({
  title = "Something went wrong",
  message = "An unexpected error occurred. Please try again.",
  requestId,
  action,
}: {
  title?: string;
  message?: string;
  requestId?: string | null;
  action?: ReactNode;
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
      role="alert"
    >
      <div style={{ color: "var(--color-danger)", fontSize: 32 }} aria-hidden="true">
        &#9888;
      </div>
      <p style={{ fontWeight: "var(--font-weight-semibold)", color: "var(--color-danger)" }}>
        {title}
      </p>
      <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)", maxWidth: 400 }}>
        {message}
      </p>
      {requestId && (
        <p
          style={{
            color: "var(--color-text-muted)",
            fontSize: "var(--font-size-xs)",
            fontFamily: "monospace",
          }}
        >
          Request ID: {requestId}
        </p>
      )}
      {action && <div style={{ marginTop: "var(--space-sm)" }}>{action}</div>}
    </div>
  );
}

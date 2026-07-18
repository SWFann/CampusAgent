"use client";

import { ReactNode } from "react";

/**
 * Loading state component.
 * Shows a spinner and optional message.
 */
export function LoadingState({ message = "Loading..." }: { message?: string }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--space-2xl)",
        gap: "var(--space-md)",
      }}
      role="status"
      aria-live="polite"
    >
      <div
        style={{
          width: 32,
          height: 32,
          border: "3px solid var(--color-border)",
          borderTopColor: "var(--color-primary)",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
        aria-hidden="true"
      />
      <span style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
        {message}
      </span>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

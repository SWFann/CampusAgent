"use client";

/**
 * Offline state component.
 * Shows when the network is disconnected.
 */
export function OfflineState({ onRetry }: { onRetry?: () => void }) {
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
      <div style={{ color: "var(--color-warning)", fontSize: 32 }} aria-hidden="true">
        &#9889;
      </div>
      <p style={{ fontWeight: "var(--font-weight-semibold)", color: "var(--color-warning)" }}>
        Connection lost
      </p>
      <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
        You are offline. Changes will be synced when the connection is restored.
      </p>
      {onRetry && (
        <button className="btn btn-sm" onClick={onRetry} style={{ marginTop: "var(--space-sm)" }}>
          Retry
        </button>
      )}
    </div>
  );
}

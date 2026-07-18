"use client";

/**
 * 离线 state component.
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
        连接已断开
      </p>
      <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)" }}>
        当前处于离线状态，连接恢复后会继续同步。
      </p>
      {onRetry && (
        <button className="btn btn-sm" onClick={onRetry} style={{ marginTop: "var(--space-sm)" }}>
          重试
        </button>
      )}
    </div>
  );
}

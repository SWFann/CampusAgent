"use client";

import { ReactNode } from "react";

/**
 * Privacy notice component.
 * Displays a privacy explanation before any preference input form.
 * Must appear before input fields to inform the user about data visibility,
 * purpose, retention, and deletion.
 */
export function PrivacyNotice({
  title = "Privacy Notice",
  children,
}: {
  title?: string;
  children?: ReactNode;
}) {
  return (
    <div
      style={{
        background: "var(--color-privacy-light)",
        border: "1px solid var(--color-privacy)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-md)",
        marginBottom: "var(--space-md)",
      }}
      role="note"
      aria-label={title}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-xs)",
          marginBottom: "var(--space-xs)",
        }}
      >
        <span style={{ color: "var(--color-privacy)", fontSize: 18 }} aria-hidden="true">
          &#128274;
        </span>
        <strong style={{ color: "var(--color-privacy)", fontSize: "var(--font-size-sm)" }}>
          {title}
        </strong>
      </div>
      <div
        style={{
          fontSize: "var(--font-size-sm)",
          color: "var(--color-text-primary)",
          lineHeight: "var(--line-height-relaxed)",
        }}
      >
        {children ?? (
          <>
            <p style={{ marginBottom: "var(--space-xs)" }}>
              &#8226; <strong>Visibility:</strong> Only you can see your raw preferences. Other members only see aggregated results.
            </p>
            <p style={{ marginBottom: "var(--space-xs)" }}>
              &#8226; <strong>Purpose:</strong> Used only for this scene&apos;s recommendation algorithm.
            </p>
            <p style={{ marginBottom: "var(--space-xs)" }}>
              &#8226; <strong>Retention:</strong> Deleted after the scene ends, or within 24 hours at most.
            </p>
            <p>
              &#8226; <strong>Deletion:</strong> You can delete your submission at any time before the scene ends.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

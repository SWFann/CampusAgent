"use client";

import { ReactNode } from "react";

/**
 * Privacy notice component.
 * Displays a privacy explanation before any preference input form.
 * Must appear before input fields to inform the user about data visibility,
 * purpose, retention, and deletion.
 */
export function PrivacyNotice({
  title = "隐私提示",
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
              &#8226; <strong>可见性：</strong>只有你可以看到原始偏好，其他成员只能看到聚合结果。
            </p>
            <p style={{ marginBottom: "var(--space-xs)" }}>
              &#8226; <strong>使用目的：</strong>仅用于当前场景的推荐算法。
            </p>
            <p style={{ marginBottom: "var(--space-xs)" }}>
              &#8226; <strong>保留期限：</strong>场景结束后删除，最长不超过 24 小时。
            </p>
            <p>
              &#8226; <strong>删除：</strong>你可以在场景结束前随时删除自己的提交。
            </p>
          </>
        )}
      </div>
    </div>
  );
}

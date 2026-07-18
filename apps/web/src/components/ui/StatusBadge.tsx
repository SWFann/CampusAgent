"use client";

/**
 * Status badge component.
 * Displays a colored badge with a label.
 */
type BadgeVariant = "success" | "warning" | "danger" | "info" | "privacy" | "default";

const variantClasses: Record<BadgeVariant, string> = {
  success: "badge-success",
  warning: "badge-warning",
  danger: "badge-danger",
  info: "badge-info",
  privacy: "badge-privacy",
  default: "",
};

export function StatusBadge({
  label,
  variant = "default",
}: {
  label: string;
  variant?: BadgeVariant;
}) {
  const className = variantClasses[variant] || "";
  return (
    <span className={`badge ${className}`} role="status">
      {label}
    </span>
  );
}

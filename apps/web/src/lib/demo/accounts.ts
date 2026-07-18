/**
 * P11-05: Demo account constants for the frontend.
 *
 * Mirrors the non-sensitive public subset of the backend demo data
 * (apps/api/src/demo/data.py) so the login page can offer one-click
 * demo account selection without duplicating the dataset.
 *
 * Privacy:
 * - DEMO_PASSWORD is a PUBLIC demo-only constant (the same value as
 *   the backend). It is never written to localStorage/sessionStorage
 *   or any persistent store. It is only ever held in React state to
 *   pre-fill the password input for demo convenience.
 * - DEMO_PRIVATE_PHRASE is exposed so frontend privacy tests can scan
 *   the DOM and storage for leaks (it must NEVER appear in results,
 *   admin pages, or browser storage).
 * - Demo account selection only fills form fields; login still goes
 *   through the real /api/v1/auth/login endpoint.
 *
 * The demo picker is gated to development/test builds via NODE_ENV so
 * it never ships in production bundles.
 */

/** Public demo password (same as backend DEMO_PASSWORD). */
export const DEMO_PASSWORD = "CampusAgentDemo2026!";

/** Unique marker carried in private preference notes. */
export const DEMO_PRIVATE_PHRASE = "DEMO_PRIVATE_PHRASE_DO_NOT_RENDER";

/** A selectable demo account (public, non-sensitive fields only). */
export interface DemoAccount {
  key: string;
  email: string;
  display_name: string;
  role: "SYSTEM_ADMIN" | "STUDENT";
  description: string;
  /** Whether this account can log in (soft-deleted accounts cannot). */
  can_login: boolean;
}

/** The fixed demo account list shown in the login picker. */
export const DEMO_ACCOUNTS: readonly DemoAccount[] = [
  {
    key: "admin",
    email: "demo_admin@example.com",
    display_name: "Demo Admin",
    role: "SYSTEM_ADMIN",
    description: "管理员 — 可访问管理后台与 demo 重置接口",
    can_login: true,
  },
  {
    key: "alice",
    email: "demo_alice@example.com",
    display_name: "Alice Chen",
    role: "STUDENT",
    description: "学生用户 — 聚餐场景参与者",
    can_login: true,
  },
  {
    key: "bob",
    email: "demo_bob@example.com",
    display_name: "Bob Lin",
    role: "STUDENT",
    description: "学生用户 — 聚餐场景参与者",
    can_login: true,
  },
  {
    key: "carol",
    email: "demo_carol@example.com",
    display_name: "Carol Wang",
    role: "STUDENT",
    description: "学生用户 — 聚餐场景参与者",
    can_login: true,
  },
  {
    key: "deleted",
    email: "demo_deleted@example.com",
    display_name: "Deleted Demo User",
    role: "STUDENT",
    description: "软删除用户 — 用于演示登录失败场景",
    can_login: false,
  },
] as const;

/** Look up a demo account by its key. */
export function getDemoAccountByKey(key: string): DemoAccount | undefined {
  return DEMO_ACCOUNTS.find((a) => a.key === key);
}

/** Look up a demo account by email (case-insensitive). */
export function getDemoAccountByEmail(email: string): DemoAccount | undefined {
  const lower = email.toLowerCase().trim();
  return DEMO_ACCOUNTS.find((a) => a.email.toLowerCase() === lower);
}

/** Return true if an email belongs to the demo namespace. */
export function isDemoEmail(email: string): boolean {
  if (!email) return false;
  const lower = email.toLowerCase().trim();
  return lower.startsWith("demo_") && lower.endsWith("@example.com");
}

/**
 * Whether the demo account picker should be shown.
 *
 * Gated to non-production builds so the picker never appears in a
 * production bundle. Next.js replaces process.env.NODE_ENV at build
 * time, so this branch is statically eliminated in production.
 */
export function isDemoPickerEnabled(): boolean {
  return process.env.NODE_ENV !== "production";
}

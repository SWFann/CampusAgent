/**
 * P11-05: Unit tests for the demo accounts module.
 *
 * Verifies:
 * - DEMO_ACCOUNTS has at least 5 accounts, emails unique.
 * - At least one admin and at least 3 students.
 * - DEMO_PASSWORD is non-empty and matches the public constant.
 * - isDemoEmail / getDemoAccountByKey / getDemoAccountByEmail helpers.
 * - isDemoPickerEnabled is true in the test environment.
 */

import {
  DEMO_ACCOUNTS,
  DEMO_PASSWORD,
  DEMO_PRIVATE_PHRASE,
  getDemoAccountByEmail,
  getDemoAccountByKey,
  isDemoEmail,
  isDemoPickerEnabled,
} from "@/lib/demo";

describe("DEMO_ACCOUNTS", () => {
  it("has at least 5 accounts", () => {
    expect(DEMO_ACCOUNTS.length).toBeGreaterThanOrEqual(5);
  });

  it("has unique emails", () => {
    const emails = DEMO_ACCOUNTS.map((a) => a.email);
    expect(new Set(emails).size).toBe(emails.length);
  });

  it("has at least one SYSTEM_ADMIN", () => {
    const admins = DEMO_ACCOUNTS.filter((a) => a.role === "SYSTEM_ADMIN");
    expect(admins.length).toBeGreaterThanOrEqual(1);
  });

  it("has at least 3 students", () => {
    const students = DEMO_ACCOUNTS.filter((a) => a.role === "STUDENT");
    expect(students.length).toBeGreaterThanOrEqual(3);
  });

  it("all emails are lowercase demo_ prefix", () => {
    for (const a of DEMO_ACCOUNTS) {
      expect(a.email.startsWith("demo_")).toBe(true);
      expect(a.email).toBe(a.email.toLowerCase());
    }
  });

  it("marks the deleted account as not loginable", () => {
    const deleted = getDemoAccountByKey("deleted");
    expect(deleted).toBeDefined();
    expect(deleted!.can_login).toBe(false);
  });

  it("marks active accounts as loginable", () => {
    for (const a of DEMO_ACCOUNTS) {
      if (a.key === "deleted") continue;
      expect(a.can_login).toBe(true);
    }
  });
});

describe("DEMO_PASSWORD", () => {
  it("is non-empty and long enough", () => {
    expect(DEMO_PASSWORD.length).toBeGreaterThanOrEqual(12);
  });

  it("matches the public demo constant", () => {
    expect(DEMO_PASSWORD).toBe("CampusAgentDemo2026!");
  });
});

describe("DEMO_PRIVATE_PHRASE", () => {
  it("is the unique leak marker", () => {
    expect(DEMO_PRIVATE_PHRASE).toBe("DEMO_PRIVATE_PHRASE_DO_NOT_RENDER");
  });
});

describe("isDemoEmail", () => {
  it("returns true for demo emails", () => {
    expect(isDemoEmail("demo_alice@example.com")).toBe(true);
    expect(isDemoEmail("demo_admin@example.com")).toBe(true);
  });

  it("returns false for non-demo emails", () => {
    expect(isDemoEmail("alice@example.com")).toBe(false);
    expect(isDemoEmail("demo_alice@other.com")).toBe(false);
    expect(isDemoEmail("")).toBe(false);
  });
});

describe("getDemoAccountByKey", () => {
  it("finds an account by key", () => {
    const admin = getDemoAccountByKey("admin");
    expect(admin).toBeDefined();
    expect(admin!.email).toBe("demo_admin@example.com");
  });

  it("returns undefined for unknown key", () => {
    expect(getDemoAccountByKey("nonexistent")).toBeUndefined();
  });
});

describe("getDemoAccountByEmail", () => {
  it("finds an account by email (case-insensitive)", () => {
    const found = getDemoAccountByEmail("DEMO_ALICE@EXAMPLE.COM");
    expect(found).toBeDefined();
    expect(found!.key).toBe("alice");
  });

  it("returns undefined for unknown email", () => {
    expect(getDemoAccountByEmail("nobody@example.com")).toBeUndefined();
  });
});

describe("isDemoPickerEnabled", () => {
  it("returns true in the test environment", () => {
    // Jest sets NODE_ENV=test
    expect(isDemoPickerEnabled()).toBe(true);
  });
});

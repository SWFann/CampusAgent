/**
 * Storage audit tests.
 *
 * Verifies that sensitive data patterns are detected in localStorage
 * and sessionStorage.
 */

import { auditStorage, clearSensitiveKey, isSensitiveValue } from "@/lib/security/storage-audit";

describe("Storage Audit", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("reports no leaks when storage is clean", () => {
    const result = auditStorage();
    expect(result.hasLeaks).toBe(false);
    expect(result.leaks).toHaveLength(0);
  });

  it("detects token in localStorage", () => {
    window.localStorage.setItem("access_token", "abc123");
    const result = auditStorage();
    expect(result.hasLeaks).toBe(true);
    expect(result.leaks).toHaveLength(1);
    expect(result.leaks[0].storage).toBe("localStorage");
    expect(result.leaks[0].key).toBe("access_token");
  });

  it("detects refresh_token in sessionStorage", () => {
    window.sessionStorage.setItem("refresh_token", "xyz789");
    const result = auditStorage();
    expect(result.hasLeaks).toBe(true);
    expect(result.leaks[0].storage).toBe("sessionStorage");
  });

  it("detects private preference keys", () => {
    window.localStorage.setItem("private_preferences", "some data");
    const result = auditStorage();
    expect(result.hasLeaks).toBe(true);
  });

  it("detects message_body keys", () => {
    window.localStorage.setItem("message_body", "hello");
    const result = auditStorage();
    expect(result.hasLeaks).toBe(true);
  });

  it("does not flag safe keys", () => {
    window.localStorage.setItem("theme", "dark");
    window.localStorage.setItem("locale", "zh-CN");
    window.sessionStorage.setItem("redirect_to", "/home");
    const result = auditStorage();
    expect(result.hasLeaks).toBe(false);
  });

  it("clears sensitive keys from localStorage", () => {
    window.localStorage.setItem("api_key", "secret");
    const cleared = clearSensitiveKey("localStorage", "api_key");
    expect(cleared).toBe(true);
    expect(window.localStorage.getItem("api_key")).toBeNull();
  });

  it("does not clear non-sensitive keys", () => {
    window.localStorage.setItem("theme", "dark");
    const cleared = clearSensitiveKey("localStorage", "theme");
    expect(cleared).toBe(false);
    expect(window.localStorage.getItem("theme")).toBe("dark");
  });

  it("isSensitiveValue detects sensitive strings", () => {
    expect(isSensitiveValue("access_token value")).toBe(true);
    expect(isSensitiveValue("user password")).toBe(true);
    expect(isSensitiveValue("hello world")).toBe(false);
  });
});

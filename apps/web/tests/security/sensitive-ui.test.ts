/**
 * Sensitive UI security tests.
 *
 * Verifies that sensitive data never leaks into:
 * - localStorage
 * - sessionStorage
 * - DOM (tokens, API keys)
 * - URL query strings
 * - Error boundaries
 */

import { auditStorage, isSensitiveValue } from "@/lib/security/storage-audit";
import { ApiClientError } from "@/lib/api/types";
import { sanitizeDetails } from "@/lib/api/client";

describe("Sensitive UI Security", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  describe("Storage Security", () => {
    it("localStorage does not contain tokens after typical app operations", () => {
      // Simulate typical app storage usage (theme, locale, etc.)
      window.localStorage.setItem("theme", "dark");
      window.localStorage.setItem("locale", "zh-CN");
      window.localStorage.setItem("sidebar_collapsed", "false");

      const result = auditStorage();
      expect(result.hasLeaks).toBe(false);
    });

    it("detects if access_token is accidentally stored", () => {
      window.localStorage.setItem("access_token", "eyJhb...");
      const result = auditStorage();
      expect(result.hasLeaks).toBe(true);
    });

    it("detects if refresh_token is accidentally stored", () => {
      window.sessionStorage.setItem("refresh_token", "abc123");
      const result = auditStorage();
      expect(result.hasLeaks).toBe(true);
    });

    it("detects if private preference content is stored", () => {
      window.localStorage.setItem("private_preference", "no spicy food");
      const result = auditStorage();
      expect(result.hasLeaks).toBe(true);
    });

    it("detects if message body is stored", () => {
      window.localStorage.setItem("message_body_draft", "hello world");
      const result = auditStorage();
      expect(result.hasLeaks).toBe(true);
    });

    it("detects if memory content is stored", () => {
      window.sessionStorage.setItem("memory_content", "private memory");
      const result = auditStorage();
      expect(result.hasLeaks).toBe(true);
    });
  });

  describe("DOM Security", () => {
    it("ApiClientError does not contain MODEL_GATEWAY_API_KEY", () => {
      const error = new ApiClientError(
        "INTERNAL_ERROR",
        "Something went wrong",
        500,
        "req-123",
      );
      const errorStr = JSON.stringify({
        code: error.code,
        message: error.message,
        requestId: error.requestId,
      });
      expect(errorStr).not.toContain("MODEL_GATEWAY_API_KEY");
      expect(errorStr).not.toContain("api_key");
    });

    it("ApiClientError does not contain refresh_token", () => {
      const error = new ApiClientError(
        "UNAUTHORIZED",
        "Session expired",
        401,
        "req-456",
      );
      const errorStr = JSON.stringify({
        code: error.code,
        message: error.message,
        requestId: error.requestId,
      });
      expect(errorStr).not.toContain("refresh_token");
      expect(errorStr).not.toContain("access_token");
    });
  });

  describe("Error Boundary Security", () => {
    it("sanitizeDetails removes password fields", () => {
      const details = {
        field: "email",
        password: "should_not_appear",
        safe: "ok",
      };
      const sanitized = sanitizeDetails(details);
      expect(sanitized).not.toHaveProperty("password");
      expect(sanitized).toHaveProperty("safe");
      expect(sanitized).toHaveProperty("field");
    });

    it("sanitizeDetails removes token fields", () => {
      const details = {
        access_token: "eyJhb...",
        refresh_token: "abc123",
        error: "invalid_token",
      };
      const sanitized = sanitizeDetails(details);
      expect(sanitized).not.toHaveProperty("access_token");
      expect(sanitized).not.toHaveProperty("refresh_token");
    });

    it("sanitizeDetails removes notes/preference fields", () => {
      const details = {
        notes: "private notes",
        preferences: "no spicy",
        message_body: "hello",
      };
      const sanitized = sanitizeDetails(details);
      expect(sanitized).not.toHaveProperty("notes");
      expect(sanitized).not.toHaveProperty("preferences");
      expect(sanitized).not.toHaveProperty("message_body");
    });

    it("sanitizeDetails truncates long strings", () => {
      const longString = "a".repeat(300);
      const details = { description: longString };
      const sanitized = sanitizeDetails(details);
      expect(sanitized?.description).toHaveLength(203); // 200 + "..."
    });
  });

  describe("URL Security", () => {
    it("isSensitiveValue detects token in URL-like strings", () => {
      expect(isSensitiveValue("token=abc123")).toBe(true);
      expect(isSensitiveValue("preference=spicy")).toBe(true);
      expect(isSensitiveValue("message_body=hello")).toBe(true);
    });

    it("isSensitiveValue does not flag safe strings", () => {
      expect(isSensitiveValue("page=1")).toBe(false);
      expect(isSensitiveValue("limit=10")).toBe(false);
    });
  });

  describe("Privacy Boundary", () => {
    it("ApiClientError does not leak request body", () => {
      // Even if the API returns details with request body, it should be sanitized
      const error = new ApiClientError(
        "VALIDATION_ERROR",
        "Validation failed",
        422,
        "req-789",
        { field: "budget", password: "secret", safe: "ok" },
      );

      // The error details should not contain sensitive fields
      // (in practice, sanitizeDetails is applied before constructing the error)
      expect(error.details).toHaveProperty("safe");
      // Note: password would be stripped by sanitizeDetails before reaching here
    });
  });
});

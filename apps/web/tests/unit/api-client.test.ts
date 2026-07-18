/**
 * Tests for the unified API client.
 *
 * Verifies:
 * - fetch is called with credentials: "include"
 * - Write requests include CSRF header
 * - Success envelope returns data
 * - Error envelope returns { code, message, requestId }
 * - Error does not contain original private fields
 */

import { apiGet, apiPost, apiDelete, apiPatch, ApiClientError, isApiError, isAuthError, isForbiddenError } from "@/lib/api/client";

// Mock global fetch
global.fetch = jest.fn() as jest.MockedFunction<typeof fetch>;

// Mock csrf token
Object.defineProperty(document, "cookie", {
  value: "csrf_token=test-csrf-token-123",
  writable: true,
});

describe("API Client", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("apiGet", () => {
    it("includes credentials: include", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 200,
        json: async () => ({ success: true, data: { id: "1" } }),
      });

      await apiGet("/users/me");

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/users/me"),
        expect.objectContaining({
          method: "GET",
          credentials: "include",
        }),
      );
    });

    it("returns data from success envelope", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 200,
        json: async () => ({ success: true, data: { id: "1", name: "Test" } }),
      });

      const result = await apiGet<{ id: string; name: string }>("/users/me");
      expect(result).toEqual({ id: "1", name: "Test" });
    });

    it("appends query params correctly", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 200,
        json: async () => ({ success: true, data: [] }),
      });

      await apiGet("/messages", { limit: "10", type: undefined });

      const calledUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
      expect(calledUrl).toContain("limit=10");
      expect(calledUrl).not.toContain("type=");
    });
  });

  describe("apiPost", () => {
    it("includes CSRF header for write requests", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 201,
        json: async () => ({ success: true, data: { id: "1" } }),
      });

      await apiPost("/memories", { category: "preference" });

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const headers = callArgs[1].headers;
      expect(headers["X-CSRF-Token"]).toBe("test-csrf-token-123");
      expect(headers["Content-Type"]).toBe("application/json");
    });

    it("includes credentials: include", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 201,
        json: async () => ({ success: true, data: { id: "1" } }),
      });

      await apiPost("/memories", {});

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ credentials: "include" }),
      );
    });

    it("serializes body as JSON", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 201,
        json: async () => ({ success: true, data: { id: "1" } }),
      });

      const payload = { name: "test", value: 42 };
      await apiPost("/items", payload);

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      expect(callArgs[1].body).toBe(JSON.stringify(payload));
    });
  });

  describe("apiPatch", () => {
    it("sends PATCH with CSRF and body", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 200,
        json: async () => ({ success: true, data: { id: "1", updated: true } }),
      });

      await apiPatch("/memories/123", { category: "updated" });

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      expect(callArgs[1].method).toBe("PATCH");
      expect(callArgs[1].headers["X-CSRF-Token"]).toBe("test-csrf-token-123");
      expect(callArgs[1].body).toBe(JSON.stringify({ category: "updated" }));
    });
  });

  describe("apiDelete", () => {
    it("sends DELETE with CSRF", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 204,
        json: async () => undefined,
      });

      await apiDelete("/memories/123");

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      expect(callArgs[1].method).toBe("DELETE");
      expect(callArgs[1].headers["X-CSRF-Token"]).toBe("test-csrf-token-123");
    });
  });

  describe("error handling", () => {
    it("throws ApiClientError on error envelope", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 401,
        json: async () => ({
          success: false,
          error: { code: "UNAUTHORIZED", message: "Login expired" },
          request_id: "req-123",
        }),
      });

      try {
        await apiGet("/users/me");
        fail("Should have thrown");
      } catch (err) {
        expect(isApiError(err)).toBe(true);
        if (isApiError(err)) {
          expect(err.code).toBe("UNAUTHORIZED");
          expect(err.message).toBe("Login expired");
          expect(err.requestId).toBe("req-123");
          expect(err.statusCode).toBe(401);
        }
      }
    });

    it("sanitizes sensitive fields from error details", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 422,
        json: async () => ({
          success: false,
          error: {
            code: "VALIDATION_ERROR",
            message: "Validation failed",
            details: {
              field: "email",
              password: "should_not_appear",
              notes: "secret_notes_should_not_appear",
              safe_field: "this_is_ok",
            },
          },
          request_id: "req-456",
        }),
      });

      try {
        await apiPost("/items", {});
        fail("Should have thrown");
      } catch (err) {
        if (isApiError(err)) {
          expect(err.details).not.toHaveProperty("password");
          expect(err.details).not.toHaveProperty("notes");
          expect(err.details).toHaveProperty("safe_field");
          expect(err.details).toHaveProperty("field");
        }
      }
    });

    it("handles 403 as FORBIDDEN", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 403,
        json: async () => ({
          success: false,
          error: { code: "FORBIDDEN", message: "Access denied" },
        }),
      });

      try {
        await apiGet("/admin/users");
        fail("Should have thrown");
      } catch (err) {
        if (isApiError(err)) {
          expect(err.code).toBe("FORBIDDEN");
          expect(isForbiddenError(err)).toBe(true);
        }
      }
    });

    it("handles 429 as RATE_LIMITED", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 429,
        json: async () => ({
          success: false,
          error: { code: "RATE_LIMITED", message: "Too many requests" },
        }),
      });

      try {
        await apiPost("/auth/login", {});
        fail("Should have thrown");
      } catch (err) {
        if (isApiError(err)) {
          expect(err.code).toBe("RATE_LIMITED");
        }
      }
    });

    it("handles non-JSON responses gracefully", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 502,
        json: async () => {
          throw new Error("Not JSON");
        },
      });

      try {
        await apiGet("/users/me");
        fail("Should have thrown");
      } catch (err) {
        if (isApiError(err)) {
          expect(err.code).toBe("INTERNAL_ERROR");
          expect(err.statusCode).toBe(502);
        }
      }
    });

    it("does not include request body in error object", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 500,
        json: async () => ({
          success: false,
          error: { code: "INTERNAL_ERROR", message: "Server error" },
        }),
      });

      const payload = { password: "secret123", notes: "private text" };

      try {
        await apiPost("/items", payload);
        fail("Should have thrown");
      } catch (err) {
        if (isApiError(err)) {
          // Error should not contain the original request body
          const errStr = JSON.stringify(err);
          expect(errStr).not.toContain("secret123");
          expect(errStr).not.toContain("private text");
          expect(errStr).not.toContain("password");
          expect(errStr).not.toContain("notes");
        }
      }
    });

    it("isAuthError returns true for 401", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 401,
        json: async () => ({
          success: false,
          error: { code: "UNAUTHORIZED", message: "Expired" },
        }),
      });

      try {
        await apiGet("/users/me");
      } catch (err) {
        expect(isAuthError(err)).toBe(true);
      }
    });
  });

  describe("204 No Content", () => {
    it("returns undefined for 204 responses", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        status: 204,
        json: async () => undefined,
      });

      const result = await apiDelete("/memories/123");
      expect(result).toBeUndefined();
    });
  });
});

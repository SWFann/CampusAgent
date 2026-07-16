/**
 * CSRF token helper for CampusAgent.
 *
 * Reads the csrf_token cookie (non-HttpOnly) and returns its value.
 * The CSRF token is set by the server on login/register and used for
 * double-submit cookie validation on write requests.
 */

/**
 * Get the CSRF token from the csrf_token cookie.
 * Returns null if the cookie is not present.
 */
export function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : null;
}

/**
 * Build headers for a write request (POST/PATCH/DELETE).
 * Includes Content-Type and X-CSRF-Token.
 */
export function getWriteHeaders(): Record<string, string> {
  const csrfToken = getCsrfToken();
  return {
    "Content-Type": "application/json",
    ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
  };
}

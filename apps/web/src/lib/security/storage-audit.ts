/**
 * Storage audit utility for detecting sensitive data leaks.
 *
 * Checks localStorage and sessionStorage for tokens, private preferences,
 * message content, and memory content that should never be persisted.
 */

/** Patterns that indicate sensitive data in storage. */
const SENSITIVE_PATTERNS = [
  /token/i,
  /password/i,
  /api_?key/i,
  /secret/i,
  /preference/i,
  /private/i,
  /message_?body/i,
  /memory_?content/i,
  /notes/i,
  /refresh_?token/i,
  /access_?token/i,
] as const;

/** Result of a storage audit. */
export interface StorageAuditResult {
  hasLeaks: boolean;
  leaks: StorageLeak[];
}

/** A single storage leak. */
export interface StorageLeak {
  storage: "localStorage" | "sessionStorage";
  key: string;
  matchedPattern: string;
}

/** Audit localStorage and sessionStorage for sensitive data. */
export function auditStorage(): StorageAuditResult {
  const leaks: StorageLeak[] = [];

  if (typeof window === "undefined") {
    return { hasLeaks: false, leaks: [] };
  }

  // Audit localStorage.
  for (let i = 0; i < window.localStorage.length; i++) {
    const key = window.localStorage.key(i);
    if (key === null) continue;
    for (const pattern of SENSITIVE_PATTERNS) {
      if (pattern.test(key)) {
        leaks.push({
          storage: "localStorage",
          key,
          matchedPattern: pattern.source,
        });
        break;
      }
    }
  }

  // Audit sessionStorage.
  for (let i = 0; i < window.sessionStorage.length; i++) {
    const key = window.sessionStorage.key(i);
    if (key === null) continue;
    for (const pattern of SENSITIVE_PATTERNS) {
      if (pattern.test(key)) {
        leaks.push({
          storage: "sessionStorage",
          key,
          matchedPattern: pattern.source,
        });
        break;
      }
    }
  }

  return { hasLeaks: leaks.length > 0, leaks };
}

/** Clear a specific storage key if it matches sensitive patterns. */
export function clearSensitiveKey(
  storage: "localStorage" | "sessionStorage",
  key: string,
): boolean {
  if (typeof window === "undefined") return false;

  const isSensitive = SENSITIVE_PATTERNS.some((p) => p.test(key));
  if (!isSensitive) return false;

  try {
    window[storage].removeItem(key);
    return true;
  } catch {
    return false;
  }
}

/** Check if a string contains sensitive value indicators. */
export function isSensitiveValue(value: string): boolean {
  return SENSITIVE_PATTERNS.some((p) => p.test(value));
}

/**
 * P11-05: Frontend demo utilities.
 *
 * Public, non-sensitive demo account data and helpers used by the
 * login page's demo account picker. See accounts.ts for details.
 */

export {
  DEMO_PASSWORD,
  DEMO_PRIVATE_PHRASE,
  DEMO_ACCOUNTS,
  getDemoAccountByKey,
  getDemoAccountByEmail,
  isDemoEmail,
  isDemoPickerEnabled,
} from "./accounts";
export type { DemoAccount } from "./accounts";

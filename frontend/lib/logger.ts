/**
 * Development-only logger that silences in production builds.
 *
 * Logs are stripped in production except for errors, which are always preserved
 * for debugging critical issues.
 *
 * @example
 * import { logger } from '@/lib/logger'
 *
 * logger.log('[Search] Query executed')     // Dev only
 * logger.error('[API] Request failed:', err) // Always logged
 */

const isDev = process.env.NODE_ENV === "development";

export const logger = {
  log: (...args: any[]) => {
    if (isDev) console.log(...args);
  },

  warn: (...args: any[]) => {
    if (isDev) console.warn(...args);
  },

  error: (...args: any[]) => {
    console.error(...args);
  },

  info: (...args: any[]) => {
    if (isDev) console.info(...args);
  },

  group: (label: string) => {
    if (isDev) console.group(label);
  },

  groupEnd: () => {
    if (isDev) console.groupEnd();
  },
};

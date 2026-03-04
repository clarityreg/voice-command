/**
 * Notification engine for severity-based alerts.
 *
 * Uses the Web Notifications API to alert users about new triage items
 * based on configurable severity thresholds.
 */

import { SEVERITY_ICONS, type Severity } from "@/lib/severity";

export type { Severity };

const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};

const STORAGE_KEY = "clarity_notification_threshold";

/** Get the current notification threshold from localStorage. Defaults to "high". */
export function getThreshold(): Severity {
  if (typeof window === "undefined") return "high";
  return (localStorage.getItem(STORAGE_KEY) as Severity) ?? "high";
}

/** Set the notification threshold. Only items at this severity or above will trigger. */
export function setThreshold(severity: Severity): void {
  localStorage.setItem(STORAGE_KEY, severity);
}

/** Check if a severity level meets or exceeds the current threshold. */
export function meetsThreshold(severity: Severity): boolean {
  const threshold = getThreshold();
  return SEVERITY_ORDER[severity] >= SEVERITY_ORDER[threshold];
}

/** Request notification permission from the browser. Returns true if granted. */
export async function requestPermission(): Promise<boolean> {
  if (typeof window === "undefined" || !("Notification" in window)) {
    return false;
  }
  if (Notification.permission === "granted") return true;
  if (Notification.permission === "denied") return false;

  const result = await Notification.requestPermission();
  return result === "granted";
}

/** Check if notifications are currently allowed. */
export function isPermissionGranted(): boolean {
  if (typeof window === "undefined" || !("Notification" in window)) {
    return false;
  }
  return Notification.permission === "granted";
}

/** Send a browser notification for a triage item, if it meets the threshold. */
export function notifyIfSevere(
  title: string,
  severity: Severity,
  description?: string,
): boolean {
  if (!isPermissionGranted()) return false;
  if (!meetsThreshold(severity)) return false;

  new Notification(`${SEVERITY_ICONS[severity]} [${severity.toUpperCase()}] ${title}`, {
    body: description ?? "New triage item requires attention.",
    tag: `clarity-${title}`,
  });

  return true;
}

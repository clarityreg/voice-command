/**
 * Shared severity and source design tokens.
 *
 * Single source of truth for icons, badge classes, and background classes
 * used across TriageCard, StatsPage, Dashboard, and notifications.
 */

export type Severity = "critical" | "high" | "medium" | "low";

export const SEVERITY_ICONS: Record<Severity, string> = {
  critical: "\uD83D\uDD34",
  high: "\uD83D\uDFE0",
  medium: "\uD83D\uDFE1",
  low: "\uD83D\uDFE2",
};

export const SEVERITY_CONFIG: Record<Severity, { bg: string; badgeBg: string; icon: string }> = {
  critical: { bg: "bg-sev-critical/15", badgeBg: "bg-sev-critical/40 text-bark", icon: SEVERITY_ICONS.critical },
  high: { bg: "bg-sev-high/15", badgeBg: "bg-sev-high/40 text-bark", icon: SEVERITY_ICONS.high },
  medium: { bg: "bg-sev-medium/15", badgeBg: "bg-sev-medium/40 text-bark", icon: SEVERITY_ICONS.medium },
  low: { bg: "bg-sev-low/15", badgeBg: "bg-sev-low/40 text-bark", icon: SEVERITY_ICONS.low },
};

export const SEVERITY_CARD_BG: Record<Severity, string> = {
  critical: "bg-sev-critical/30",
  high: "bg-sev-high/30",
  medium: "bg-sev-medium/30",
  low: "bg-sev-low/30",
};

export const SOURCE_BADGE: Record<string, string> = {
  posthog: "bg-source-posthog/30 text-bark",
  aikido: "bg-source-aikido/30 text-bark",
};

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/", label: "Focus", icon: "\uD83C\uDFAF" },
  { href: "/inbox", label: "Inbox", icon: "\uD83D\uDCEC" },
  { href: "/triage", label: "Triage", icon: "\u26A1" },
  { href: "/agent", label: "Agent", icon: "🤖" },
  { href: "/dashboard", label: "Events", icon: "\uD83D\uDCCA" },
  { href: "/stats", label: "Stats", icon: "\uD83D\uDCC8" },
  { href: "/settings", label: "Settings", icon: "\u2699\uFE0F" },
];

export default function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 gap-1 rounded-nav bg-nav-bg px-6 py-3 shadow-lg">
      {tabs.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`flex flex-col items-center gap-0.5 rounded-xl px-5 py-1.5 text-xs font-medium transition-all ${
              active
                ? "scale-105 text-sev-high"
                : "text-bark-light hover:text-cream"
            }`}
          >
            <span className="text-lg">{tab.icon}</span>
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}

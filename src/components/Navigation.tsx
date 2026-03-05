"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { navTabs } from "@/lib/navTabs";

export default function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 gap-1 rounded-nav bg-nav-bg px-6 py-3 shadow-lg md:hidden">
      {navTabs.map((tab) => {
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

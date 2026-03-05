"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { navTabs } from "@/lib/navTabs";
import { useVoice } from "@/hooks/useVoice";
import { MicIcon } from "@/components/VoiceButton";

export default function DesktopSidebar() {
  const pathname = usePathname();
  const { state, toggle } = useVoice();

  return (
    <aside className="hidden md:flex md:w-16 lg:w-56 flex-col bg-nav-bg text-cream h-screen sticky top-0 z-30">
      {/* Branding */}
      <div className="flex items-center justify-center px-4 py-5 lg:justify-start">
        <span className="text-lg font-bold tracking-tight lg:hidden">C</span>
        <span className="hidden lg:block text-lg font-bold tracking-tight">Clarity</span>
      </div>

      {/* Nav tabs */}
      <nav className="flex flex-1 flex-col gap-1 px-2">
        {navTabs.map((tab) => {
          const active = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                active
                  ? "bg-white/10 text-sev-high border-l-2 border-sev-high"
                  : "text-cream/70 hover:bg-white/5 hover:text-cream"
              }`}
            >
              <span className="text-lg shrink-0 md:mx-auto lg:mx-0">{tab.icon}</span>
              <span className="hidden lg:inline">{tab.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Voice button at bottom */}
      <div className="px-2 pb-4">
        <button
          onClick={toggle}
          disabled={state === "processing"}
          aria-label="Voice command"
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-white/10 px-3 py-2.5 text-sm font-medium text-cream transition hover:bg-white/20 disabled:opacity-50"
        >
          <MicIcon className="h-5 w-5 shrink-0" />
          <span className="hidden lg:inline">Voice</span>
        </button>
      </div>
    </aside>
  );
}

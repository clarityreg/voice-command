import type { Metadata } from "next";
import "./globals.css";
import Navigation from "@/components/Navigation";
import VoiceButton from "@/components/VoiceButton";
import DesktopSidebar from "@/components/DesktopSidebar";

export const metadata: Metadata = {
  title: "Clarity Command Centre",
  description: "ADHD-friendly triage for errors, vulnerabilities, and tasks",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-cream text-bark antialiased">
        <div className="flex min-h-screen">
          {/* Desktop sidebar — hidden below md */}
          <DesktopSidebar />

          {/* Main content area */}
          <div className="flex flex-1 flex-col">
            {/* Mobile header */}
            <header className="flex items-center justify-center py-2 md:hidden">
              <h1 className="text-lg font-bold tracking-tight text-bark">
                Clarity
              </h1>
            </header>

            <main className="flex-1 p-4 pb-24 md:p-6 md:pb-6 lg:p-8">
              {children}
            </main>
          </div>
        </div>

        {/* Mobile bottom nav — hidden on md+ */}
        <Navigation />
        {/* Mobile floating voice button — hidden on md+ */}
        <VoiceButton />
      </body>
    </html>
  );
}

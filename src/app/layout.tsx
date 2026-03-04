import type { Metadata } from "next";
import "./globals.css";
import Navigation from "@/components/Navigation";
import VoiceButton from "@/components/VoiceButton";

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
        <div className="mx-auto flex min-h-screen max-w-lg flex-col gap-4 p-4 pb-24">
          <header className="flex items-center justify-center py-2">
            <h1 className="text-lg font-bold tracking-tight text-bark">
              Clarity
            </h1>
          </header>
          <main className="flex-1">{children}</main>
        </div>
        <Navigation />
        <VoiceButton />
      </body>
    </html>
  );
}

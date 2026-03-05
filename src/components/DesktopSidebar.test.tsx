import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import DesktopSidebar from "./DesktopSidebar";

vi.mock("next/navigation", () => ({
  usePathname: () => "/inbox",
}));

vi.mock("next/link", () => ({
  default: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

vi.mock("@/hooks/useVoice", () => ({
  useVoice: () => ({ state: "idle", toggle: vi.fn() }),
}));

describe("DesktopSidebar", () => {
  it("renders all seven tabs with correct hrefs", () => {
    render(<DesktopSidebar />);
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(7);

    const hrefs = links.map((l) => l.getAttribute("href"));
    expect(hrefs).toEqual(["/", "/inbox", "/triage", "/agent", "/dashboard", "/stats", "/settings"]);
  });

  it("renders tab labels", () => {
    render(<DesktopSidebar />);
    expect(screen.getByText("Focus")).toBeInTheDocument();
    expect(screen.getByText("Inbox")).toBeInTheDocument();
    expect(screen.getByText("Triage")).toBeInTheDocument();
    expect(screen.getByText("Agent")).toBeInTheDocument();
    expect(screen.getByText("Events")).toBeInTheDocument();
    expect(screen.getByText("Stats")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("highlights the active tab", () => {
    render(<DesktopSidebar />);
    const inboxLink = screen.getByText("Inbox").closest("a");
    expect(inboxLink?.className).toContain("bg-white/10");
  });

  it("renders voice button", () => {
    render(<DesktopSidebar />);
    expect(screen.getByLabelText("Voice command")).toBeInTheDocument();
  });

  it("renders branding", () => {
    render(<DesktopSidebar />);
    expect(screen.getByText("Clarity")).toBeInTheDocument();
  });
});

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Navigation from "./Navigation";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

// Mock next/link to render a plain anchor
vi.mock("next/link", () => ({
  default: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

describe("Navigation", () => {
  it("renders all seven tab labels", () => {
    render(<Navigation />);
    expect(screen.getByText("Focus")).toBeInTheDocument();
    expect(screen.getByText("Inbox")).toBeInTheDocument();
    expect(screen.getByText("Triage")).toBeInTheDocument();
    expect(screen.getByText("Agent")).toBeInTheDocument();
    expect(screen.getByText("Events")).toBeInTheDocument();
    expect(screen.getByText("Stats")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("renders tab links with correct hrefs", () => {
    render(<Navigation />);
    expect(screen.getByText("Focus").closest("a")).toHaveAttribute("href", "/");
    expect(screen.getByText("Inbox").closest("a")).toHaveAttribute("href", "/inbox");
    expect(screen.getByText("Triage").closest("a")).toHaveAttribute("href", "/triage");
    expect(screen.getByText("Agent").closest("a")).toHaveAttribute("href", "/agent");
    expect(screen.getByText("Events").closest("a")).toHaveAttribute("href", "/dashboard");
    expect(screen.getByText("Stats").closest("a")).toHaveAttribute("href", "/stats");
    expect(screen.getByText("Settings").closest("a")).toHaveAttribute("href", "/settings");
  });

  it("highlights the active tab", () => {
    render(<Navigation />);
    const focusLink = screen.getByText("Focus").closest("a");
    expect(focusLink?.className).toContain("scale-105");
  });

  it("has md:hidden class on nav element", () => {
    const { container } = render(<Navigation />);
    const nav = container.querySelector("nav");
    expect(nav?.className).toContain("md:hidden");
  });
});

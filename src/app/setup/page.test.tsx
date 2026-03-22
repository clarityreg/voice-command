import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import SetupPage from "./page";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/lib/notificationApi", () => ({
  getAuthStatus: vi.fn().mockResolvedValue({
    gmail_accounts: [],
    outlook_accounts: [],
  }),
}));

vi.mock("@/lib/api", () => ({
  API_BASE: "http://localhost:8001",
}));

describe("SetupPage", () => {
  beforeEach(() => {
    mockPush.mockClear();
    localStorage.clear();
  });

  it("renders welcome step initially", () => {
    render(<SetupPage />);
    expect(screen.getByText("Welcome to Clarity")).toBeInTheDocument();
    expect(screen.getByText("Get Started")).toBeInTheDocument();
  });

  it("advances to connect step on Get Started click", () => {
    render(<SetupPage />);
    fireEvent.click(screen.getByText("Get Started"));
    expect(screen.getByText("Connect Accounts")).toBeInTheDocument();
  });

  it("shows Gmail and Outlook connect buttons", () => {
    render(<SetupPage />);
    fireEvent.click(screen.getByText("Get Started"));

    const gmailLink = screen.getAllByText("Connect")[0].closest("a");
    expect(gmailLink).toHaveAttribute("href", "http://localhost:8001/auth/google/start");

    const outlookLink = screen.getAllByText("Connect")[1].closest("a");
    expect(outlookLink).toHaveAttribute("href", "http://localhost:8001/auth/microsoft/start");
  });

  it("advances to done step and navigates to inbox", () => {
    render(<SetupPage />);
    fireEvent.click(screen.getByText("Get Started"));
    fireEvent.click(screen.getByText("Continue"));
    expect(screen.getByText("You're all set!")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Go to Inbox"));
    expect(localStorage.getItem("clarity-setup-complete")).toBe("true");
    expect(mockPush).toHaveBeenCalledWith("/inbox");
  });

  it("skip link advances to done step", () => {
    render(<SetupPage />);
    fireEvent.click(screen.getByText("Get Started"));
    fireEvent.click(screen.getByText("Skip"));
    expect(screen.getByText("You're all set!")).toBeInTheDocument();
  });
});

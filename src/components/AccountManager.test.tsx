import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock API modules
vi.mock("@/lib/notificationApi", () => ({
  getAuthStatus: vi.fn(),
  getServiceStatuses: vi.fn(),
  removeGmailAccount: vi.fn(),
  removeOutlookAccount: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  API_BASE: "http://localhost:8070",
}));

import AccountManager from "./AccountManager";
import { getAuthStatus, getServiceStatuses, removeGmailAccount, removeOutlookAccount } from "@/lib/notificationApi";

const mockGetAuthStatus = vi.mocked(getAuthStatus);
const mockGetServiceStatuses = vi.mocked(getServiceStatuses);
const mockRemoveGmail = vi.mocked(removeGmailAccount);
const mockRemoveOutlook = vi.mocked(removeOutlookAccount);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AccountManager", () => {
  it("shows loading state initially", () => {
    // Never resolve the promises
    mockGetAuthStatus.mockReturnValue(new Promise(() => {}));
    mockGetServiceStatuses.mockReturnValue(new Promise(() => {}));

    render(<AccountManager />);
    expect(screen.getByText("Loading accounts...")).toBeDefined();
  });

  it("renders empty state when no accounts configured", async () => {
    mockGetAuthStatus.mockResolvedValue({
      gmail_accounts: [],
      outlook_accounts: [],
    });
    mockGetServiceStatuses.mockResolvedValue({ services: [] });

    render(<AccountManager />);

    await waitFor(() => {
      expect(screen.getByText("No Gmail accounts connected.")).toBeDefined();
      expect(screen.getByText("No Outlook accounts connected.")).toBeDefined();
      expect(screen.getByText("No services configured.")).toBeDefined();
    });
  });

  it("renders gmail accounts with connection indicators", async () => {
    mockGetAuthStatus.mockResolvedValue({
      gmail_accounts: [{ email: "test@gmail.com", connected: true }],
      outlook_accounts: [],
    });
    mockGetServiceStatuses.mockResolvedValue({ services: [] });

    render(<AccountManager />);

    await waitFor(() => {
      expect(screen.getByText("test@gmail.com")).toBeDefined();
    });
  });

  it("renders outlook accounts", async () => {
    mockGetAuthStatus.mockResolvedValue({
      gmail_accounts: [],
      outlook_accounts: [{ email: "test@outlook.com", connected: false }],
    });
    mockGetServiceStatuses.mockResolvedValue({ services: [] });

    render(<AccountManager />);

    await waitFor(() => {
      expect(screen.getByText("test@outlook.com")).toBeDefined();
    });
  });

  it("renders service statuses", async () => {
    mockGetAuthStatus.mockResolvedValue({
      gmail_accounts: [],
      outlook_accounts: [],
    });
    mockGetServiceStatuses.mockResolvedValue({
      services: [
        { service: "posthog", connected: true, account: "PostHog" },
        { service: "slack", connected: false, account: "workspace-1" },
      ],
    });

    render(<AccountManager />);

    await waitFor(() => {
      expect(screen.getByText("posthog")).toBeDefined();
      expect(screen.getByText("PostHog")).toBeDefined();
      expect(screen.getByText("Connected")).toBeDefined();
      expect(screen.getByText("slack")).toBeDefined();
      expect(screen.getByText("Disconnected")).toBeDefined();
    });
  });

  it("calls removeGmailAccount on remove button click", async () => {
    mockGetAuthStatus.mockResolvedValue({
      gmail_accounts: [{ email: "test@gmail.com", connected: true }],
      outlook_accounts: [],
    });
    mockGetServiceStatuses.mockResolvedValue({ services: [] });
    mockRemoveGmail.mockResolvedValue(undefined);

    render(<AccountManager />);

    await waitFor(() => {
      expect(screen.getByText("test@gmail.com")).toBeDefined();
    });

    const removeButtons = screen.getAllByText("Remove");
    fireEvent.click(removeButtons[0]);

    await waitFor(() => {
      expect(mockRemoveGmail).toHaveBeenCalledWith("test@gmail.com");
    });
  });

  it("calls removeOutlookAccount on remove button click", async () => {
    mockGetAuthStatus.mockResolvedValue({
      gmail_accounts: [],
      outlook_accounts: [{ email: "test@outlook.com", connected: true }],
    });
    mockGetServiceStatuses.mockResolvedValue({ services: [] });
    mockRemoveOutlook.mockResolvedValue(undefined);

    render(<AccountManager />);

    await waitFor(() => {
      expect(screen.getByText("test@outlook.com")).toBeDefined();
    });

    const removeButtons = screen.getAllByText("Remove");
    fireEvent.click(removeButtons[0]);

    await waitFor(() => {
      expect(mockRemoveOutlook).toHaveBeenCalledWith("test@outlook.com");
    });
  });

  it("refresh button refetches data", async () => {
    mockGetAuthStatus.mockResolvedValue({
      gmail_accounts: [],
      outlook_accounts: [],
    });
    mockGetServiceStatuses.mockResolvedValue({ services: [] });

    render(<AccountManager />);

    await waitFor(() => {
      expect(screen.getByText("Refresh")).toBeDefined();
    });

    // Initial load
    expect(mockGetAuthStatus).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText("Refresh"));

    await waitFor(() => {
      expect(mockGetAuthStatus).toHaveBeenCalledTimes(2);
    });
  });

  it("handles API errors gracefully", async () => {
    mockGetAuthStatus.mockRejectedValue(new Error("Network error"));
    mockGetServiceStatuses.mockRejectedValue(new Error("Network error"));

    render(<AccountManager />);

    // Should render without crashing, showing empty state
    await waitFor(() => {
      expect(screen.getByText("No Gmail accounts connected.")).toBeDefined();
    });
  });

  it("renders Add Gmail Account link with correct href", async () => {
    mockGetAuthStatus.mockResolvedValue({
      gmail_accounts: [],
      outlook_accounts: [],
    });
    mockGetServiceStatuses.mockResolvedValue({ services: [] });

    render(<AccountManager />);

    await waitFor(() => {
      const link = screen.getByText("Add Gmail Account");
      expect(link.getAttribute("href")).toBe("http://localhost:8070/auth/google/start");
    });
  });

  it("renders Add Outlook Account link with correct href", async () => {
    mockGetAuthStatus.mockResolvedValue({
      gmail_accounts: [],
      outlook_accounts: [],
    });
    mockGetServiceStatuses.mockResolvedValue({ services: [] });

    render(<AccountManager />);

    await waitFor(() => {
      const link = screen.getByText("Add Outlook Account");
      expect(link.getAttribute("href")).toBe("http://localhost:8070/auth/microsoft/start");
    });
  });
});

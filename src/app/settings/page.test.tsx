import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import SettingsPage from "./page";

vi.mock("@/lib/api", () => ({
  getSettings: vi.fn(),
  updateSettings: vi.fn(),
}));

vi.mock("@/components/AccountManager", () => ({ default: () => <div data-testid="account-manager" /> }));
vi.mock("@/components/NotificationSettings", () => ({ default: () => <div data-testid="notification-settings" /> }));
vi.mock("@/components/TtsSettings", () => ({ default: () => <div data-testid="tts-settings" /> }));
vi.mock("@/components/WhisperSetup", () => ({ default: () => <div data-testid="whisper-setup" /> }));
vi.mock("@/components/VocabularyEditor", () => ({ default: () => <div data-testid="vocabulary-editor" /> }));

import { getSettings, updateSettings } from "@/lib/api";
const mockedGetSettings = vi.mocked(getSettings);
const mockedUpdateSettings = vi.mocked(updateSettings);

const defaultSettings = {
  plane_api_key: "",
  plane_workspace_slug: "",
  plane_project_id: "",
  aikido_webhook_secret: "",
  focus_minutes: 25,
  break_minutes: 5,
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("SettingsPage", () => {
  it("shows loading skeleton initially", () => {
    mockedGetSettings.mockReturnValue(new Promise(() => {}));
    render(<SettingsPage />);
    // Skeleton placeholders render (animate-pulse divs)
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders form with loaded settings", async () => {
    mockedGetSettings.mockResolvedValue(defaultSettings);
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText("Settings")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Workspace Slug")).toBeInTheDocument();
    expect(screen.getByLabelText("Focus (min)")).toHaveValue(25);
    expect(screen.getByLabelText("Break (min)")).toHaveValue(5);
  });

  it("shows error when API fails", async () => {
    mockedGetSettings.mockRejectedValue(new Error("Network error"));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("calls updateSettings on save", async () => {
    mockedGetSettings.mockResolvedValue(defaultSettings);
    mockedUpdateSettings.mockResolvedValue({ ...defaultSettings, focus_minutes: 30 });
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByLabelText("Focus (min)")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Focus (min)"), { target: { value: "30" } });
    fireEvent.click(screen.getByText("Save Settings"));

    await waitFor(() => {
      expect(mockedUpdateSettings).toHaveBeenCalledWith(
        expect.objectContaining({ focus_minutes: 30 }),
      );
    });
  });

  it("shows saved confirmation after successful save", async () => {
    mockedGetSettings.mockResolvedValue(defaultSettings);
    mockedUpdateSettings.mockResolvedValue(defaultSettings);
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText("Save Settings")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Save Settings"));
    await waitFor(() => {
      expect(screen.getByText(/Saved/)).toBeInTheDocument();
    });
  });

  it("resets form on Reset button click", async () => {
    mockedGetSettings.mockResolvedValue(defaultSettings);
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByLabelText("Focus (min)")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Focus (min)"), { target: { value: "45" } });
    expect(screen.getByLabelText("Focus (min)")).toHaveValue(45);

    // Reset reloads from API
    mockedGetSettings.mockResolvedValue(defaultSettings);
    fireEvent.click(screen.getByText("Reset"));
    await waitFor(() => {
      expect(screen.getByLabelText("Focus (min)")).toHaveValue(25);
    });
  });

  it("renders all three sections", async () => {
    mockedGetSettings.mockResolvedValue(defaultSettings);
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText("Plane Integration")).toBeInTheDocument();
    });
    expect(screen.getByText("Aikido Webhook")).toBeInTheDocument();
    expect(screen.getByText("Timer")).toBeInTheDocument();
    expect(screen.getByTestId("tts-settings")).toBeInTheDocument();
  });
});

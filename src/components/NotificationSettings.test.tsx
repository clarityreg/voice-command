import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import NotificationSettings from "./NotificationSettings";

vi.mock("@/lib/notifications", () => ({
  getThreshold: vi.fn(() => "high"),
  setThreshold: vi.fn(),
  isPermissionGranted: vi.fn(() => false),
  requestPermission: vi.fn(async () => true),
}));

import {
  isPermissionGranted,
  requestPermission,
  setThreshold,
} from "@/lib/notifications";

describe("NotificationSettings", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(isPermissionGranted).mockReturnValue(false);
  });

  it("shows enable button when not permitted", () => {
    render(<NotificationSettings />);
    expect(screen.getByText("Enable")).toBeInTheDocument();
  });

  it("requests permission on enable click", async () => {
    vi.mocked(requestPermission).mockResolvedValue(true);
    render(<NotificationSettings />);
    fireEvent.click(screen.getByText("Enable"));
    expect(requestPermission).toHaveBeenCalledOnce();
  });

  it("shows threshold buttons when permitted", () => {
    vi.mocked(isPermissionGranted).mockReturnValue(true);
    render(<NotificationSettings />);
    expect(screen.getByText("critical")).toBeInTheDocument();
    expect(screen.getByText("high")).toBeInTheDocument();
    expect(screen.getByText("medium")).toBeInTheDocument();
    expect(screen.getByText("low")).toBeInTheDocument();
  });

  it("calls setThreshold when button clicked", () => {
    vi.mocked(isPermissionGranted).mockReturnValue(true);
    render(<NotificationSettings />);
    fireEvent.click(screen.getByText("critical"));
    expect(setThreshold).toHaveBeenCalledWith("critical");
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getThreshold,
  setThreshold,
  meetsThreshold,
  isPermissionGranted,
  notifyIfSevere,
} from "./notifications";

describe("notifications", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  describe("getThreshold / setThreshold", () => {
    it("defaults to high", () => {
      expect(getThreshold()).toBe("high");
    });

    it("persists threshold in localStorage", () => {
      setThreshold("critical");
      expect(getThreshold()).toBe("critical");
    });

    it("can be set to low", () => {
      setThreshold("low");
      expect(getThreshold()).toBe("low");
    });
  });

  describe("meetsThreshold", () => {
    it("critical meets high threshold", () => {
      setThreshold("high");
      expect(meetsThreshold("critical")).toBe(true);
    });

    it("low does not meet high threshold", () => {
      setThreshold("high");
      expect(meetsThreshold("low")).toBe(false);
    });

    it("medium meets medium threshold", () => {
      setThreshold("medium");
      expect(meetsThreshold("medium")).toBe(true);
    });

    it("high meets low threshold", () => {
      setThreshold("low");
      expect(meetsThreshold("high")).toBe(true);
    });
  });

  describe("isPermissionGranted", () => {
    it("returns false when Notification is not available", () => {
      const orig = globalThis.Notification;
      // @ts-expect-error testing absence
      delete globalThis.Notification;
      expect(isPermissionGranted()).toBe(false);
      globalThis.Notification = orig;
    });

    it("returns true when permission is granted", () => {
      Object.defineProperty(globalThis, "Notification", {
        value: { permission: "granted" },
        writable: true,
        configurable: true,
      });
      expect(isPermissionGranted()).toBe(true);
    });

    it("returns false when permission is denied", () => {
      Object.defineProperty(globalThis, "Notification", {
        value: { permission: "denied" },
        writable: true,
        configurable: true,
      });
      expect(isPermissionGranted()).toBe(false);
    });
  });

  describe("notifyIfSevere", () => {
    it("returns false when notifications not permitted", () => {
      Object.defineProperty(globalThis, "Notification", {
        value: { permission: "denied" },
        writable: true,
        configurable: true,
      });
      expect(notifyIfSevere("Error", "critical")).toBe(false);
    });

    it("returns false when severity below threshold", () => {
      const MockNotification = vi.fn();
      MockNotification.permission = "granted";
      Object.defineProperty(globalThis, "Notification", {
        value: MockNotification,
        writable: true,
        configurable: true,
      });
      setThreshold("critical");
      expect(notifyIfSevere("Error", "low")).toBe(false);
    });

    it("creates notification when severity meets threshold", () => {
      const MockNotification = vi.fn();
      MockNotification.permission = "granted";
      Object.defineProperty(globalThis, "Notification", {
        value: MockNotification,
        writable: true,
        configurable: true,
      });
      setThreshold("high");
      const result = notifyIfSevere("DB error", "critical", "Connection lost");
      expect(result).toBe(true);
      expect(MockNotification).toHaveBeenCalledOnce();
      expect(MockNotification.mock.calls[0][0]).toContain("CRITICAL");
      expect(MockNotification.mock.calls[0][0]).toContain("DB error");
    });
  });
});

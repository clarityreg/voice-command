import { describe, it, expect, beforeEach } from "vitest";
import { isTauri } from "./whisper";

describe("whisper bridge", () => {
  beforeEach(() => {
    // Clean up any __TAURI_INTERNALS__ from previous tests
    if ("__TAURI_INTERNALS__" in window) {
      delete (window as Record<string, unknown>).__TAURI_INTERNALS__;
    }
  });

  it("isTauri returns false in jsdom (no __TAURI_INTERNALS__)", () => {
    expect(isTauri()).toBe(false);
  });

  it("isTauri returns true when __TAURI_INTERNALS__ is set", () => {
    (window as Record<string, unknown>).__TAURI_INTERNALS__ = {};
    expect(isTauri()).toBe(true);
  });
});

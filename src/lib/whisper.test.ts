import { describe, it, expect, vi, beforeEach } from "vitest";
import { isTauri, getModelStatus, downloadModel, loadModel, transcribe, getCustomVocab, saveCustomVocab } from "./whisper";

// Mock @tauri-apps/api/core
const mockInvoke = vi.fn();
vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => mockInvoke(...args),
}));

// Mock @tauri-apps/api/event
const mockListen = vi.fn();
vi.mock("@tauri-apps/api/event", () => ({
  listen: (...args: unknown[]) => mockListen(...args),
}));

describe("whisper bridge", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

  it("getModelStatus invokes whisper_model_status", async () => {
    const status = { model_exists: true, model_loaded: false, model_path: "/path/to/model" };
    mockInvoke.mockResolvedValueOnce(status);
    const result = await getModelStatus();
    expect(result).toEqual(status);
    expect(mockInvoke).toHaveBeenCalledWith("whisper_model_status", undefined);
  });

  it("downloadModel invokes with default model name", async () => {
    mockInvoke.mockResolvedValueOnce("/path/to/model");
    const result = await downloadModel();
    expect(result).toBe("/path/to/model");
    expect(mockInvoke).toHaveBeenCalledWith("download_whisper_model", { modelName: "small.en" });
  });

  it("downloadModel invokes with custom model name", async () => {
    mockInvoke.mockResolvedValueOnce("/path/to/base");
    await downloadModel("base.en");
    expect(mockInvoke).toHaveBeenCalledWith("download_whisper_model", { modelName: "base.en" });
  });

  it("loadModel invokes load_whisper_model", async () => {
    mockInvoke.mockResolvedValueOnce(undefined);
    await loadModel();
    expect(mockInvoke).toHaveBeenCalledWith("load_whisper_model", undefined);
  });

  it("transcribe invokes with audio data and sample rate", async () => {
    mockInvoke.mockResolvedValueOnce("hello world");
    const data = new Uint8Array([1, 2, 3]);
    const result = await transcribe(data, 16000);
    expect(result).toBe("hello world");
    expect(mockInvoke).toHaveBeenCalledWith("transcribe_audio", {
      audioData: [1, 2, 3],
      sampleRate: 16000,
    });
  });

  it("getCustomVocab invokes get_custom_vocab", async () => {
    mockInvoke.mockResolvedValueOnce(["Clarity", "Plane"]);
    const result = await getCustomVocab();
    expect(result).toEqual(["Clarity", "Plane"]);
    expect(mockInvoke).toHaveBeenCalledWith("get_custom_vocab", undefined);
  });

  it("saveCustomVocab invokes save_custom_vocab", async () => {
    mockInvoke.mockResolvedValueOnce(undefined);
    await saveCustomVocab(["Test", "Term"]);
    expect(mockInvoke).toHaveBeenCalledWith("save_custom_vocab", { terms: ["Test", "Term"] });
  });
});

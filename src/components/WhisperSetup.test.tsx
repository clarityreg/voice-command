import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import WhisperSetup from "./WhisperSetup";

vi.mock("@/lib/whisper", () => ({
  isTauri: vi.fn(() => false),
  getModelStatus: vi.fn(),
  downloadModel: vi.fn(),
  onDownloadProgress: vi.fn(),
  loadModel: vi.fn(),
}));

import { isTauri, getModelStatus } from "@/lib/whisper";
const mockedIsTauri = vi.mocked(isTauri);
const mockedGetModelStatus = vi.mocked(getModelStatus);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("WhisperSetup", () => {
  it("renders nothing when not in Tauri", () => {
    mockedIsTauri.mockReturnValue(false);
    const { container } = render(<WhisperSetup />);
    expect(container.firstChild).toBeNull();
  });

  it("shows checking state initially in Tauri", () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetModelStatus.mockReturnValue(new Promise(() => {})); // never resolves
    render(<WhisperSetup />);
    expect(screen.getByText("Checking whisper model...")).toBeInTheDocument();
  });

  it("shows download buttons when model not found", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetModelStatus.mockResolvedValue({
      model_exists: false,
      model_loaded: false,
      model_path: "/path/to/model",
    });

    render(<WhisperSetup />);

    expect(
      await screen.findByText("Download a speech recognition model to enable local voice commands."),
    ).toBeInTheDocument();
    expect(screen.getByText("small.en (~460 MB)")).toBeInTheDocument();
    expect(screen.getByText("base.en (~140 MB)")).toBeInTheDocument();
  });

  it("shows ready state when model is loaded", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetModelStatus.mockResolvedValue({
      model_exists: true,
      model_loaded: true,
      model_path: "/home/user/.clarity/models/ggml-small.en.bin",
    });

    render(<WhisperSetup />);
    expect(await screen.findByText("Local voice recognition ready")).toBeInTheDocument();
  });
});

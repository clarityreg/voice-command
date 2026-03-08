import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import WhisperSetup from "./WhisperSetup";

vi.mock("@/lib/whisper", () => ({
  isTauri: vi.fn(() => false),
  getModelStatus: vi.fn(),
  downloadModel: vi.fn(),
  onDownloadProgress: vi.fn(),
  loadModel: vi.fn(),
}));

import { isTauri, getModelStatus, downloadModel, onDownloadProgress, loadModel } from "@/lib/whisper";
const mockedIsTauri = vi.mocked(isTauri);
const mockedGetModelStatus = vi.mocked(getModelStatus);
const mockedDownloadModel = vi.mocked(downloadModel);
const mockedOnDownloadProgress = vi.mocked(onDownloadProgress);
const mockedLoadModel = vi.mocked(loadModel);

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
    expect(screen.getByText("/home/user/.clarity/models/ggml-small.en.bin")).toBeInTheDocument();
  });

  it("auto-loads model when exists but not loaded", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetModelStatus.mockResolvedValue({
      model_exists: true,
      model_loaded: false,
      model_path: "/path/to/model.bin",
    });
    mockedLoadModel.mockResolvedValue(undefined);
    const onReady = vi.fn();

    render(<WhisperSetup onReady={onReady} />);
    await waitFor(() => {
      expect(mockedLoadModel).toHaveBeenCalled();
      expect(screen.getByText("Local voice recognition ready")).toBeInTheDocument();
    });
    expect(onReady).toHaveBeenCalled();
  });

  it("shows error when model status check fails", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetModelStatus.mockRejectedValue(new Error("check failed"));

    render(<WhisperSetup />);
    await waitFor(() => {
      expect(screen.getByText("Error: check failed")).toBeInTheDocument();
      expect(screen.getByText("Retry Download")).toBeInTheDocument();
    });
  });

  it("shows error when load model fails", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetModelStatus.mockResolvedValue({
      model_exists: true,
      model_loaded: false,
      model_path: "/path/to/model.bin",
    });
    mockedLoadModel.mockRejectedValue(new Error("load failed"));

    render(<WhisperSetup />);
    await waitFor(() => {
      expect(screen.getByText("Error: load failed")).toBeInTheDocument();
    });
  });

  it("downloads model when download button clicked", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetModelStatus.mockResolvedValue({
      model_exists: false,
      model_loaded: false,
      model_path: "",
    });
    const unlisten = vi.fn();
    mockedOnDownloadProgress.mockResolvedValue(unlisten);
    mockedDownloadModel.mockResolvedValue("/path/to/model");
    mockedLoadModel.mockResolvedValue(undefined);

    render(<WhisperSetup />);
    await waitFor(() => {
      expect(screen.getByText("small.en (~460 MB)")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("small.en (~460 MB)"));
    await waitFor(() => {
      expect(mockedDownloadModel).toHaveBeenCalledWith("small.en");
      expect(mockedLoadModel).toHaveBeenCalled();
    });
  });

  it("retries download on error state button click", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetModelStatus.mockRejectedValue(new Error("fail"));

    render(<WhisperSetup />);
    await waitFor(() => {
      expect(screen.getByText("Retry Download")).toBeInTheDocument();
    });

    const unlisten = vi.fn();
    mockedOnDownloadProgress.mockResolvedValue(unlisten);
    mockedDownloadModel.mockResolvedValue("/model");
    mockedLoadModel.mockResolvedValue(undefined);

    fireEvent.click(screen.getByText("Retry Download"));
    await waitFor(() => {
      expect(mockedDownloadModel).toHaveBeenCalled();
    });
  });

  it("shows download progress state", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetModelStatus.mockResolvedValue({
      model_exists: false,
      model_loaded: false,
      model_path: "",
    });

    let progressCallback: ((p: { percent: number }) => void) | undefined;
    mockedOnDownloadProgress.mockImplementation(async (cb) => {
      progressCallback = cb as (p: { percent: number }) => void;
      return vi.fn();
    });
    // Make download hang so we can see the downloading state
    mockedDownloadModel.mockReturnValue(new Promise(() => {}));

    render(<WhisperSetup />);
    await waitFor(() => {
      expect(screen.getByText("small.en (~460 MB)")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("small.en (~460 MB)"));
    await waitFor(() => {
      expect(screen.getByText(/Downloading model/)).toBeInTheDocument();
    });
  });
});

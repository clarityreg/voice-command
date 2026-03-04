/**
 * Tauri IPC bridge for whisper.cpp local speech-to-text.
 *
 * When running inside Tauri, these functions invoke Rust commands.
 * When running in a browser (dev mode), isTauri() returns false
 * and the caller should fall back to Web Speech API.
 */

type ModelStatus = {
  model_exists: boolean;
  model_loaded: boolean;
  model_path: string;
};

type DownloadProgress = {
  downloaded: number;
  total: number;
  percent: number;
};

export function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke: tauriInvoke } = await import("@tauri-apps/api/core");
  return tauriInvoke<T>(cmd, args);
}

export async function getModelStatus(): Promise<ModelStatus> {
  return invoke<ModelStatus>("whisper_model_status");
}

export async function downloadModel(modelName?: string): Promise<string> {
  return invoke<string>("download_whisper_model", {
    modelName: modelName ?? "small.en",
  });
}

export async function onDownloadProgress(
  callback: (progress: DownloadProgress) => void,
): Promise<() => void> {
  const { listen } = await import("@tauri-apps/api/event");
  const unlisten = await listen<DownloadProgress>("whisper-download-progress", (event) => {
    callback(event.payload);
  });
  return unlisten;
}

export async function loadModel(): Promise<void> {
  await invoke<void>("load_whisper_model");
}

export async function transcribe(
  audioData: Uint8Array,
  sampleRate: number,
): Promise<string> {
  return invoke<string>("transcribe_audio", {
    audioData: Array.from(audioData),
    sampleRate,
  });
}

export async function getCustomVocab(): Promise<string[]> {
  return invoke<string[]>("get_custom_vocab");
}

export async function saveCustomVocab(terms: string[]): Promise<void> {
  await invoke<void>("save_custom_vocab", { terms });
}

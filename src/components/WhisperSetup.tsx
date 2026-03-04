"use client";

import { useCallback, useEffect, useState } from "react";
import {
  isTauri,
  getModelStatus,
  downloadModel,
  onDownloadProgress,
  loadModel,
} from "@/lib/whisper";

type SetupState = "checking" | "needs-download" | "downloading" | "loading" | "ready" | "error";

export default function WhisperSetup({ onReady }: { onReady?: () => void }) {
  const [setupState, setSetupState] = useState<SetupState>("checking");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [modelPath, setModelPath] = useState("");

  useEffect(() => {
    if (!isTauri()) return;

    getModelStatus()
      .then((status) => {
        setModelPath(status.model_path);
        if (status.model_loaded) {
          setSetupState("ready");
        } else if (status.model_exists) {
          setSetupState("loading");
          loadModel()
            .then(() => {
              setSetupState("ready");
              onReady?.();
            })
            .catch((e) => {
              setSetupState("error");
              setError(String(e));
            });
        } else {
          setSetupState("needs-download");
        }
      })
      .catch((e) => {
        setSetupState("error");
        setError(String(e));
      });
  }, [onReady]);

  const handleDownload = useCallback(
    async (modelName?: string) => {
      setSetupState("downloading");
      setProgress(0);
      setError(null);

      let unlisten: (() => void) | undefined;
      try {
        unlisten = await onDownloadProgress((p) => {
          setProgress(Math.round(p.percent));
        });

        await downloadModel(modelName);
        unlisten?.();

        setSetupState("loading");
        await loadModel();
        setSetupState("ready");
        onReady?.();
      } catch (e) {
        unlisten?.();
        setSetupState("error");
        setError(String(e));
      }
    },
    [onReady],
  );

  if (!isTauri()) return null;

  if (setupState === "checking") {
    return (
      <div className="rounded-card bg-card-bg p-4 shadow-card">
        <p className="text-sm text-bark-muted">Checking whisper model...</p>
      </div>
    );
  }

  if (setupState === "ready") {
    return (
      <div className="rounded-card bg-card-bg p-4 shadow-card">
        <p className="text-sm text-bark">Local voice recognition ready</p>
        <p className="mt-1 text-xs text-bark-muted">{modelPath}</p>
      </div>
    );
  }

  if (setupState === "downloading") {
    return (
      <div className="rounded-card bg-card-bg p-4 shadow-card">
        <p className="mb-2 text-sm font-medium text-bark">Downloading model... {progress}%</p>
        <div className="h-2 overflow-hidden rounded-full bg-cream-dark">
          <div
            className="h-full rounded-full bg-accent transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    );
  }

  if (setupState === "loading") {
    return (
      <div className="rounded-card bg-card-bg p-4 shadow-card">
        <p className="text-sm text-bark-muted">Loading model into memory...</p>
      </div>
    );
  }

  if (setupState === "error") {
    return (
      <div className="rounded-card bg-card-bg p-4 shadow-card">
        <p className="text-sm text-sev-critical">{error}</p>
        <button
          onClick={() => handleDownload()}
          className="mt-2 rounded-pill bg-nav-bg px-4 py-1.5 text-xs font-medium text-cream hover:opacity-90"
        >
          Retry Download
        </button>
      </div>
    );
  }

  // needs-download
  return (
    <div className="rounded-card bg-card-bg p-4 shadow-card">
      <p className="mb-2 text-sm font-medium text-bark">
        Download a speech recognition model to enable local voice commands.
      </p>
      <div className="flex gap-2">
        <button
          onClick={() => handleDownload("small.en")}
          className="rounded-pill bg-nav-bg px-4 py-1.5 text-xs font-medium text-cream hover:opacity-90"
        >
          small.en (~460 MB)
        </button>
        <button
          onClick={() => handleDownload("base.en")}
          className="rounded-pill bg-cream-dark px-4 py-1.5 text-xs font-medium text-bark hover:opacity-80"
        >
          base.en (~140 MB)
        </button>
      </div>
      <p className="mt-2 text-xs text-bark-muted">
        small.en is recommended for best accuracy. base.en is lighter for limited storage.
      </p>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { isTauri, getModelStatus } from "@/lib/whisper";

type SttStatus = "whisper" | "web-speech" | "none" | "loading";

export default function TtsSettings() {
  const [sttStatus, setSttStatus] = useState<SttStatus>("loading");
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoiceUri, setSelectedVoiceUri] = useState<string>("");
  const [rate, setRate] = useState(1.0);

  // Detect STT backend
  useEffect(() => {
    async function detect() {
      if (isTauri()) {
        try {
          const status = await getModelStatus();
          if (status.model_loaded || status.model_exists) {
            setSttStatus("whisper");
            return;
          }
        } catch {
          // Fall through
        }
      }

      const SpeechRecognitionAPI =
        typeof window !== "undefined"
          ? window.SpeechRecognition || window.webkitSpeechRecognition
          : null;
      setSttStatus(SpeechRecognitionAPI ? "web-speech" : "none");
    }
    detect();
  }, []);

  // Load voices
  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;

    function loadVoices() {
      const available = speechSynthesis.getVoices();
      setVoices(available);
    }

    loadVoices();
    speechSynthesis.addEventListener("voiceschanged", loadVoices);
    return () => speechSynthesis.removeEventListener("voiceschanged", loadVoices);
  }, []);

  // Load saved preferences
  useEffect(() => {
    const savedUri = localStorage.getItem("clarity-tts-voice-uri");
    const savedRate = localStorage.getItem("clarity-tts-rate");
    if (savedUri) setSelectedVoiceUri(savedUri);
    if (savedRate) setRate(parseFloat(savedRate));
  }, []);

  const handleVoiceChange = useCallback((uri: string) => {
    setSelectedVoiceUri(uri);
    localStorage.setItem("clarity-tts-voice-uri", uri);
  }, []);

  const handleRateChange = useCallback((newRate: number) => {
    setRate(newRate);
    localStorage.setItem("clarity-tts-rate", String(newRate));
  }, []);

  const handlePreview = useCallback(() => {
    if (!("speechSynthesis" in window)) return;
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance("Clarity is ready.");
    if (selectedVoiceUri) {
      const match = voices.find((v) => v.voiceURI === selectedVoiceUri);
      if (match) utterance.voice = match;
    }
    utterance.rate = rate;
    speechSynthesis.speak(utterance);
  }, [selectedVoiceUri, voices, rate]);

  const sttLabel: Record<SttStatus, string> = {
    loading: "Detecting...",
    whisper: "Whisper (local)",
    "web-speech": "Web Speech API (browser)",
    none: "Not supported",
  };

  const sttDotColor: Record<SttStatus, string> = {
    loading: "bg-bark-muted",
    whisper: "bg-sev-low",
    "web-speech": "bg-sev-low",
    none: "bg-sev-critical",
  };

  return (
    <div className="flex flex-col gap-4">
      {/* STT backend indicator */}
      <div className="flex flex-col gap-1">
        <span className="text-xs font-medium text-bark-muted">Speech-to-Text</span>
        <div className="flex items-center gap-2">
          <span className={`inline-block h-2.5 w-2.5 rounded-full ${sttDotColor[sttStatus]}`} />
          <span className="text-sm text-bark">{sttLabel[sttStatus]}</span>
        </div>
        <p className="text-xs text-bark-muted">
          Keyboard shortcut: <kbd className="rounded bg-cream-dark px-1 py-0.5 text-xs font-mono">⌘⇧Space</kbd>
        </p>
      </div>

      {/* TTS voice dropdown */}
      <label className="flex flex-col gap-1">
        <span className="text-xs font-medium text-bark-muted">TTS Voice</span>
        <select
          value={selectedVoiceUri}
          onChange={(e) => handleVoiceChange(e.target.value)}
          className="rounded-lg border border-cream-dark bg-cream-light px-3 py-2 text-sm text-bark outline-none focus:border-accent"
        >
          <option value="">System default</option>
          {voices.map((v) => (
            <option key={v.voiceURI} value={v.voiceURI}>
              {v.name} ({v.lang})
            </option>
          ))}
        </select>
      </label>

      {/* Speech rate slider */}
      <label className="flex flex-col gap-1">
        <span className="text-xs font-medium text-bark-muted">
          Speech Rate: {rate.toFixed(1)}x
        </span>
        <input
          type="range"
          min="0.5"
          max="2.0"
          step="0.1"
          value={rate}
          onChange={(e) => handleRateChange(parseFloat(e.target.value))}
          className="w-full accent-accent"
        />
        <div className="flex justify-between text-xs text-bark-muted">
          <span>0.5x</span>
          <span>2.0x</span>
        </div>
      </label>

      {/* Preview button */}
      <button
        onClick={handlePreview}
        className="self-start rounded-pill bg-cream-dark px-4 py-2 text-sm font-medium text-bark transition hover:opacity-80"
      >
        Preview Voice
      </button>
    </div>
  );
}

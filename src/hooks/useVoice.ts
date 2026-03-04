"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { processVoice, type VoiceResponse } from "@/lib/api";
import {
  isTauri,
  getModelStatus,
  transcribe as whisperTranscribe,
} from "@/lib/whisper";
import { useAudioCapture } from "@/hooks/useAudioCapture";

export type VoiceState = "idle" | "listening" | "processing" | "speaking";
export type SttBackend = "whisper" | "web-speech" | "none";

export interface UseVoiceReturn {
  state: VoiceState;
  sttBackend: SttBackend;
  lastResponse: string | null;
  audioLevel: number;
  toggle: () => void;
  dismissResponse: () => void;
}

export function useVoice(): UseVoiceReturn {
  const [state, setState] = useState<VoiceState>("idle");
  const [lastResponse, setLastResponse] = useState<string | null>(null);
  const [sttBackend, setSttBackend] = useState<SttBackend>("none");
  const [audioLevel, setAudioLevel] = useState(0);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const { startCapture, stopCapture } = useAudioCapture();

  // Detect STT backend on mount
  useEffect(() => {
    async function detectBackend() {
      if (isTauri()) {
        try {
          const status = await getModelStatus();
          if (status.model_loaded || status.model_exists) {
            setSttBackend("whisper");
            return;
          }
        } catch {
          // Fall through to web-speech
        }
      }

      const SpeechRecognitionAPI =
        typeof window !== "undefined"
          ? window.SpeechRecognition || window.webkitSpeechRecognition
          : null;
      setSttBackend(SpeechRecognitionAPI ? "web-speech" : "none");
    }
    detectBackend();
  }, []);

  const speak = useCallback((text: string) => {
    if (!("speechSynthesis" in window)) return;
    const utterance = new SpeechSynthesisUtterance(text);

    // Read TTS preferences from localStorage
    const savedVoiceUri =
      typeof localStorage !== "undefined"
        ? localStorage.getItem("clarity-tts-voice-uri")
        : null;
    const savedRate =
      typeof localStorage !== "undefined"
        ? localStorage.getItem("clarity-tts-rate")
        : null;

    if (savedVoiceUri) {
      const voices = speechSynthesis.getVoices();
      const match = voices.find((v) => v.voiceURI === savedVoiceUri);
      if (match) utterance.voice = match;
    }

    utterance.rate = savedRate ? parseFloat(savedRate) : 1.0;
    utterance.onend = () => setState("idle");
    setState("speaking");
    speechSynthesis.speak(utterance);
  }, []);

  const handleResult = useCallback(
    async (transcript: string) => {
      setState("processing");
      try {
        const result: VoiceResponse = await processVoice(transcript);
        setLastResponse(result.response);
        speak(result.response);
      } catch {
        setLastResponse("Sorry, something went wrong.");
        setState("idle");
      }
    },
    [speak],
  );

  // --- Whisper path (push-to-talk) ---

  const startWhisper = useCallback(async () => {
    try {
      await startCapture({ onLevel: setAudioLevel });
      setState("listening");
    } catch {
      setLastResponse("Microphone access denied.");
      setState("idle");
    }
  }, [startCapture]);

  const stopWhisper = useCallback(async () => {
    setState("processing");
    setAudioLevel(0);
    try {
      const { audioData, sampleRate } = await stopCapture();
      const text = await whisperTranscribe(audioData, sampleRate);
      if (text) {
        handleResult(text);
      } else {
        setLastResponse("Didn't catch that. Try again.");
        setState("idle");
      }
    } catch {
      setLastResponse("Transcription failed.");
      setState("idle");
    }
  }, [stopCapture, handleResult]);

  // --- Web Speech API path ---

  const startWebSpeech = useCallback(() => {
    const SpeechRecognitionAPI =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) {
      setLastResponse("Speech recognition not supported in this browser.");
      return;
    }

    const recognition = new SpeechRecognitionAPI();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      if (transcript) {
        handleResult(transcript);
      } else {
        setState("idle");
      }
    };

    recognition.onerror = () => {
      setState("idle");
    };

    recognition.onend = () => {
      if (state === "listening") {
        setState("idle");
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
    setState("listening");
  }, [handleResult, state]);

  const stopWebSpeech = useCallback(() => {
    recognitionRef.current?.stop();
    setState("idle");
    setAudioLevel(0);
  }, []);

  // --- Toggle ---

  const toggle = useCallback(() => {
    if (state === "listening") {
      if (sttBackend === "whisper") {
        stopWhisper();
      } else {
        stopWebSpeech();
      }
    } else if (state === "idle") {
      if (sttBackend === "whisper") {
        startWhisper();
      } else if (sttBackend === "web-speech") {
        startWebSpeech();
      } else {
        setLastResponse("Speech recognition not supported.");
      }
    }
  }, [
    state,
    sttBackend,
    startWhisper,
    stopWhisper,
    startWebSpeech,
    stopWebSpeech,
  ]);

  const dismissResponse = useCallback(() => {
    setLastResponse(null);
    speechSynthesis.cancel();
    setState("idle");
  }, []);

  // Global keyboard shortcut: Cmd+Shift+Space
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.metaKey && e.shiftKey && e.code === "Space") {
        e.preventDefault();
        toggle();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [toggle]);

  return {
    state,
    sttBackend,
    lastResponse,
    audioLevel,
    toggle,
    dismissResponse,
  };
}

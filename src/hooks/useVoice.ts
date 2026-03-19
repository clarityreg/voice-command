"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  processVoice,
  processAudio,
  confirmPlaneAction,
  getSettings,
  type VoiceResponse,
  type PendingAction,
} from "@/lib/api";
import {
  isTauri,
  getModelStatus,
  transcribe as whisperTranscribe,
} from "@/lib/whisper";
import { useAudioCapture } from "@/hooks/useAudioCapture";

export type VoiceState = "idle" | "listening" | "processing" | "speaking";
export type SttBackend = "whisper" | "web-speech" | "openai-whisper" | "none";

export interface UseVoiceReturn {
  state: VoiceState;
  sttBackend: SttBackend;
  lastResponse: string | null;
  audioLevel: number;
  pendingAction: PendingAction | null;
  toggle: () => void;
  dismissResponse: () => void;
  confirmAction: () => void;
  rejectAction: () => void;
}

export function useVoice(): UseVoiceReturn {
  const [state, setState] = useState<VoiceState>("idle");
  const [lastResponse, setLastResponse] = useState<string | null>(null);
  const [sttBackend, setSttBackend] = useState<SttBackend>("none");
  const [audioLevel, setAudioLevel] = useState(0);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaChunksRef = useRef<Blob[]>([]);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const { startCapture, stopCapture } = useAudioCapture();

  // Detect STT backend on mount — respect user preference from settings
  useEffect(() => {
    async function detectBackend() {
      // Check if user has configured a preferred STT backend
      try {
        const settings = await getSettings();
        const preferred = settings.stt_backend;
        if (preferred === "openai-whisper") {
          setSttBackend("openai-whisper");
          return;
        }
      } catch {
        // Settings not available, fall through to auto-detect
      }

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

        // Check if the response contains a pending action requiring confirmation
        const pa = result.data?.pending_action as PendingAction | undefined;
        if (pa) {
          setPendingAction(pa);
          speak(result.response);
        } else {
          speak(result.response);
        }
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

  // --- OpenAI Whisper path (push-to-talk, cloud transcription) ---

  const handleAudioResult = useCallback(
    async (result: VoiceResponse) => {
      setLastResponse(result.response);
      const pa = result.data?.pending_action as PendingAction | undefined;
      if (pa) {
        setPendingAction(pa);
      }
      speak(result.response);
    },
    [speak],
  );

  const startOpenAIWhisper = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      mediaChunksRef.current = [];

      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/mp4")
          ? "audio/mp4"
          : undefined;
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) mediaChunksRef.current.push(e.data);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setState("listening");
    } catch {
      setLastResponse("Microphone access denied.");
      setState("idle");
    }
  }, []);

  const stopOpenAIWhisper = useCallback(async () => {
    setState("processing");

    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      setState("idle");
      return;
    }

    // Wait for the recorder to finish
    const blob = await new Promise<Blob>((resolve) => {
      recorder.onstop = () => {
        resolve(new Blob(mediaChunksRef.current, { type: recorder.mimeType || "audio/webm" }));
      };
      recorder.stop();
    });

    // Stop all tracks
    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    mediaStreamRef.current = null;
    mediaRecorderRef.current = null;

    try {
      const result = await processAudio(blob);
      handleAudioResult(result);
    } catch {
      setLastResponse("Transcription failed.");
      setState("idle");
    }
  }, [handleAudioResult]);

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
      } else if (sttBackend === "openai-whisper") {
        stopOpenAIWhisper();
      } else {
        stopWebSpeech();
      }
    } else if (state === "idle") {
      if (sttBackend === "whisper") {
        startWhisper();
      } else if (sttBackend === "openai-whisper") {
        startOpenAIWhisper();
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
    startOpenAIWhisper,
    stopOpenAIWhisper,
    startWebSpeech,
    stopWebSpeech,
  ]);

  const dismissResponse = useCallback(() => {
    setLastResponse(null);
    setPendingAction(null);
    speechSynthesis.cancel();
    setState("idle");
  }, []);

  const confirmAction = useCallback(async () => {
    if (!pendingAction) return;
    const action = pendingAction;
    setPendingAction(null);
    setState("processing");
    try {
      const result = await confirmPlaneAction(action);
      setLastResponse(result.response);
      speak(result.response);
    } catch {
      setLastResponse("Failed to execute action.");
      setState("idle");
    }
  }, [pendingAction, speak]);

  const rejectAction = useCallback(() => {
    setPendingAction(null);
    setLastResponse("Action cancelled.");
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
    pendingAction,
    toggle,
    dismissResponse,
    confirmAction,
    rejectAction,
  };
}

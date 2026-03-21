"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import AccountManager from "@/components/AccountManager";
import NotificationSettings from "@/components/NotificationSettings";
import TtsSettings from "@/components/TtsSettings";
import WhisperSetup from "@/components/WhisperSetup";
import VocabularyEditor from "@/components/VocabularyEditor";
import PlaneProjectsEditor from "@/components/PlaneProjectsEditor";
import { getSettings, updateSettings, type AppSettings } from "@/lib/api";

type FormData = {
  plane_api_key: string;
  plane_workspace_slug: string;
  plane_project_id: string;
  openai_api_key: string;
  stt_backend: string;
  voice_shortcut: string;
  aikido_webhook_secret: string;
  posthog_api_key: string;
  posthog_project_id: string;
  posthog_host: string;
  focus_minutes: string;
  break_minutes: string;
  clarity_api_url: string;
  clarity_api_key: string;
  clarity_webhook_secret: string;
};

function toForm(s: AppSettings): FormData {
  return {
    plane_api_key: s.plane_api_key,
    plane_workspace_slug: s.plane_workspace_slug,
    plane_project_id: s.plane_project_id,
    openai_api_key: s.openai_api_key ?? "",
    stt_backend: s.stt_backend ?? "web-speech",
    voice_shortcut: s.voice_shortcut ?? "Cmd+Shift+Space",
    aikido_webhook_secret: s.aikido_webhook_secret,
    posthog_api_key: s.posthog_api_key ?? "",
    posthog_project_id: s.posthog_project_id ?? "",
    posthog_host: s.posthog_host ?? "https://eu.posthog.com",
    focus_minutes: String(s.focus_minutes),
    break_minutes: String(s.break_minutes),
    clarity_api_url: s.clarity_api_url ?? "http://localhost:8000",
    clarity_api_key: s.clarity_api_key ?? "",
    clarity_webhook_secret: s.clarity_webhook_secret ?? "",
  };
}

export default function SettingsPage() {
  const [form, setForm] = useState<FormData | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSettings()
      .then((s) => setForm(toForm(s)))
      .catch((e) => setError(e.message));
  }, []);

  const handleChange = (key: keyof FormData, value: string) => {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
    setSaved(false);
  };

  const handleSave = async () => {
    if (!form) return;
    setSaving(true);
    setError(null);
    try {
      const payload: Partial<AppSettings> = {
        plane_api_key: form.plane_api_key,
        plane_workspace_slug: form.plane_workspace_slug,
        plane_project_id: form.plane_project_id,
        openai_api_key: form.openai_api_key,
        stt_backend: form.stt_backend,
        voice_shortcut: form.voice_shortcut,
        aikido_webhook_secret: form.aikido_webhook_secret,
        posthog_api_key: form.posthog_api_key,
        posthog_project_id: form.posthog_project_id,
        posthog_host: form.posthog_host,
        focus_minutes: parseInt(form.focus_minutes, 10) || 25,
        break_minutes: parseInt(form.break_minutes, 10) || 5,
        clarity_api_url: form.clarity_api_url,
        clarity_api_key: form.clarity_api_key,
        clarity_webhook_secret: form.clarity_webhook_secret,
      };
      const updated = await updateSettings(payload);
      setForm(toForm(updated));
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    getSettings()
      .then((s) => {
        setForm(toForm(s));
        setSaved(false);
      })
      .catch(() => {});
  };

  if (error && !form) {
    return (
      <div className="rounded-card bg-sev-critical/20 p-5 text-center shadow-card">
        <p className="text-bark">{error}</p>
      </div>
    );
  }

  if (!form) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 animate-pulse rounded-card bg-cream-dark" />
        ))}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl">
      <h2 className="mb-5 text-lg font-bold text-bark">Settings</h2>

      <div className="lg:grid lg:grid-cols-2 lg:gap-8">
        {/* Left column — settings form */}
        <div className="flex flex-col gap-5">
          <section className="rounded-card bg-card-bg p-5 shadow-card">
            <h3 className="mb-3 flex items-center gap-2 font-semibold text-bark">
              <span className="text-lg">{"\uD83D\uDCC1"}</span> Plane Integration
            </h3>
            <div className="flex flex-col gap-3">
              <Field label="API Key" value={form.plane_api_key} type="password" onChange={(v) => handleChange("plane_api_key", v)} />
              <Field label="Workspace Slug" value={form.plane_workspace_slug} onChange={(v) => handleChange("plane_workspace_slug", v)} />
              <Field label="Project ID" value={form.plane_project_id} onChange={(v) => handleChange("plane_project_id", v)} />
            </div>
            <hr className="my-3 border-cream-dark" />
            <PlaneProjectsEditor />
          </section>

          <section className="rounded-card bg-card-bg p-5 shadow-card">
            <h3 className="mb-3 flex items-center gap-2 font-semibold text-bark">
              <span className="text-lg">{"\uD83D\uDEE1\uFE0F"}</span> Aikido Webhook
            </h3>
            <Field label="Webhook Secret" value={form.aikido_webhook_secret} type="password" onChange={(v) => handleChange("aikido_webhook_secret", v)} />
          </section>

          <section className="rounded-card bg-card-bg p-5 shadow-card">
            <h3 className="mb-3 flex items-center gap-2 font-semibold text-bark">
              <span className="text-lg">{"\uD83E\uDD94"}</span> PostHog
            </h3>
            <div className="flex flex-col gap-3">
              <Field label="Personal API Key" value={form.posthog_api_key} type="password" onChange={(v) => handleChange("posthog_api_key", v)} />
              <Field label="Project ID" value={form.posthog_project_id} onChange={(v) => handleChange("posthog_project_id", v)} />
              <Field label="Host" value={form.posthog_host} onChange={(v) => handleChange("posthog_host", v)} />
              <span className="text-[10px] text-bark-light">
                Polls PostHog for error events every 60s. Errors appear in your triage queue.
              </span>
            </div>
          </section>

          <section className="rounded-card bg-card-bg p-5 shadow-card">
            <h3 className="mb-3 flex items-center gap-2 font-semibold text-bark">
              <span className="text-lg">{"\uD83D\uDD17"}</span> Clarity App
            </h3>
            <div className="flex flex-col gap-3">
              <Field label="API URL" value={form.clarity_api_url} onChange={(v) => handleChange("clarity_api_url", v)} />
              <Field label="API Key" value={form.clarity_api_key} type="password" onChange={(v) => handleChange("clarity_api_key", v)} />
              <Field label="Webhook Secret" value={form.clarity_webhook_secret} type="password" onChange={(v) => handleChange("clarity_webhook_secret", v)} />
              <span className="text-[10px] text-bark-light">
                Connects voice commands to Clarity&apos;s regulatory platform (schedules, compliance, ADHD Bridge).
              </span>
            </div>
          </section>

          <section className="rounded-card bg-card-bg p-5 shadow-card">
            <h3 className="mb-3 flex items-center gap-2 font-semibold text-bark">
              <span className="text-lg">{"\u23F1\uFE0F"}</span> Timer
            </h3>
            <div className="flex gap-4">
              <Field label="Focus (min)" value={form.focus_minutes} type="number" onChange={(v) => handleChange("focus_minutes", v)} />
              <Field label="Break (min)" value={form.break_minutes} type="number" onChange={(v) => handleChange("break_minutes", v)} />
            </div>
          </section>

          <section className="rounded-card bg-card-bg p-5 shadow-card">
            <h3 className="mb-3 flex items-center gap-2 font-semibold text-bark">
              <span className="text-lg">{"\uD83C\uDFA4"}</span> Voice Recognition
            </h3>
            <div className="flex flex-col gap-3">
              <ShortcutRecorder
                value={form.voice_shortcut}
                onChange={(v) => handleChange("voice_shortcut", v)}
              />
              <label className="flex flex-col gap-1">
                <span className="text-xs font-medium text-bark-muted">Speech-to-Text Backend</span>
                <select
                  value={form.stt_backend}
                  onChange={(e) => handleChange("stt_backend", e.target.value)}
                  className="rounded-lg border border-cream-dark bg-cream-light px-3 py-2 text-sm text-bark outline-none focus:border-accent"
                >
                  <option value="web-speech">Web Speech API (browser built-in)</option>
                  <option value="openai-whisper">OpenAI Whisper (cloud, best accuracy)</option>
                  <option value="whisper">Local Whisper (Tauri only)</option>
                </select>
                <span className="text-[10px] text-bark-light">
                  OpenAI Whisper uses your project names to improve recognition accuracy.
                </span>
              </label>
              {form.stt_backend === "openai-whisper" && (
                <Field label="OpenAI API Key" value={form.openai_api_key} type="password" onChange={(v) => handleChange("openai_api_key", v)} />
              )}
              <hr className="border-cream-dark" />
              <TtsSettings />
              <hr className="border-cream-dark" />
              <WhisperSetup />
              <VocabularyEditor />
            </div>
          </section>

          <NotificationSettings />

          {error && (
            <p className="text-sm text-sev-critical">{error}</p>
          )}

          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="rounded-pill bg-nav-bg px-5 py-2.5 text-sm font-medium text-cream transition hover:opacity-90 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Settings"}
            </button>
            <button
              onClick={handleReset}
              className="rounded-pill bg-cream-dark px-5 py-2.5 text-sm font-medium text-bark transition hover:opacity-80"
            >
              Reset
            </button>
            {saved && (
              <span className="self-center text-sm text-sev-low">{"\u2705"} Saved</span>
            )}
          </div>
        </div>

        {/* Right column — connected accounts */}
        <div className="mt-5 lg:mt-0">
          <AccountManager />
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  type = "text",
  onChange,
}: {
  label: string;
  value: string;
  type?: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium text-bark-muted">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-cream-dark bg-cream-light px-3 py-2 text-sm text-bark outline-none focus:border-accent"
      />
    </label>
  );
}

const MODIFIER_DISPLAY: Record<string, string> = {
  Meta: "\u2318",
  Shift: "\u21E7",
  Alt: "\u2325",
  Control: "\u2303",
};

const KEY_TO_SHORTCUT_TOKEN: Record<string, string> = {
  Meta: "Cmd",
  Control: "Ctrl",
  Alt: "Alt",
  Shift: "Shift",
};

function buildShortcutString(e: KeyboardEvent): string {
  const parts: string[] = [];
  if (e.metaKey) parts.push("Cmd");
  if (e.ctrlKey) parts.push("Ctrl");
  if (e.altKey) parts.push("Alt");
  if (e.shiftKey) parts.push("Shift");

  // The non-modifier key
  if (!["Meta", "Control", "Alt", "Shift"].includes(e.key)) {
    if (e.code === "Space") {
      parts.push("Space");
    } else if (e.code.startsWith("Key") && e.code.length === 4) {
      // e.g. KeyV → V
      parts.push(e.code.slice(3));
    } else {
      parts.push(e.code);
    }
  }

  return parts.join("+");
}

function formatShortcutDisplay(shortcut: string): string {
  return shortcut
    .split("+")
    .map((part) => {
      switch (part.trim().toLowerCase()) {
        case "cmd":
        case "meta":
          return "\u2318";
        case "shift":
          return "\u21E7";
        case "alt":
        case "option":
          return "\u2325";
        case "ctrl":
        case "control":
          return "\u2303";
        default:
          return part.trim();
      }
    })
    .join("");
}

function ShortcutRecorder({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const [recording, setRecording] = useState(false);
  const [preview, setPreview] = useState<string>("");
  const containerRef = useRef<HTMLDivElement>(null);

  const startRecording = useCallback(() => {
    setRecording(true);
    setPreview("");
    // Focus the hidden input so keydown events fire reliably
    containerRef.current?.focus();
  }, []);

  const stopRecording = useCallback(() => {
    setRecording(false);
    setPreview("");
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (!recording) return;
      e.preventDefault();
      e.stopPropagation();

      const isModifierOnly = ["Meta", "Control", "Alt", "Shift"].includes(e.key);

      if (isModifierOnly) {
        // Show a live preview of modifiers held so far
        const modParts: string[] = [];
        if (e.metaKey) modParts.push(MODIFIER_DISPLAY["Meta"]);
        if (e.ctrlKey) modParts.push(MODIFIER_DISPLAY["Control"]);
        if (e.altKey) modParts.push(MODIFIER_DISPLAY["Alt"]);
        if (e.shiftKey) modParts.push(MODIFIER_DISPLAY["Shift"]);
        // Mark the key being held right now too
        if (!modParts.includes(MODIFIER_DISPLAY[e.key])) {
          modParts.push(MODIFIER_DISPLAY[e.key]);
        }
        setPreview(modParts.join("") + "...");
        return;
      }

      // Escape cancels recording without saving
      if (e.key === "Escape") {
        stopRecording();
        return;
      }

      const shortcut = buildShortcutString(e.nativeEvent);
      if (shortcut) {
        onChange(shortcut);
      }
      setRecording(false);
      setPreview("");
    },
    [recording, onChange, stopRecording],
  );

  // Clicking outside cancels recording
  useEffect(() => {
    if (!recording) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        stopRecording();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [recording, stopRecording]);

  // Suppress unused import warnings for helper maps
  void KEY_TO_SHORTCUT_TOKEN;

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium text-bark-muted">Voice Shortcut</span>
      <div
        ref={containerRef}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className="outline-none"
        aria-label="Voice shortcut recorder"
      >
        {recording ? (
          <div className="flex items-center gap-2 rounded-lg border border-accent bg-cream-light px-3 py-2">
            <span className="animate-pulse text-sm text-bark-muted">
              {preview || "Press your shortcut..."}
            </span>
            <button
              type="button"
              onClick={stopRecording}
              className="ml-auto text-xs text-bark-light hover:text-bark"
              aria-label="Cancel shortcut recording"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={startRecording}
            className="flex items-center gap-2 rounded-lg border border-cream-dark bg-cream-light px-3 py-2 text-sm text-bark transition hover:border-accent"
            aria-label={`Current shortcut: ${value}. Click to change.`}
          >
            <kbd className="rounded bg-cream-dark px-1.5 py-0.5 font-mono text-xs">
              {formatShortcutDisplay(value)}
            </kbd>
            <span className="text-bark-muted">Click to change</span>
          </button>
        )}
      </div>
      <span className="text-[10px] text-bark-light">
        Click then press a key combo. Use Escape to cancel.
      </span>
    </div>
  );
}

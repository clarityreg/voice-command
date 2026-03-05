"use client";

import { useEffect, useState } from "react";
import AccountManager from "@/components/AccountManager";
import NotificationSettings from "@/components/NotificationSettings";
import TtsSettings from "@/components/TtsSettings";
import WhisperSetup from "@/components/WhisperSetup";
import VocabularyEditor from "@/components/VocabularyEditor";
import { getSettings, updateSettings, type AppSettings } from "@/lib/api";

type FormData = {
  plane_api_key: string;
  plane_workspace_slug: string;
  plane_project_id: string;
  aikido_webhook_secret: string;
  focus_minutes: string;
  break_minutes: string;
};

function toForm(s: AppSettings): FormData {
  return {
    plane_api_key: s.plane_api_key,
    plane_workspace_slug: s.plane_workspace_slug,
    plane_project_id: s.plane_project_id,
    aikido_webhook_secret: s.aikido_webhook_secret,
    focus_minutes: String(s.focus_minutes),
    break_minutes: String(s.break_minutes),
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
        aikido_webhook_secret: form.aikido_webhook_secret,
        focus_minutes: parseInt(form.focus_minutes, 10) || 25,
        break_minutes: parseInt(form.break_minutes, 10) || 5,
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
          </section>

          <section className="rounded-card bg-card-bg p-5 shadow-card">
            <h3 className="mb-3 flex items-center gap-2 font-semibold text-bark">
              <span className="text-lg">{"\uD83D\uDEE1\uFE0F"}</span> Aikido Webhook
            </h3>
            <Field label="Webhook Secret" value={form.aikido_webhook_secret} type="password" onChange={(v) => handleChange("aikido_webhook_secret", v)} />
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

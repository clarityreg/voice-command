"use client";

import { useCallback, useEffect, useState } from "react";
import { isTauri, getCustomVocab, saveCustomVocab } from "@/lib/whisper";
import { getPlaneProjects } from "@/lib/api";

export default function VocabularyEditor() {
  const [terms, setTerms] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!isTauri()) return;
    getCustomVocab()
      .then((t) => setTerms(t.join("\n")))
      .catch(() => {});
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaved(false);
    try {
      const termList = terms
        .split("\n")
        .map((l) => l.trim())
        .filter((l) => l.length > 0);
      await saveCustomVocab(termList);
      setSaved(true);
    } catch {
      // Best-effort save
    } finally {
      setSaving(false);
    }
  }, [terms]);

  const importProjectNames = useCallback(async () => {
    try {
      const data = await getPlaneProjects();
      const projects = data.projects ?? {};
      const existingTerms = new Set(
        terms
          .split("\n")
          .map((l) => l.trim().toLowerCase())
          .filter((l) => l.length > 0),
      );

      const newTerms: string[] = [];
      for (const [alias, project] of Object.entries(projects)) {
        if (!existingTerms.has(alias.toLowerCase())) {
          newTerms.push(alias);
        }
        const name = project.name;
        if (name && !existingTerms.has(name.toLowerCase())) {
          newTerms.push(name);
        }
      }

      if (newTerms.length > 0) {
        const updated = terms.trim()
          ? `${terms.trim()}\n${newTerms.join("\n")}`
          : newTerms.join("\n");
        setTerms(updated);
        setSaved(false);
      }
    } catch {
      // Best-effort import
    }
  }, [terms]);

  if (!isTauri()) return null;

  return (
    <div className="rounded-card bg-card-bg p-5 shadow-card">
      <h3 className="mb-2 font-semibold text-bark">Custom Vocabulary</h3>
      <p className="mb-3 text-xs text-bark-muted">
        Add domain-specific terms (one per line) to improve recognition accuracy.
        Write terms as they should be spelled. Keep under ~50 terms for best results.
      </p>
      <textarea
        value={terms}
        onChange={(e) => {
          setTerms(e.target.value);
          setSaved(false);
        }}
        rows={6}
        placeholder={"PostHog\nOWASP\nCVE (Common Vulnerabilities and Exposures)\nwebhook"}
        className="w-full rounded-lg border border-cream-dark bg-cream-light px-3 py-2 text-sm text-bark outline-none focus:border-accent"
      />
      <div className="mt-2 flex items-center gap-2">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-pill bg-nav-bg px-4 py-1.5 text-xs font-medium text-cream hover:opacity-90 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Vocabulary"}
        </button>
        <button
          onClick={importProjectNames}
          className="rounded-pill bg-accent/20 px-4 py-1.5 text-xs font-medium text-accent hover:bg-accent/30"
        >
          Import Project Names
        </button>
        {saved && <span className="text-xs text-sev-low">Saved</span>}
      </div>
    </div>
  );
}

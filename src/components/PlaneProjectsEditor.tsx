"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getPlaneProjects,
  syncPlaneProjects,
  updateProjectAlias,
  deleteProjectAlias,
  type PlaneProjectEntry,
} from "@/lib/api";

export default function PlaneProjectsEditor() {
  const [projects, setProjects] = useState<Record<string, PlaneProjectEntry>>(
    {},
  );
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncSuccess, setSyncSuccess] = useState(false);
  const [editingAlias, setEditingAlias] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const loadProjects = useCallback(async () => {
    try {
      const data = await getPlaneProjects();
      setProjects(data.projects ?? {});
    } catch {
      // Projects not loaded yet — that's OK
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    setSyncSuccess(false);
    try {
      const data = await syncPlaneProjects();
      if (data.error) {
        setError(data.error);
      } else {
        setProjects(data.projects ?? {});
        setSyncSuccess(true);
        setTimeout(() => setSyncSuccess(false), 3000);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const handleStartEdit = (alias: string) => {
    setEditingAlias(alias);
    setEditValue(alias);
  };

  const savingRef = useRef(false);

  const handleSaveAlias = async (oldAlias: string) => {
    if (savingRef.current) return;
    savingRef.current = true;
    const newAlias = editValue.trim().toLowerCase();
    if (!newAlias || newAlias === oldAlias) {
      setEditingAlias(null);
      savingRef.current = false;
      return;
    }
    try {
      const data = await updateProjectAlias(oldAlias, { new_alias: newAlias });
      if (data.error) {
        setError(data.error);
      } else {
        setProjects(data.projects ?? {});
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update alias");
    }
    setEditingAlias(null);
    savingRef.current = false;
  };

  const handleDelete = async (alias: string) => {
    try {
      const data = await deleteProjectAlias(alias);
      if ((data as Record<string, unknown>).error) {
        setError((data as Record<string, unknown>).error as string);
        return;
      }
      setProjects(data.projects ?? {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete alias");
    }
  };

  const entries = Object.entries(projects);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-bark-muted">
            Voice Aliases ({entries.length} projects)
          </p>
          <p className="text-[10px] text-bark-light">
            Click an alias to rename it. Say the alias to target a project by voice.
          </p>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="rounded-pill bg-accent px-3 py-1.5 text-xs font-medium text-cream transition hover:opacity-90 disabled:opacity-50"
        >
          {syncing ? "Syncing..." : "Sync from Plane"}
        </button>
      </div>

      {error && (
        <p className="text-xs text-sev-critical">{error}</p>
      )}

      {syncSuccess && (
        <p className="text-xs text-sev-low">Projects synced successfully</p>
      )}

      {entries.length === 0 ? (
        <p className="text-xs text-bark-light">
          No projects synced yet. Click &quot;Sync from Plane&quot; to load your
          projects.
        </p>
      ) : (
        <div className="max-h-64 overflow-y-auto rounded-lg border border-cream-dark">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-cream-dark bg-cream-light">
                <th className="px-3 py-2 text-left font-medium text-bark-muted">
                  Voice Alias
                </th>
                <th className="px-3 py-2 text-left font-medium text-bark-muted">
                  Project
                </th>
                <th className="px-3 py-2 text-left font-medium text-bark-muted">
                  ID
                </th>
                <th className="w-8 px-2 py-2" />
              </tr>
            </thead>
            <tbody>
              {entries.map(([alias, project]) => (
                <tr
                  key={alias}
                  className="border-b border-cream-dark last:border-0"
                >
                  <td className="px-3 py-2">
                    {editingAlias === alias ? (
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => handleSaveAlias(alias)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSaveAlias(alias);
                          if (e.key === "Escape") setEditingAlias(null);
                        }}
                        autoFocus
                        className="w-full rounded border border-accent bg-cream px-1.5 py-0.5 font-mono text-xs text-accent outline-none"
                      />
                    ) : (
                      <button
                        onClick={() => handleStartEdit(alias)}
                        className="font-mono text-accent hover:underline"
                        title="Click to rename alias"
                      >
                        {alias}
                      </button>
                    )}
                  </td>
                  <td className="px-3 py-2 text-bark">{project.name}</td>
                  <td className="px-3 py-2 text-bark-light">
                    {project.identifier}
                  </td>
                  <td className="px-2 py-2">
                    <button
                      onClick={() => handleDelete(alias)}
                      className="text-bark-light hover:text-sev-critical"
                      title="Remove alias"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

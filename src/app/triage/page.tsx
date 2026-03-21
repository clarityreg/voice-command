"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TriageCard from "@/components/TriageCard";
import ShortcutHelp from "@/components/ShortcutHelp";
import InvestigationResult from "@/components/InvestigationResult";
import {
  createIssue,
  dismissItem,
  getTriageItems,
  investigateItem,
  snoozeItem,
  startAgentFix,
  type InvestigationResult as InvestResult,
  type TriageItem,
} from "@/lib/api";

export default function TriagePage() {
  const router = useRouter();
  const [items, setItems] = useState<TriageItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [investigating, setInvestigating] = useState(false);
  const [investigation, setInvestigation] = useState<InvestResult | null>(null);
  const [fixing, setFixing] = useState(false);

  const fetchItems = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getTriageItems("pending");
      setItems(data);
      setCurrentIndex(0);
      setError(null);
    } catch {
      setError("Could not connect to backend. Is it running on :8070?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const advance = () => {
    setInvestigation(null);
    if (currentIndex < items.length - 1) {
      setCurrentIndex((i) => i + 1);
    } else {
      fetchItems();
    }
  };

  const handleInvestigate = async (id: number) => {
    try {
      setInvestigating(true);
      const data = await investigateItem(id);
      setInvestigation(data.investigation);
    } catch {
      setInvestigation({
        root_cause: "Investigation failed. Is the backend running?",
        affected_files: [],
        suggested_fix: "Try again or investigate manually.",
        raw_response: "",
      });
    } finally {
      setInvestigating(false);
    }
  };

  const handleSnooze = async (id: number) => {
    await snoozeItem(id);
    advance();
  };

  const handleDismiss = async (id: number) => {
    await dismissItem(id);
    advance();
  };

  const handleCreateIssue = async (id: number) => {
    await createIssue(id);
    advance();
  };

  const handleFix = async (id: number) => {
    try {
      setFixing(true);
      await startAgentFix(id);
      router.push("/agent");
    } finally {
      setFixing(false);
    }
  };

  // Keyboard shortcuts — only when a triage card is visible
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      // Don't capture when typing in inputs
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      const current = items[currentIndex];

      if (e.key === "?") {
        setShowHelp((prev) => !prev);
        return;
      }

      // Only handle action keys when a card is visible and help is closed
      if (!current || loading || error || showHelp) return;

      switch (e.key) {
        case "c":
          handleCreateIssue(current.id);
          break;
        case "i":
          handleInvestigate(current.id);
          break;
        case "f":
          handleFix(current.id);
          break;
        case "s":
          handleSnooze(current.id);
          break;
        case "d":
          handleDismiss(current.id);
          break;
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [items, currentIndex, loading, error, showHelp]);

  if (loading) {
    return (
      <div className="py-20 text-center text-bark-muted">
        Loading triage queue...
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-20 text-center">
        <p className="mb-4 text-sev-critical">{error}</p>
        <button
          onClick={fetchItems}
          className="rounded-pill bg-cream-dark px-4 py-2 text-sm text-bark hover:bg-cream"
        >
          Retry
        </button>
      </div>
    );
  }

  const current = items[currentIndex];

  if (!current) {
    return (
      <div className="py-20 text-center">
        <p className="mb-2 text-2xl font-bold text-sev-low">All clear!</p>
        <p className="text-bark-muted">
          No pending items in the triage queue. Nice work.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl lg:max-w-2xl">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold text-bark">Triage Queue</h2>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowHelp(true)}
            className="rounded-md bg-cream-dark px-2 py-0.5 text-xs font-mono text-bark-muted hover:text-bark"
            title="Keyboard shortcuts"
          >
            ?
          </button>
          <span className="text-sm text-bark-muted">
            {currentIndex + 1} of {items.length}
          </span>
        </div>
      </div>
      <TriageCard
        item={current}
        onSnooze={handleSnooze}
        onDismiss={handleDismiss}
        onCreateIssue={handleCreateIssue}
        onInvestigate={handleInvestigate}
        investigating={investigating}
        onFix={handleFix}
        fixing={fixing}
      />
      {investigation && (
        <InvestigationResult
          result={investigation}
          onClose={() => setInvestigation(null)}
        />
      )}
      {showHelp && <ShortcutHelp onClose={() => setShowHelp(false)} />}
    </div>
  );
}

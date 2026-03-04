"use client";

interface ShortcutHelpProps {
  onClose: () => void;
}

const shortcuts = [
  { key: "c", label: "Create Issue" },
  { key: "s", label: "Snooze" },
  { key: "d", label: "Dismiss" },
  { key: "?", label: "Toggle this help" },
];

export default function ShortcutHelp({ onClose }: ShortcutHelpProps) {
  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-bark/50"
      onClick={onClose}
    >
      <div
        className="w-72 rounded-card bg-card-bg p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="mb-4 text-lg font-bold text-bark">Keyboard Shortcuts</h3>
        <div className="flex flex-col gap-3">
          {shortcuts.map((s) => (
            <div key={s.key} className="flex items-center justify-between">
              <span className="text-sm text-bark-muted">{s.label}</span>
              <kbd className="rounded-md bg-cream-dark px-2.5 py-1 text-xs font-mono font-bold text-bark">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>
        <button
          onClick={onClose}
          className="mt-5 w-full rounded-pill bg-cream-dark py-2 text-sm font-medium text-bark transition hover:bg-cream"
        >
          Close
        </button>
      </div>
    </div>
  );
}

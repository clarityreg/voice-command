"use client";

import { useCallback, useEffect, useState } from "react";
import type { Notification, Priority } from "@/lib/notificationTypes";
import { createTask } from "@/lib/notificationApi";

interface TaskCreatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  notification?: Notification | null;
}

export default function TaskCreatorModal({ isOpen, onClose, notification }: TaskCreatorModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [target, setTarget] = useState<"plane" | "asana">("plane");
  const [priority, setPriority] = useState<Priority>("normal");
  const [isCreating, setIsCreating] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (isOpen && notification) {
      setTitle(notification.title);
      setDescription(notification.body);
    }
  }, [isOpen, notification]);

  const handleClose = useCallback(() => {
    onClose();
    setTitle("");
    setDescription("");
    setTarget("plane");
    setPriority("normal");
    setSuccess(false);
  }, [onClose]);

  const handleCreate = useCallback(async () => {
    if (!title.trim()) return;
    setIsCreating(true);
    try {
      await createTask({
        title,
        description,
        target,
        priority,
        source_notification_id: notification?.id,
      });
      setSuccess(true);
      setTimeout(handleClose, 1000);
    } catch (e) {
      console.error("Failed to create task:", e);
    }
    setIsCreating(false);
  }, [title, description, target, priority, notification, handleClose]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") handleCreate();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, handleClose, handleCreate]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={handleClose}>
      <div className="w-[480px] max-w-[90vw] rounded-card bg-card-bg shadow-lg" onClick={(e) => e.stopPropagation()}>
        {success ? (
          <div className="py-12 text-center">
            <p className="text-lg font-bold text-sev-low">Task created in {target === "plane" ? "Plane" : "Asana"}!</p>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between border-b border-cream-dark p-5">
              <h3 className="text-lg font-bold text-bark">Create Task</h3>
              <button onClick={handleClose} className="text-sm text-bark-muted hover:text-bark">Close</button>
            </div>
            <div className="flex flex-col gap-4 p-5">
              <label className="flex flex-col gap-1">
                <span className="text-xs font-medium text-bark-muted">Title</span>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Task title..."
                  autoFocus
                  className="rounded-lg border border-cream-dark bg-cream-light px-3 py-2 text-sm text-bark outline-none focus:border-accent"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs font-medium text-bark-muted">Description</span>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional description..."
                  rows={3}
                  className="rounded-lg border border-cream-dark bg-cream-light px-3 py-2 text-sm text-bark outline-none focus:border-accent"
                />
              </label>
              <div className="flex gap-3">
                <label className="flex flex-1 flex-col gap-1">
                  <span className="text-xs font-medium text-bark-muted">Create in</span>
                  <select value={target} onChange={(e) => setTarget(e.target.value as "plane" | "asana")} className="rounded-lg border border-cream-dark bg-cream-light px-3 py-2 text-sm text-bark outline-none focus:border-accent">
                    <option value="plane">Plane</option>
                    <option value="asana">Asana</option>
                  </select>
                </label>
                <label className="flex flex-1 flex-col gap-1">
                  <span className="text-xs font-medium text-bark-muted">Priority</span>
                  <select value={priority} onChange={(e) => setPriority(e.target.value as Priority)} className="rounded-lg border border-cream-dark bg-cream-light px-3 py-2 text-sm text-bark outline-none focus:border-accent">
                    <option value="urgent">Urgent</option>
                    <option value="high">High</option>
                    <option value="normal">Normal</option>
                    <option value="low">Low</option>
                  </select>
                </label>
              </div>
            </div>
            <div className="flex items-center justify-between border-t border-cream-dark p-4">
              <span className="text-xs text-bark-light">Cmd+Enter to create</span>
              <div className="flex gap-2">
                <button onClick={handleClose} className="rounded-pill bg-cream-dark px-4 py-2 text-sm font-medium text-bark hover:opacity-80">
                  Cancel
                </button>
                <button
                  disabled={!title.trim() || isCreating}
                  onClick={handleCreate}
                  className="rounded-pill bg-nav-bg px-4 py-2 text-sm font-medium text-cream disabled:opacity-50"
                >
                  {isCreating ? "Creating..." : "Create Task"}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

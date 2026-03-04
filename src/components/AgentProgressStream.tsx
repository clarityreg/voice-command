"use client";

import { useEffect, useRef } from "react";
import type { AgentEvent } from "@/lib/api";

interface AgentProgressStreamProps {
  events: AgentEvent[];
}

export default function AgentProgressStream({ events }: AgentProgressStreamProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  if (events.length === 0) {
    return null;
  }

  return (
    <div className="max-h-64 overflow-y-auto rounded-md bg-cream p-2">
      {events.map((event, idx) => {
        if (event.type === "assistant" || event.type === "text") {
          const text = (event.data.text as string) ?? (event.data.content as string) ?? "";
          return (
            <div key={idx} className="mb-2 rounded-card bg-cream-light p-3 text-bark">
              {text}
            </div>
          );
        }
        if (event.type === "tool_use") {
          const name = (event.data.name as string) ?? "tool";
          const input = JSON.stringify(event.data.input ?? {});
          return (
            <div key={idx} className="mb-2 font-mono text-xs text-bark-muted">
              <span className="font-semibold text-accent">{name}</span>{" "}
              <span>{input.length > 80 ? `${input.slice(0, 80)}…` : input}</span>
            </div>
          );
        }
        if (event.type === "tool_result") {
          const content = (event.data.content as string) ?? JSON.stringify(event.data);
          return (
            <div key={idx} className="mb-2 whitespace-pre-wrap font-mono text-sm text-bark-light">
              {content.length > 200 ? `${content.slice(0, 200)}…` : content}
            </div>
          );
        }
        return null;
      })}
      <div ref={bottomRef} />
    </div>
  );
}

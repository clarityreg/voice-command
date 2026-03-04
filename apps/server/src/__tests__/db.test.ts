import { test, expect, beforeAll, beforeEach, describe } from "bun:test";
import {
  initDatabase,
  insertEvent,
  getRecentEvents,
  getFilterOptions,
  updateEventHITLResponse,
  insertTheme,
  getTheme,
  getThemes,
  updateTheme,
  deleteTheme,
  incrementThemeDownloadCount,
  db,
} from "../db";
import type { HookEvent, Theme } from "../types";

// Initialize the database once before all tests
beforeAll(() => {
  initDatabase();
});

// Clean tables before each test so tests are isolated
beforeEach(() => {
  db.exec("DELETE FROM theme_ratings");
  db.exec("DELETE FROM theme_shares");
  db.exec("DELETE FROM themes");
  db.exec("DELETE FROM events");
});

// ---------------------------------------------------------------------------
// initDatabase
// ---------------------------------------------------------------------------
describe("initDatabase", () => {
  test("creates the events table", () => {
    const rows = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
      )
      .all() as any[];
    expect(rows.length).toBe(1);
  });

  test("creates the themes table", () => {
    const rows = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='themes'"
      )
      .all() as any[];
    expect(rows.length).toBe(1);
  });

  test("creates the theme_shares table", () => {
    const rows = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='theme_shares'"
      )
      .all() as any[];
    expect(rows.length).toBe(1);
  });

  test("creates the theme_ratings table", () => {
    const rows = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='theme_ratings'"
      )
      .all() as any[];
    expect(rows.length).toBe(1);
  });

  test("creates indexes on events table", () => {
    const indexes = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='events'"
      )
      .all() as any[];
    const indexNames = indexes.map((i: any) => i.name);
    expect(indexNames).toContain("idx_source_app");
    expect(indexNames).toContain("idx_session_id");
    expect(indexNames).toContain("idx_hook_event_type");
    expect(indexNames).toContain("idx_timestamp");
  });

  test("events table has all expected columns", () => {
    const columns = db.prepare("PRAGMA table_info(events)").all() as any[];
    const columnNames = columns.map((c: any) => c.name);
    expect(columnNames).toContain("id");
    expect(columnNames).toContain("source_app");
    expect(columnNames).toContain("session_id");
    expect(columnNames).toContain("hook_event_type");
    expect(columnNames).toContain("payload");
    expect(columnNames).toContain("chat");
    expect(columnNames).toContain("summary");
    expect(columnNames).toContain("timestamp");
    expect(columnNames).toContain("humanInTheLoop");
    expect(columnNames).toContain("humanInTheLoopStatus");
    expect(columnNames).toContain("model_name");
  });
});

// ---------------------------------------------------------------------------
// insertEvent
// ---------------------------------------------------------------------------
describe("insertEvent", () => {
  test("inserts a valid event and returns it with id and timestamp", () => {
    const event: HookEvent = {
      source_app: "test-app",
      session_id: "session-1",
      hook_event_type: "PreToolUse",
      payload: { tool: "Bash", command: "ls" },
    };

    const result = insertEvent(event);

    expect(result.id).toBeDefined();
    expect(typeof result.id).toBe("number");
    expect(result.timestamp).toBeDefined();
    expect(typeof result.timestamp).toBe("number");
    expect(result.source_app).toBe("test-app");
    expect(result.session_id).toBe("session-1");
    expect(result.hook_event_type).toBe("PreToolUse");
  });

  test("auto-generates timestamp when not provided", () => {
    const before = Date.now();
    const result = insertEvent({
      source_app: "test-app",
      session_id: "session-1",
      hook_event_type: "Stop",
      payload: {},
    });
    const after = Date.now();

    expect(result.timestamp).toBeGreaterThanOrEqual(before);
    expect(result.timestamp).toBeLessThanOrEqual(after);
  });

  test("uses provided timestamp when given", () => {
    const fixedTimestamp = 1700000000000;
    const result = insertEvent({
      source_app: "test-app",
      session_id: "session-1",
      hook_event_type: "Stop",
      payload: {},
      timestamp: fixedTimestamp,
    });

    expect(result.timestamp).toBe(fixedTimestamp);
  });

  test("inserts event with HITL data and sets pending status", () => {
    const event: HookEvent = {
      source_app: "test-app",
      session_id: "session-1",
      hook_event_type: "PermissionRequest",
      payload: { action: "write" },
      humanInTheLoop: {
        question: "Allow write?",
        responseWebSocketUrl: "ws://localhost:9999",
        type: "permission",
      },
    };

    const result = insertEvent(event);

    expect(result.humanInTheLoopStatus).toBeDefined();
    expect(result.humanInTheLoopStatus!.status).toBe("pending");
  });

  test("inserts event with chat and summary", () => {
    const event: HookEvent = {
      source_app: "test-app",
      session_id: "session-1",
      hook_event_type: "Stop",
      payload: {},
      chat: [{ role: "user", content: "hello" }],
      summary: "A greeting session",
    };

    const result = insertEvent(event);
    expect(result.id).toBeDefined();

    // Verify persisted by reading back
    const events = getRecentEvents(1);
    expect(events.length).toBe(1);
    expect(events[0].chat).toEqual([{ role: "user", content: "hello" }]);
    expect(events[0].summary).toBe("A greeting session");
  });

  test("inserts event with model_name", () => {
    const result = insertEvent({
      source_app: "test-app",
      session_id: "session-1",
      hook_event_type: "Stop",
      payload: {},
      model_name: "claude-opus-4",
    });

    const events = getRecentEvents(1);
    expect(events[0].model_name).toBe("claude-opus-4");
  });
});

// ---------------------------------------------------------------------------
// getRecentEvents
// ---------------------------------------------------------------------------
describe("getRecentEvents", () => {
  test("returns empty array when no events exist", () => {
    const events = getRecentEvents();
    expect(events).toEqual([]);
  });

  test("returns events in chronological order (oldest first)", () => {
    insertEvent({
      source_app: "app",
      session_id: "s1",
      hook_event_type: "A",
      payload: {},
      timestamp: 1000,
    });
    insertEvent({
      source_app: "app",
      session_id: "s1",
      hook_event_type: "B",
      payload: {},
      timestamp: 3000,
    });
    insertEvent({
      source_app: "app",
      session_id: "s1",
      hook_event_type: "C",
      payload: {},
      timestamp: 2000,
    });

    const events = getRecentEvents();

    // The function fetches DESC then reverses, so should be chronological
    expect(events[0].hook_event_type).toBe("A");
    expect(events[1].hook_event_type).toBe("C");
    expect(events[2].hook_event_type).toBe("B");
  });

  test("respects limit parameter", () => {
    for (let i = 0; i < 10; i++) {
      insertEvent({
        source_app: "app",
        session_id: "s1",
        hook_event_type: `Event-${i}`,
        payload: {},
        timestamp: 1000 + i,
      });
    }

    const events = getRecentEvents(3);
    expect(events.length).toBe(3);
    // Should be the 3 most recent, in chronological order
    expect(events[0].hook_event_type).toBe("Event-7");
    expect(events[1].hook_event_type).toBe("Event-8");
    expect(events[2].hook_event_type).toBe("Event-9");
  });

  test("parses payload JSON correctly", () => {
    insertEvent({
      source_app: "app",
      session_id: "s1",
      hook_event_type: "Test",
      payload: { nested: { key: "value" }, count: 42 },
    });

    const events = getRecentEvents(1);
    expect(events[0].payload).toEqual({ nested: { key: "value" }, count: 42 });
  });
});

// ---------------------------------------------------------------------------
// getFilterOptions
// ---------------------------------------------------------------------------
describe("getFilterOptions", () => {
  test("returns empty arrays when no events exist", () => {
    const options = getFilterOptions();
    expect(options.source_apps).toEqual([]);
    expect(options.session_ids).toEqual([]);
    expect(options.hook_event_types).toEqual([]);
  });

  test("returns distinct values", () => {
    insertEvent({
      source_app: "app-a",
      session_id: "s1",
      hook_event_type: "PreToolUse",
      payload: {},
    });
    insertEvent({
      source_app: "app-b",
      session_id: "s1",
      hook_event_type: "PreToolUse",
      payload: {},
    });
    insertEvent({
      source_app: "app-a",
      session_id: "s2",
      hook_event_type: "Stop",
      payload: {},
    });

    const options = getFilterOptions();

    expect(options.source_apps.sort()).toEqual(["app-a", "app-b"]);
    expect(options.session_ids.sort()).toEqual(["s1", "s2"]);
    expect(options.hook_event_types.sort()).toEqual(["PreToolUse", "Stop"]);
  });
});

// ---------------------------------------------------------------------------
// updateEventHITLResponse
// ---------------------------------------------------------------------------
describe("updateEventHITLResponse", () => {
  test("updates HITL status to responded", () => {
    const event = insertEvent({
      source_app: "app",
      session_id: "s1",
      hook_event_type: "PermissionRequest",
      payload: {},
      humanInTheLoop: {
        question: "Allow?",
        responseWebSocketUrl: "ws://localhost:9999",
        type: "permission",
      },
    });

    const response = {
      permission: true,
      respondedAt: Date.now(),
      hookEvent: event,
    };

    const updated = updateEventHITLResponse(event.id!, response);

    expect(updated).not.toBeNull();
    expect(updated!.humanInTheLoopStatus!.status).toBe("responded");
    expect(updated!.humanInTheLoopStatus!.response).toBeDefined();
    expect(updated!.humanInTheLoopStatus!.response.permission).toBe(true);
  });

  test("returns null for non-existent event id", () => {
    const result = updateEventHITLResponse(99999, {
      respondedAt: Date.now(),
      hookEvent: {} as any,
    });

    expect(result).toBeNull();
  });

  test("preserves original event data after HITL update", () => {
    const event = insertEvent({
      source_app: "my-app",
      session_id: "sess-42",
      hook_event_type: "PermissionRequest",
      payload: { tool: "Write", path: "/tmp/file" },
      humanInTheLoop: {
        question: "Allow write to /tmp/file?",
        responseWebSocketUrl: "ws://localhost:9999",
        type: "permission",
      },
    });

    updateEventHITLResponse(event.id!, {
      permission: true,
      respondedAt: Date.now(),
      hookEvent: event,
    });

    const updated = getRecentEvents(1)[0];
    expect(updated.source_app).toBe("my-app");
    expect(updated.session_id).toBe("sess-42");
    expect(updated.payload).toEqual({ tool: "Write", path: "/tmp/file" });
  });
});

// ---------------------------------------------------------------------------
// Theme DB functions
// ---------------------------------------------------------------------------
function makeTheme(overrides: Partial<Theme> = {}): Theme {
  return {
    id: overrides.id ?? "theme-" + Math.random().toString(36).substr(2, 8),
    name: overrides.name ?? "test-theme",
    displayName: overrides.displayName ?? "Test Theme",
    description: overrides.description ?? "A test theme",
    colors: overrides.colors ?? ({
      primary: "#000000",
      primaryHover: "#111111",
      primaryLight: "#222222",
      primaryDark: "#333333",
      bgPrimary: "#ffffff",
      bgSecondary: "#eeeeee",
      bgTertiary: "#dddddd",
      bgQuaternary: "#cccccc",
      textPrimary: "#000000",
      textSecondary: "#111111",
      textTertiary: "#222222",
      textQuaternary: "#333333",
      borderPrimary: "#aaaaaa",
      borderSecondary: "#bbbbbb",
      borderTertiary: "#cccccc",
      accentSuccess: "#00ff00",
      accentWarning: "#ffff00",
      accentError: "#ff0000",
      accentInfo: "#0000ff",
      shadow: "rgba(0,0,0,0.1)",
      shadowLg: "rgba(0,0,0,0.2)",
      hoverBg: "#f0f0f0",
      activeBg: "#e0e0e0",
      focusRing: "#4488ff",
    } as any),
    isPublic: overrides.isPublic ?? true,
    authorId: overrides.authorId ?? "author-1",
    authorName: overrides.authorName ?? "Test Author",
    createdAt: overrides.createdAt ?? Date.now(),
    updatedAt: overrides.updatedAt ?? Date.now(),
    tags: overrides.tags ?? ["dark", "modern"],
    downloadCount: overrides.downloadCount ?? 0,
    rating: overrides.rating ?? 0,
    ratingCount: overrides.ratingCount ?? 0,
  };
}

describe("insertTheme", () => {
  test("inserts and returns the theme", () => {
    const theme = makeTheme();
    const result = insertTheme(theme);

    expect(result.id).toBe(theme.id);
    expect(result.name).toBe(theme.name);
  });

  test("persists theme to database", () => {
    const theme = makeTheme({ id: "persist-check" });
    insertTheme(theme);

    const fetched = getTheme("persist-check");
    expect(fetched).not.toBeNull();
    expect(fetched!.name).toBe(theme.name);
    expect(fetched!.displayName).toBe(theme.displayName);
    expect(fetched!.colors).toEqual(theme.colors);
  });
});

describe("getTheme", () => {
  test("returns null for non-existent theme", () => {
    const result = getTheme("non-existent");
    expect(result).toBeNull();
  });

  test("returns theme with parsed colors and tags", () => {
    const theme = makeTheme({ tags: ["retro", "warm"] });
    insertTheme(theme);

    const fetched = getTheme(theme.id);
    expect(fetched!.tags).toEqual(["retro", "warm"]);
    expect(typeof fetched!.colors).toBe("object");
    expect(fetched!.colors.primary).toBe("#000000");
  });
});

describe("getThemes", () => {
  test("returns all themes when no query given", () => {
    insertTheme(makeTheme({ id: "t1", name: "theme-one" }));
    insertTheme(makeTheme({ id: "t2", name: "theme-two" }));

    const themes = getThemes();
    expect(themes.length).toBe(2);
  });

  test("filters by isPublic", () => {
    insertTheme(makeTheme({ id: "pub", name: "pub-theme", isPublic: true }));
    insertTheme(
      makeTheme({ id: "priv", name: "priv-theme", isPublic: false })
    );

    const publicThemes = getThemes({ isPublic: true });
    expect(publicThemes.length).toBe(1);
    expect(publicThemes[0].name).toBe("pub-theme");
  });

  test("filters by authorId", () => {
    insertTheme(
      makeTheme({ id: "a1", name: "a1-theme", authorId: "author-x" })
    );
    insertTheme(
      makeTheme({ id: "a2", name: "a2-theme", authorId: "author-y" })
    );

    const themes = getThemes({ authorId: "author-x" });
    expect(themes.length).toBe(1);
    expect(themes[0].authorId).toBe("author-x");
  });

  test("respects limit and offset", () => {
    for (let i = 0; i < 5; i++) {
      insertTheme(
        makeTheme({
          id: `lim-${i}`,
          name: `lim-theme-${i}`,
          createdAt: 1000 + i,
        })
      );
    }

    const themes = getThemes({ limit: 2 });
    expect(themes.length).toBe(2);
  });
});

describe("updateTheme", () => {
  test("updates allowed fields", () => {
    const theme = makeTheme({ id: "upd-1", name: "upd-theme" });
    insertTheme(theme);

    const success = updateTheme("upd-1", {
      displayName: "Updated Display Name",
      updatedAt: Date.now(),
    });

    expect(success).toBe(true);
    const fetched = getTheme("upd-1");
    expect(fetched!.displayName).toBe("Updated Display Name");
  });

  test("returns false for non-existent theme", () => {
    const success = updateTheme("no-such-id", { displayName: "Nope" });
    expect(success).toBe(false);
  });

  test("ignores disallowed fields", () => {
    const theme = makeTheme({ id: "upd-2", name: "upd-theme-2" });
    insertTheme(theme);

    // 'name' is not in the allowed fields list
    const success = updateTheme("upd-2", { name: "hacked-name" } as any);
    expect(success).toBe(false); // No valid fields => empty setClause => returns false
  });
});

describe("deleteTheme", () => {
  test("deletes an existing theme", () => {
    insertTheme(makeTheme({ id: "del-1", name: "del-theme" }));

    const success = deleteTheme("del-1");
    expect(success).toBe(true);
    expect(getTheme("del-1")).toBeNull();
  });

  test("returns false for non-existent theme", () => {
    const success = deleteTheme("no-such-id");
    expect(success).toBe(false);
  });
});

describe("incrementThemeDownloadCount", () => {
  test("increments download count", () => {
    insertTheme(makeTheme({ id: "dl-1", name: "dl-theme", downloadCount: 5 }));

    const success = incrementThemeDownloadCount("dl-1");
    expect(success).toBe(true);

    const fetched = getTheme("dl-1");
    expect(fetched!.downloadCount).toBe(6);
  });

  test("returns false for non-existent theme", () => {
    const success = incrementThemeDownloadCount("no-such-id");
    expect(success).toBe(false);
  });
});

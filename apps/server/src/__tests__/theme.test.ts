import { test, expect, beforeAll, beforeEach, describe } from "bun:test";
import { initDatabase, db } from "../db";
import {
  createTheme,
  updateThemeById,
  getThemeById,
  searchThemes,
  deleteThemeById,
  exportThemeById,
  importTheme,
  getThemeStats,
} from "../theme";
import type { ThemeColors } from "../types";

// Initialize the database once before all tests
beforeAll(() => {
  initDatabase();
});

// Clean theme tables before each test
beforeEach(() => {
  db.exec("DELETE FROM theme_ratings");
  db.exec("DELETE FROM theme_shares");
  db.exec("DELETE FROM themes");
});

/**
 * Generates valid theme data with all 24 required color keys.
 * Override any fields by passing a partial object.
 */
function makeValidThemeData(overrides: Record<string, any> = {}) {
  const colors: ThemeColors = {
    primary: "#6366f1",
    primaryHover: "#4f46e5",
    primaryLight: "#818cf8",
    primaryDark: "#4338ca",
    bgPrimary: "#ffffff",
    bgSecondary: "#f9fafb",
    bgTertiary: "#f3f4f6",
    bgQuaternary: "#e5e7eb",
    textPrimary: "#111827",
    textSecondary: "#374151",
    textTertiary: "#6b7280",
    textQuaternary: "#9ca3af",
    borderPrimary: "#d1d5db",
    borderSecondary: "#e5e7eb",
    borderTertiary: "#f3f4f6",
    accentSuccess: "#10b981",
    accentWarning: "#f59e0b",
    accentError: "#ef4444",
    accentInfo: "#3b82f6",
    shadow: "rgba(0,0,0,0.1)",
    shadowLg: "rgba(0,0,0,0.2)",
    hoverBg: "#f3f4f6",
    activeBg: "#e5e7eb",
    focusRing: "#6366f1",
  };

  return {
    name: "test-theme",
    displayName: "Test Theme",
    description: "A theme for testing",
    colors,
    isPublic: true,
    authorId: "author-1",
    authorName: "Test Author",
    tags: ["dark", "modern"],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// createTheme
// ---------------------------------------------------------------------------
describe("createTheme", () => {
  test("creates a valid theme successfully", async () => {
    const data = makeValidThemeData();
    const result = await createTheme(data);

    expect(result.success).toBe(true);
    expect(result.data).toBeDefined();
    expect(result.data!.name).toBe("test-theme");
    expect(result.data!.displayName).toBe("Test Theme");
    expect(result.data!.id).toBeDefined();
    expect(result.data!.id.length).toBeGreaterThan(0);
    expect(result.message).toBe("Theme created successfully");
  });

  test("returns error for duplicate name", async () => {
    const data = makeValidThemeData({ name: "duplicate-theme" });
    await createTheme(data);

    const result = await createTheme(
      makeValidThemeData({ name: "duplicate-theme" })
    );

    expect(result.success).toBe(false);
    expect(result.error).toContain("already exists");
    expect(result.validationErrors).toBeDefined();
    expect(result.validationErrors![0].code).toBe("DUPLICATE");
  });

  test("returns validation error when name is missing", async () => {
    const data = makeValidThemeData({ name: "" });
    const result = await createTheme(data);

    expect(result.success).toBe(false);
    expect(result.error).toBe("Validation failed");
    expect(result.validationErrors).toBeDefined();
    const nameError = result.validationErrors!.find(
      (e) => e.field === "name"
    );
    expect(nameError).toBeDefined();
    expect(nameError!.code).toBe("REQUIRED");
  });

  test("sanitizes invalid name format into valid name", async () => {
    // sanitizeTheme lowercases and strips non [a-z0-9-_] chars,
    // so "Invalid Name With Spaces!" becomes "invalidnamewithspaces" — which is valid
    const data = makeValidThemeData({ name: "Invalid Name With Spaces!" });
    const result = await createTheme(data);

    expect(result.success).toBe(true);
    expect(result.data!.name).toBe("invalidnamewithspaces");
  });

  test("returns validation error for name that sanitizes to empty", async () => {
    const data = makeValidThemeData({ name: "!!!" });
    const result = await createTheme(data);

    expect(result.success).toBe(false);
    expect(result.validationErrors).toBeDefined();
    const nameError = result.validationErrors!.find(
      (e) => e.field === "name"
    );
    expect(nameError).toBeDefined();
  });

  test("returns validation error when colors are missing", async () => {
    // sanitizeTheme converts undefined colors to {} via `theme.colors || {}`,
    // so validation sees an empty object and flags individual missing color keys
    const data = makeValidThemeData({ colors: undefined });
    const result = await createTheme(data);

    expect(result.success).toBe(false);
    expect(result.validationErrors).toBeDefined();
    // Should have errors for individual required color keys (not a top-level "colors" REQUIRED)
    const colorErrors = result.validationErrors!.filter(
      (e) => e.field.startsWith("colors.")
    );
    expect(colorErrors.length).toBeGreaterThan(0);
    expect(colorErrors[0].code).toBe("REQUIRED");
  });

  test("returns validation error when displayName is missing", async () => {
    const data = makeValidThemeData({ displayName: "" });
    const result = await createTheme(data);

    expect(result.success).toBe(false);
    const displayNameError = result.validationErrors!.find(
      (e) => e.field === "displayName"
    );
    expect(displayNameError).toBeDefined();
    expect(displayNameError!.code).toBe("REQUIRED");
  });

  test("returns validation error for missing individual color keys", async () => {
    const colors = { ...makeValidThemeData().colors };
    delete (colors as any).primary;
    delete (colors as any).bgPrimary;

    const data = makeValidThemeData({ colors });
    const result = await createTheme(data);

    expect(result.success).toBe(false);
    expect(result.validationErrors).toBeDefined();
    const primaryError = result.validationErrors!.find(
      (e) => e.field === "colors.primary"
    );
    expect(primaryError).toBeDefined();
  });

  test("assigns createdAt and updatedAt timestamps", async () => {
    const before = Date.now();
    const result = await createTheme(makeValidThemeData({ name: "ts-theme" }));
    const after = Date.now();

    expect(result.data!.createdAt).toBeGreaterThanOrEqual(before);
    expect(result.data!.createdAt).toBeLessThanOrEqual(after);
    expect(result.data!.updatedAt).toBeGreaterThanOrEqual(before);
  });
});

// ---------------------------------------------------------------------------
// getThemeById
// ---------------------------------------------------------------------------
describe("getThemeById", () => {
  test("returns existing theme", async () => {
    const created = await createTheme(
      makeValidThemeData({ name: "get-theme" })
    );
    const id = created.data!.id;

    const result = await getThemeById(id);

    expect(result.success).toBe(true);
    expect(result.data).toBeDefined();
    expect(result.data!.id).toBe(id);
    expect(result.data!.name).toBe("get-theme");
  });

  test("returns error for non-existent theme", async () => {
    const result = await getThemeById("non-existent-id");

    expect(result.success).toBe(false);
    expect(result.error).toBe("Theme not found");
  });
});

// ---------------------------------------------------------------------------
// updateThemeById
// ---------------------------------------------------------------------------
describe("updateThemeById", () => {
  test("updates an existing theme", async () => {
    const created = await createTheme(
      makeValidThemeData({ name: "update-me" })
    );
    const id = created.data!.id;

    const result = await updateThemeById(id, {
      displayName: "Updated Display Name",
      description: "Updated description",
      colors: makeValidThemeData().colors,
    });

    expect(result.success).toBe(true);
    expect(result.data!.displayName).toBe("Updated Display Name");
    expect(result.message).toBe("Theme updated successfully");
  });

  test("returns error for non-existent theme", async () => {
    const result = await updateThemeById("no-such-id", {
      displayName: "Nope",
    });

    expect(result.success).toBe(false);
    expect(result.error).toBe("Theme not found");
  });
});

// ---------------------------------------------------------------------------
// deleteThemeById
// ---------------------------------------------------------------------------
describe("deleteThemeById", () => {
  test("deletes an existing theme", async () => {
    const created = await createTheme(
      makeValidThemeData({ name: "delete-me" })
    );
    const id = created.data!.id;

    const result = await deleteThemeById(id);

    expect(result.success).toBe(true);
    expect(result.message).toBe("Theme deleted successfully");

    // Verify it is gone
    const fetched = await getThemeById(id);
    expect(fetched.success).toBe(false);
  });

  test("returns error for non-existent theme", async () => {
    const result = await deleteThemeById("no-such-id");

    expect(result.success).toBe(false);
    expect(result.error).toContain("not found");
  });

  test("returns unauthorized error for wrong authorId", async () => {
    const created = await createTheme(
      makeValidThemeData({ name: "auth-theme", authorId: "owner-1" })
    );
    const id = created.data!.id;

    const result = await deleteThemeById(id, "different-user");

    expect(result.success).toBe(false);
    expect(result.error).toContain("Unauthorized");
  });
});

// ---------------------------------------------------------------------------
// searchThemes
// ---------------------------------------------------------------------------
describe("searchThemes", () => {
  test("returns empty array when no themes exist", async () => {
    const result = await searchThemes({});

    expect(result.success).toBe(true);
    expect(result.data).toEqual([]);
  });

  test("filters by public themes by default", async () => {
    await createTheme(
      makeValidThemeData({ name: "public-one", isPublic: true })
    );
    await createTheme(
      makeValidThemeData({ name: "private-one", isPublic: false })
    );

    const result = await searchThemes({});

    expect(result.success).toBe(true);
    // searchThemes defaults to isPublic: true when no authorId given
    expect(result.data!.length).toBe(1);
    expect(result.data![0].name).toBe("public-one");
  });

  test("returns all themes for a specific author regardless of public status", async () => {
    await createTheme(
      makeValidThemeData({
        name: "author-pub",
        isPublic: true,
        authorId: "author-x",
      })
    );
    await createTheme(
      makeValidThemeData({
        name: "author-priv",
        isPublic: false,
        authorId: "author-x",
      })
    );

    const result = await searchThemes({ authorId: "author-x" });

    expect(result.success).toBe(true);
    expect(result.data!.length).toBe(2);
  });
});

// ---------------------------------------------------------------------------
// exportThemeById
// ---------------------------------------------------------------------------
describe("exportThemeById", () => {
  test("exports a valid theme", async () => {
    const created = await createTheme(
      makeValidThemeData({ name: "export-theme", isPublic: true })
    );
    const id = created.data!.id;

    const result = await exportThemeById(id);

    expect(result.success).toBe(true);
    expect(result.data).toBeDefined();
    expect(result.data.version).toBe("1.0.0");
    expect(result.data.theme).toBeDefined();
    expect(result.data.theme.name).toBe("export-theme");
    expect(result.data.exportedAt).toBeDefined();
    expect(result.data.exportedBy).toBe("observability-system");
    // Server-specific fields should be undefined in export
    expect(result.data.theme.id).toBeUndefined();
    expect(result.data.theme.authorId).toBeUndefined();
  });

  test("returns error for non-existent theme", async () => {
    const result = await exportThemeById("no-such-id");

    expect(result.success).toBe(false);
    expect(result.error).toContain("not found");
  });
});

// ---------------------------------------------------------------------------
// importTheme
// ---------------------------------------------------------------------------
describe("importTheme", () => {
  test("imports a valid theme", async () => {
    const importData = {
      version: "1.0.0",
      theme: {
        name: "imported-theme",
        displayName: "Imported Theme",
        colors: makeValidThemeData().colors,
        tags: ["imported"],
      },
    };

    const result = await importTheme(importData, "importer-1");

    expect(result.success).toBe(true);
    expect(result.data).toBeDefined();
    expect(result.data!.name).toBe("imported-theme");
    // Imported themes default to private
    expect(result.data!.isPublic).toBe(false);
    expect(result.data!.authorId).toBe("importer-1");
  });

  test("returns error for missing theme in import data", async () => {
    const result = await importTheme({}, "importer-1");

    expect(result.success).toBe(false);
    expect(result.error).toContain("missing theme");
  });
});

// ---------------------------------------------------------------------------
// getThemeStats
// ---------------------------------------------------------------------------
describe("getThemeStats", () => {
  test("returns correct statistics for empty database", async () => {
    const result = await getThemeStats();

    expect(result.success).toBe(true);
    expect(result.data).toBeDefined();
    expect(result.data.totalThemes).toBe(0);
    expect(result.data.publicThemes).toBe(0);
    expect(result.data.privateThemes).toBe(0);
    expect(result.data.totalDownloads).toBe(0);
    expect(result.data.averageRating).toBe(0);
  });

  test("returns correct statistics with themes present", async () => {
    await createTheme(
      makeValidThemeData({ name: "stat-pub-1", isPublic: true })
    );
    await createTheme(
      makeValidThemeData({ name: "stat-pub-2", isPublic: true })
    );
    await createTheme(
      makeValidThemeData({ name: "stat-priv-1", isPublic: false })
    );

    const result = await getThemeStats();

    expect(result.success).toBe(true);
    expect(result.data.totalThemes).toBe(3);
    expect(result.data.publicThemes).toBe(2);
    expect(result.data.privateThemes).toBe(1);
  });
});

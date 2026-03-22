import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import VocabularyEditor from "./VocabularyEditor";

vi.mock("@/lib/whisper", () => ({
  isTauri: vi.fn(() => false),
  getCustomVocab: vi.fn(),
  saveCustomVocab: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  getPlaneProjects: vi.fn(),
}));

import { isTauri, getCustomVocab, saveCustomVocab } from "@/lib/whisper";
import { getPlaneProjects } from "@/lib/api";
const mockedIsTauri = vi.mocked(isTauri);
const mockedGetCustomVocab = vi.mocked(getCustomVocab);
const mockedSaveCustomVocab = vi.mocked(saveCustomVocab);
const mockedGetPlaneProjects = vi.mocked(getPlaneProjects);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("VocabularyEditor", () => {
  it("renders nothing when not in Tauri", () => {
    mockedIsTauri.mockReturnValue(false);
    const { container } = render(<VocabularyEditor />);
    expect(container.firstChild).toBeNull();
  });

  it("loads and displays existing vocabulary", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetCustomVocab.mockResolvedValue(["PostHog", "OWASP", "CVE"]);

    render(<VocabularyEditor />);

    await waitFor(() => {
      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveValue("PostHog\nOWASP\nCVE");
    });
  });

  it("saves vocabulary on button click", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetCustomVocab.mockResolvedValue([]);
    mockedSaveCustomVocab.mockResolvedValue(undefined);

    render(<VocabularyEditor />);

    await waitFor(() => {
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "PostHog\nOWASP" },
    });
    fireEvent.click(screen.getByText("Save Vocabulary"));

    await waitFor(() => {
      expect(mockedSaveCustomVocab).toHaveBeenCalledWith(["PostHog", "OWASP"]);
      expect(screen.getByText("Saved")).toBeInTheDocument();
    });
  });

  it("handles getCustomVocab failure gracefully", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetCustomVocab.mockRejectedValue(new Error("fail"));

    render(<VocabularyEditor />);
    await waitFor(() => {
      expect(screen.getByText("Custom Vocabulary")).toBeInTheDocument();
    });
  });

  it("imports project names from Plane", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetCustomVocab.mockResolvedValue([]);
    mockedGetPlaneProjects.mockResolvedValue({
      projects: {
        clarity: { id: "p1", name: "Clarity Command Centre", identifier: "CC" },
      },
    });

    render(<VocabularyEditor />);
    await waitFor(() => {
      expect(screen.getByText("Import Project Names")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Import Project Names"));
    await waitFor(() => {
      const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
      expect(textarea.value).toContain("clarity");
      expect(textarea.value).toContain("Clarity Command Centre");
    });
  });

  it("does not duplicate existing terms on import", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetCustomVocab.mockResolvedValue(["clarity"]);
    mockedGetPlaneProjects.mockResolvedValue({
      projects: {
        clarity: { id: "p1", name: "Clarity", identifier: "CC" },
      },
    });

    render(<VocabularyEditor />);
    await waitFor(() => {
      expect(screen.getByDisplayValue("clarity")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Import Project Names"));
    await waitFor(() => {
      const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
      // "clarity" and "Clarity" (case-insensitive) already exist — no new terms
      expect(textarea.value).toBe("clarity");
    });
  });

  it("clears saved indicator when text changes", async () => {
    mockedIsTauri.mockReturnValue(true);
    mockedGetCustomVocab.mockResolvedValue(["term1"]);
    mockedSaveCustomVocab.mockResolvedValue(undefined);

    render(<VocabularyEditor />);
    await waitFor(() => {
      expect(screen.getByDisplayValue("term1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Save Vocabulary"));
    await waitFor(() => {
      expect(screen.getByText("Saved")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "term1\nterm2" } });
    expect(screen.queryByText("Saved")).not.toBeInTheDocument();
  });
});

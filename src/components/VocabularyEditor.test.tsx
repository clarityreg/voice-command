import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import VocabularyEditor from "./VocabularyEditor";

vi.mock("@/lib/whisper", () => ({
  isTauri: vi.fn(() => false),
  getCustomVocab: vi.fn(),
  saveCustomVocab: vi.fn(),
}));

import { isTauri, getCustomVocab, saveCustomVocab } from "@/lib/whisper";
const mockedIsTauri = vi.mocked(isTauri);
const mockedGetCustomVocab = vi.mocked(getCustomVocab);
const mockedSaveCustomVocab = vi.mocked(saveCustomVocab);

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
});

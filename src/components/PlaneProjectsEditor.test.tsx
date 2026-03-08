import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import PlaneProjectsEditor from "./PlaneProjectsEditor";

vi.mock("@/lib/api", () => ({
  getPlaneProjects: vi.fn(),
  syncPlaneProjects: vi.fn(),
  updateProjectAlias: vi.fn(),
  deleteProjectAlias: vi.fn(),
}));

import { getPlaneProjects, syncPlaneProjects, updateProjectAlias, deleteProjectAlias } from "@/lib/api";
const mockGetProjects = vi.mocked(getPlaneProjects);
const mockSyncProjects = vi.mocked(syncPlaneProjects);
const mockUpdateAlias = vi.mocked(updateProjectAlias);
const mockDeleteAlias = vi.mocked(deleteProjectAlias);

beforeEach(() => {
  vi.clearAllMocks();
});

const sampleProjects = {
  clarity: { id: "p1", name: "Clarity Command Centre", identifier: "CC" },
  frontend: { id: "p2", name: "Frontend App", identifier: "FA" },
};

describe("PlaneProjectsEditor", () => {
  it("shows empty state when no projects", async () => {
    mockGetProjects.mockResolvedValue({ projects: {} });
    render(<PlaneProjectsEditor />);
    await waitFor(() => {
      expect(screen.getByText(/No projects synced yet/)).toBeInTheDocument();
    });
  });

  it("loads and displays projects", async () => {
    mockGetProjects.mockResolvedValue({ projects: sampleProjects });
    render(<PlaneProjectsEditor />);
    await waitFor(() => {
      expect(screen.getByText("clarity")).toBeInTheDocument();
      expect(screen.getByText("Clarity Command Centre")).toBeInTheDocument();
      expect(screen.getByText("CC")).toBeInTheDocument();
      expect(screen.getByText("frontend")).toBeInTheDocument();
    });
  });

  it("shows project count", async () => {
    mockGetProjects.mockResolvedValue({ projects: sampleProjects });
    render(<PlaneProjectsEditor />);
    await waitFor(() => {
      expect(screen.getByText("Voice Aliases (2 projects)")).toBeInTheDocument();
    });
  });

  it("syncs projects from Plane", async () => {
    mockGetProjects.mockResolvedValue({ projects: {} });
    mockSyncProjects.mockResolvedValue({ projects: sampleProjects });
    render(<PlaneProjectsEditor />);
    await waitFor(() => {
      expect(screen.getByText("Sync from Plane")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Sync from Plane"));
    await waitFor(() => {
      expect(mockSyncProjects).toHaveBeenCalled();
      expect(screen.getByText("Projects synced successfully")).toBeInTheDocument();
    });
  });

  it("shows error from sync API response", async () => {
    mockGetProjects.mockResolvedValue({ projects: {} });
    mockSyncProjects.mockResolvedValue({ projects: {}, error: "API key invalid" });
    render(<PlaneProjectsEditor />);
    await waitFor(() => {
      expect(screen.getByText("Sync from Plane")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Sync from Plane"));
    await waitFor(() => {
      expect(screen.getByText("API key invalid")).toBeInTheDocument();
    });
  });

  it("shows error when sync throws", async () => {
    mockGetProjects.mockResolvedValue({ projects: {} });
    mockSyncProjects.mockRejectedValue(new Error("Network error"));
    render(<PlaneProjectsEditor />);
    await waitFor(() => {
      expect(screen.getByText("Sync from Plane")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Sync from Plane"));
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("disables sync button while syncing", async () => {
    mockGetProjects.mockResolvedValue({ projects: {} });
    let resolveSync: (v: { projects: Record<string, never> }) => void;
    mockSyncProjects.mockReturnValue(
      new Promise((resolve) => { resolveSync = resolve; }),
    );
    render(<PlaneProjectsEditor />);
    await waitFor(() => {
      expect(screen.getByText("Sync from Plane")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Sync from Plane"));
    expect(screen.getByText("Syncing...")).toBeDisabled();
    resolveSync!({ projects: {} });
    await waitFor(() => {
      expect(screen.queryByText("Syncing...")).not.toBeInTheDocument();
    });
  });

  it("allows editing an alias", async () => {
    mockGetProjects.mockResolvedValue({ projects: sampleProjects });
    mockUpdateAlias.mockResolvedValue({ projects: { ...sampleProjects, "new-alias": sampleProjects.clarity } });
    render(<PlaneProjectsEditor />);
    await waitFor(() => {
      expect(screen.getByText("clarity")).toBeInTheDocument();
    });

    // Click alias to start editing
    fireEvent.click(screen.getByText("clarity"));
    const input = screen.getByDisplayValue("clarity");
    fireEvent.change(input, { target: { value: "new-alias" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(mockUpdateAlias).toHaveBeenCalledWith("clarity", { new_alias: "new-alias" });
    });
  });

  it("cancels edit on Escape", async () => {
    mockGetProjects.mockResolvedValue({ projects: sampleProjects });
    render(<PlaneProjectsEditor />);
    await waitFor(() => {
      expect(screen.getByText("clarity")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("clarity"));
    const input = screen.getByDisplayValue("clarity");
    fireEvent.keyDown(input, { key: "Escape" });

    // Should go back to button view
    expect(screen.getByText("clarity")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("does not save if alias unchanged", async () => {
    mockGetProjects.mockResolvedValue({ projects: sampleProjects });
    render(<PlaneProjectsEditor />);
    await waitFor(() => {
      expect(screen.getByText("clarity")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("clarity"));
    const input = screen.getByDisplayValue("clarity");
    fireEvent.blur(input);

    expect(mockUpdateAlias).not.toHaveBeenCalled();
  });

  it("deletes an alias", async () => {
    mockGetProjects.mockResolvedValue({ projects: sampleProjects });
    mockDeleteAlias.mockResolvedValue({ projects: { frontend: sampleProjects.frontend } });
    render(<PlaneProjectsEditor />);
    await waitFor(() => {
      expect(screen.getByText("clarity")).toBeInTheDocument();
    });

    // Find delete button (×) for clarity row
    const deleteButtons = screen.getAllByTitle("Remove alias");
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(mockDeleteAlias).toHaveBeenCalledWith("clarity");
    });
  });

  it("handles load failure gracefully", async () => {
    mockGetProjects.mockRejectedValue(new Error("fail"));
    render(<PlaneProjectsEditor />);
    await waitFor(() => {
      // Should still render with empty state
      expect(screen.getByText(/No projects synced yet/)).toBeInTheDocument();
    });
  });
});

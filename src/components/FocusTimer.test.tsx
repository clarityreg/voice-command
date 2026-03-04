import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import FocusTimer from "./FocusTimer";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("FocusTimer", () => {
  // Shows idle state with 25:00 default
  it("shows 25:00 in idle state", () => {
    render(<FocusTimer />);
    expect(screen.getByTestId("timer-display")).toHaveTextContent("25:00");
    expect(screen.getByText("ready")).toBeInTheDocument();
    expect(screen.getByText("Start Focus")).toBeInTheDocument();
  });

  // Start Focus begins countdown
  it("starts countdown on Start Focus click", () => {
    render(<FocusTimer />);
    fireEvent.click(screen.getByText("Start Focus"));
    expect(screen.getByText("focus")).toBeInTheDocument();
    expect(screen.getByText("Pause")).toBeInTheDocument();
    expect(screen.getByText("Reset")).toBeInTheDocument();
  });

  // Timer ticks down after 1 second
  it("ticks down after 1 second", () => {
    render(<FocusTimer />);
    fireEvent.click(screen.getByText("Start Focus"));
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByTestId("timer-display")).toHaveTextContent("24:59");
  });

  // Pause stops the countdown
  it("pauses the timer", () => {
    render(<FocusTimer />);
    fireEvent.click(screen.getByText("Start Focus"));
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    fireEvent.click(screen.getByText("Pause"));
    const timeAfterPause = screen.getByTestId("timer-display").textContent;
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    // Time should not have changed
    expect(screen.getByTestId("timer-display")).toHaveTextContent(timeAfterPause!);
  });

  // Reset returns to idle
  it("resets to idle state", () => {
    render(<FocusTimer />);
    fireEvent.click(screen.getByText("Start Focus"));
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    fireEvent.click(screen.getByText("Reset"));
    expect(screen.getByTestId("timer-display")).toHaveTextContent("25:00");
    expect(screen.getByText("ready")).toBeInTheDocument();
  });

  // Timer completes and shows done state
  it("shows done state when timer completes", () => {
    render(<FocusTimer />);
    fireEvent.click(screen.getByText("Start Focus"));
    act(() => {
      vi.advanceTimersByTime(25 * 60 * 1000);
    });
    expect(screen.getByText("done!")).toBeInTheDocument();
    expect(screen.getByText(/Time's up/)).toBeInTheDocument();
    expect(screen.getByText("Start Break")).toBeInTheDocument();
    expect(screen.getByText("New Focus")).toBeInTheDocument();
  });

  // Start Break begins 5-minute countdown
  it("starts 5-minute break after focus", () => {
    render(<FocusTimer />);
    fireEvent.click(screen.getByText("Start Focus"));
    act(() => {
      vi.advanceTimersByTime(25 * 60 * 1000);
    });
    fireEvent.click(screen.getByText("Start Break"));
    expect(screen.getByTestId("timer-display")).toHaveTextContent("5:00");
    expect(screen.getByText("break")).toBeInTheDocument();
  });
});

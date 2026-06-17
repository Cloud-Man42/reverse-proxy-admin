import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAutoRefresh } from "./useAutoRefresh";

describe("useAutoRefresh", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("polls on interval when enabled", () => {
    const callback = vi.fn();
    renderHook(({ enabled }) => useAutoRefresh(enabled, 1000, callback), {
      initialProps: { enabled: true },
    });

    expect(callback).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1000);
    expect(callback).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(2000);
    expect(callback).toHaveBeenCalledTimes(3);
  });

  it("does not poll when disabled", () => {
    const callback = vi.fn();
    renderHook(({ enabled }) => useAutoRefresh(enabled, 1000, callback), {
      initialProps: { enabled: false },
    });

    vi.advanceTimersByTime(5000);
    expect(callback).not.toHaveBeenCalled();
  });
});

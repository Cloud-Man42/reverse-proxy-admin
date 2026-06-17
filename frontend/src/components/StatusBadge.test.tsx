import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("maps known statuses to classes", () => {
    const { container } = render(<StatusBadge status="valid" />);
    expect(container.firstChild).toHaveClass("text-emerald-300");
  });

  it("falls back for unknown statuses", () => {
    const { container } = render(<StatusBadge status="unknown-status" />);
    expect(container.firstChild).toHaveClass("text-slate-300");
    expect(screen.getByText("unknown-status")).toBeInTheDocument();
  });
});

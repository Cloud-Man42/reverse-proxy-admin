import { describe, expect, it } from "vitest";
import { MetricCard } from "./MetricCard";

describe("MetricCard", () => {
  it("exports a component", () => {
    expect(typeof MetricCard).toBe("function");
  });
});

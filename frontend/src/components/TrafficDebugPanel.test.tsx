import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TrafficDebugPanel } from "./TrafficDebugPanel";
import { renderWithQueryClient } from "../test/test-utils";

const proxyTrafficDebug = vi.fn();

vi.mock("../api/client", () => ({
  api: {
    proxyTrafficDebug: (...args: unknown[]) => proxyTrafficDebug(...args),
  },
}));

describe("TrafficDebugPanel", () => {
  beforeEach(() => {
    proxyTrafficDebug.mockReset();
  });

  it("shows idle message until debug mode is enabled", () => {
    renderWithQueryClient(<TrafficDebugPanel proxyId="demo" domains={["demo.example.com"]} />);
    expect(screen.getByText(/Enable debug mode/i)).toBeInTheDocument();
  });

  it("shows warning when dedicated log is unavailable", async () => {
    proxyTrafficDebug.mockResolvedValue({
      proxy_id: "demo",
      proxy_name: "demo",
      domains: ["demo.example.com"],
      dedicated_log: false,
      source: "/var/log/nginx/access.log",
      entries: [],
    });

    renderWithQueryClient(<TrafficDebugPanel proxyId="demo" domains={["demo.example.com"]} />);
    await userEvent.click(screen.getByLabelText(/Debug mode/i));

    await waitFor(() => {
      expect(screen.getByText(/Per-proxy logging is not active yet/i)).toBeInTheDocument();
    });
  });

  it("shows empty-state message when there are no entries", async () => {
    proxyTrafficDebug.mockResolvedValue({
      proxy_id: "demo",
      proxy_name: "demo",
      domains: ["demo.example.com"],
      dedicated_log: true,
      source: "/var/log/nginx/proxy-demo.log",
      entries: [],
    });

    renderWithQueryClient(<TrafficDebugPanel proxyId="demo" domains={["demo.example.com"]} />);
    await userEvent.click(screen.getByLabelText(/Debug mode/i));

    await waitFor(() => {
      expect(screen.getByText(/No matching requests yet/i)).toBeInTheDocument();
    });
  });
});

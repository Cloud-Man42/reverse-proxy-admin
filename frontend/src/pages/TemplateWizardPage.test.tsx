import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { TemplateWizardPage } from "../pages/TemplateWizardPage";
import { AuthProvider } from "../hooks/useAuth";
import { ToastProvider } from "../hooks/useToast";

vi.mock("../api/client", () => ({
  api: {
    me: vi.fn().mockRejectedValue(new Error("unauthenticated")),
    getTemplate: vi.fn().mockResolvedValue({
      id: 1,
      slug: "grafana",
      name: "Grafana",
      description: "Metrics dashboard",
      group: "monitoring-observability",
      category: "Monitoring",
      icon: "activity",
      tags: [],
      availability_level: "free",
      optimized: true,
      default_upstream_protocol: "http",
      default_upstream_port: 3000,
      websocket_support: true,
      large_upload_support: false,
      https_upstream_supported: false,
      http_to_https_redirect_default: true,
      recommended_headers: [],
      security_headers: [],
      slug_aliases: [],
      hsts_recommended: false,
      defaults: {},
      builtin: true,
    }),
    previewTemplate: vi.fn(),
    createProxyFromTemplate: vi.fn(),
  },
  setCsrfToken: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

describe("TemplateWizardPage", () => {
  it("renders step 1 and advances to domain step", async () => {
    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/templates/grafana/wizard"]}>
          <AuthProvider>
            <ToastProvider>
              <Routes>
                <Route path="/templates/:slug/wizard" element={<TemplateWizardPage />} />
              </Routes>
            </ToastProvider>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText("Setup wizard")).toBeInTheDocument();
    expect(screen.getByText("Grafana")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByPlaceholderText("app.example.com")).toBeInTheDocument();
  });
});

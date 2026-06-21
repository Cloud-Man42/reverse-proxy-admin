import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { Checkbox } from "../components/Checkbox";
import { NginxConfigPreview } from "../components/catalog/NginxConfigPreview";
import { RecommendedSettingsPanel } from "../components/catalog/RecommendedSettingsPanel";
import { TemplateBadges } from "../components/catalog/TemplateBadges";
import { WIZARD_STEP_COUNT, WizardStepper } from "../components/catalog/WizardStepper";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { buildInitialWizardState, wizardStateToPreviewPayload } from "../lib/templateWizard";
import { TemplateCreateProxyResponse, TemplatePreviewResponse, TemplateWizardState } from "../types";

function parseInitialStep(raw: string | null): number {
  const step = Number(raw);
  if (Number.isFinite(step) && step >= 1 && step <= WIZARD_STEP_COUNT) {
    return step;
  }
  return 1;
}

export function TemplateWizardPage() {
  const { slug = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { canCreate } = useAuth();
  const { showError, showSuccess } = useToast();
  const [step, setStep] = useState(() => parseInitialStep(searchParams.get("step")));
  const [wizard, setWizard] = useState<TemplateWizardState | null>(null);
  const [preview, setPreview] = useState<TemplatePreviewResponse | null>(null);
  const [createResult, setCreateResult] = useState<TemplateCreateProxyResponse | null>(null);

  const { data: template, isLoading, isError } = useQuery({
    queryKey: ["template", slug],
    queryFn: () => api.getTemplate(slug),
    enabled: Boolean(slug),
  });

  useEffect(() => {
    if (template && !wizard) {
      setWizard(buildInitialWizardState(template));
    }
  }, [template, wizard]);

  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    next.set("step", String(step));
    setSearchParams(next, { replace: true });
  }, [step, searchParams, setSearchParams]);

  const previewMutation = useMutation({
    mutationFn: () => api.previewTemplate(slug, wizardStateToPreviewPayload(wizard!)),
    onSuccess: (result) => {
      setPreview(result);
      setStep(6);
    },
    onError: (error) => showError(error instanceof ApiError ? error.message : "Preview failed"),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.createProxyFromTemplate(slug, {
        ...wizardStateToPreviewPayload(wizard!),
        name: wizard!.name,
        enabled: wizard!.enabled,
      }),
    onSuccess: (result) => {
      setCreateResult(result);
      if (result.success) {
        showSuccess(result.message || "Proxy created");
      } else {
        showError(result.message || "Proxy creation failed");
      }
    },
    onError: (error) => showError(error instanceof ApiError ? error.message : "Create failed"),
  });

  const canAdvance = useMemo(() => {
    if (!wizard) return false;
    if (step === 2) return wizard.domain.trim().length > 0;
    if (step === 3) return wizard.upstream_host.trim().length > 0 && wizard.upstream_port > 0;
    if (step === 7) return wizard.name.trim().length > 0;
    return true;
  }, [step, wizard]);

  const updateWizard = (patch: Partial<TemplateWizardState>) => {
    setWizard((current) => (current ? { ...current, ...patch } : current));
  };

  const goNext = () => {
    if (step === 5) {
      previewMutation.mutate();
      return;
    }
    if (step < WIZARD_STEP_COUNT) {
      setStep((current) => current + 1);
    }
  };

  const goBack = () => {
    if (step > 1) {
      setStep((current) => current - 1);
    }
  };

  const onCreate = (event: FormEvent) => {
    event.preventDefault();
    if (!canCreate) {
      showError("You do not have permission to create proxies.");
      return;
    }
    createMutation.mutate();
  };

  if (isLoading || !wizard) {
    return <p>Loading wizard...</p>;
  }

  if (isError || !template) {
    return (
      <div className="space-y-3">
        <Link to="/templates" className="text-sm text-accent hover:underline">
          ← Application Catalog
        </Link>
        <p>Template not found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <Link to={`/templates/${encodeURIComponent(template.slug)}`} className="text-sm text-accent hover:underline">
          ← {template.name}
        </Link>
        <h2 className="mt-1 text-2xl font-semibold">Setup wizard</h2>
        <p className="text-sm text-white/60">Configure and deploy a proxy host from the {template.name} template.</p>
      </div>

      <WizardStepper currentStep={step} />

      <Card>
        {step === 1 ? (
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-medium">{template.name}</h3>
              <p className="text-sm text-white/60">{template.description}</p>
            </div>
            <TemplateBadges template={template} />
            <p className="text-sm text-white/70">
              This wizard walks through domain, upstream, recommended nginx settings, preview, and safe proxy creation.
            </p>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="space-y-3">
            <label className="block text-sm">
              <span className="mb-1 block text-white/70">Public domain</span>
              <input
                type="text"
                value={wizard.domain}
                onChange={(event) => updateWizard({ domain: event.target.value })}
                placeholder="app.example.com"
                className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
              />
            </label>
            <p className="text-xs text-white/50">Issue a certificate for this domain before enabling HTTPS redirect.</p>
          </div>
        ) : null}

        {step === 3 ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm sm:col-span-2">
              <span className="mb-1 block text-white/70">Upstream host</span>
              <input
                type="text"
                value={wizard.upstream_host}
                onChange={(event) => updateWizard({ upstream_host: event.target.value })}
                className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-white/70">Upstream port</span>
              <input
                type="number"
                min={1}
                max={65535}
                value={wizard.upstream_port}
                onChange={(event) => updateWizard({ upstream_port: Number(event.target.value) })}
                className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-white/70">Upstream protocol</span>
              <select
                value={wizard.upstream_protocol}
                onChange={(event) =>
                  updateWizard({ upstream_protocol: event.target.value as TemplateWizardState["upstream_protocol"] })
                }
                className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
              >
                <option value="http">HTTP</option>
                <option value="https">HTTPS</option>
              </select>
            </label>
          </div>
        ) : null}

        {step === 4 ? (
          <div className="space-y-3">
            <Checkbox
              checked={wizard.websocket_enabled}
              onChange={(checked) => updateWizard({ websocket_enabled: checked })}
              label="Enable WebSocket proxying"
            />
            <Checkbox
              checked={wizard.force_https}
              onChange={(checked) => updateWizard({ force_https: checked })}
              label="Redirect HTTP to HTTPS"
            />
            {template.large_upload_support ? (
              <>
                <Checkbox
                  checked={wizard.large_upload_enabled}
                  onChange={(checked) => updateWizard({ large_upload_enabled: checked })}
                  label="Enable large upload body size"
                />
                {wizard.large_upload_enabled ? (
                  <label className="block text-sm">
                    <span className="mb-1 block text-white/70">client_max_body_size</span>
                    <input
                      type="text"
                      value={wizard.max_body_size}
                      onChange={(event) => updateWizard({ max_body_size: event.target.value })}
                      className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
                    />
                  </label>
                ) : null}
              </>
            ) : null}
            <Checkbox
              checked={wizard.hsts_enabled}
              onChange={(checked) => updateWizard({ hsts_enabled: checked })}
              label="Enable HSTS (requires HTTPS)"
            />
            <Checkbox
              checked={wizard.apply_recommended_headers}
              onChange={(checked) => updateWizard({ apply_recommended_headers: checked })}
              label="Apply recommended proxy headers"
            />
            <Checkbox
              checked={wizard.apply_security_headers}
              onChange={(checked) => updateWizard({ apply_security_headers: checked })}
              label="Apply security headers"
            />
          </div>
        ) : null}

        {step === 5 ? <RecommendedSettingsPanel template={template} state={wizard} /> : null}

        {step === 6 ? (
          <NginxConfigPreview
            config={preview?.rendered_config || ""}
            warnings={preview?.warnings}
            loading={previewMutation.isPending}
          />
        ) : null}

        {step === 7 ? (
          <form onSubmit={onCreate} className="space-y-4">
            <label className="block text-sm">
              <span className="mb-1 block text-white/70">Proxy name</span>
              <input
                type="text"
                value={wizard.name}
                onChange={(event) => updateWizard({ name: event.target.value })}
                className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
              />
            </label>
            <Checkbox
              checked={wizard.enabled}
              onChange={(checked) => updateWizard({ enabled: checked })}
              label="Enable proxy after creation"
            />
            {createResult ? (
              <div
                className={`rounded-lg border p-4 text-sm ${
                  createResult.success
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"
                    : "border-red-500/30 bg-red-500/10 text-red-100"
                }`}
              >
                <p>{createResult.message}</p>
                {createResult.failure_stage ? <p className="mt-1 text-xs opacity-80">Stage: {createResult.failure_stage}</p> : null}
                {createResult.success ? (
                  <button
                    type="button"
                    onClick={() => navigate("/proxies")}
                    className="mt-3 rounded-lg bg-accent px-3 py-2 text-sm text-white"
                  >
                    Go to proxies
                  </button>
                ) : null}
              </div>
            ) : null}
          </form>
        ) : null}

        <div className="mt-6 flex flex-wrap gap-2 border-t border-white/10 pt-4">
          {step > 1 && step < 7 ? (
            <button type="button" onClick={goBack} className="rounded-lg bg-white/10 px-4 py-2 text-sm">
              Back
            </button>
          ) : null}
          {step < 5 ? (
            <button
              type="button"
              onClick={goNext}
              disabled={!canAdvance}
              className="rounded-lg bg-accent px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              Next
            </button>
          ) : null}
          {step === 5 ? (
            <button
              type="button"
              onClick={goNext}
              disabled={!canAdvance || previewMutation.isPending}
              className="rounded-lg bg-accent px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {previewMutation.isPending ? "Generating preview..." : "Preview nginx config"}
            </button>
          ) : null}
          {step === 6 ? (
            <button type="button" onClick={() => setStep(7)} className="rounded-lg bg-accent px-4 py-2 text-sm text-white">
              Continue to create
            </button>
          ) : null}
          {step === 7 && canCreate && !createResult?.success ? (
            <button
              type="button"
              onClick={() => createMutation.mutate()}
              disabled={!canAdvance || createMutation.isPending}
              className="rounded-lg bg-accent px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {createMutation.isPending ? "Creating..." : "Create proxy host"}
            </button>
          ) : null}
        </div>
      </Card>
    </div>
  );
}

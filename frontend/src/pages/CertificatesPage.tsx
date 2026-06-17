import { FormEvent, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { StatusBadge } from "../components/StatusBadge";
import { useToast } from "../hooks/useToast";

export function CertificatesPage() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const [domain, setDomain] = useState("");
  const [email, setEmail] = useState("");
  const [confirm, setConfirm] = useState<{ action: "renew" | "dry-run"; name?: string } | null>(null);

  const { data = [], isLoading } = useQuery({ queryKey: ["certificates"], queryFn: api.listCertificates });
  const { data: settings } = useQuery({ queryKey: ["certificate-settings"], queryFn: api.certificateSettings });

  useEffect(() => {
    if (settings?.email_configured && settings.default_email) {
      setEmail(settings.default_email);
    }
  }, [settings]);

  const issue = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const result = await api.issueCertificate(domain, email.trim() || undefined);
      showSuccess(result.message);
      queryClient.invalidateQueries({ queryKey: ["certificates"] });
      setDomain("");
    } catch (error) {
      showError(error instanceof ApiError ? error.message : "Issue failed");
    }
  };

  const runConfirm = async () => {
    if (!confirm) return;
    try {
      if (confirm.action === "renew" && confirm.name) {
        const result = await api.renewCertificate(confirm.name);
        showSuccess(result.message);
      } else {
        const result = await api.dryRunRenew();
        showSuccess(result.message);
      }
      queryClient.invalidateQueries({ queryKey: ["certificates"] });
    } catch (error) {
      showError(error instanceof ApiError ? error.message : "Action failed");
    } finally {
      setConfirm(null);
    }
  };

  const emailConfigured = settings?.email_configured ?? false;

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold">Certificates</h2>

      <Card title="Issue new certificate">
        {!emailConfigured ? (
          <p className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
            Certbot requires a real contact email. Set <code className="text-xs">CERTBOT_EMAIL</code> in{" "}
            <code className="text-xs">/etc/nginx-admin/env</code> or enter one below. Placeholder addresses such as{" "}
            <code className="text-xs">admin@example.com</code> are rejected by Let&apos;s Encrypt.
          </p>
        ) : null}
        <form className="flex flex-col gap-3" onSubmit={issue}>
          <div className="flex flex-col gap-3 md:flex-row">
            <input
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="example.com"
              required
              className="flex-1"
            />
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@yourdomain.com"
              type="email"
              required={!emailConfigured}
              className="flex-1"
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <button type="submit" className="rounded-lg bg-accent px-4 py-2 text-sm text-white">
              Create certificate
            </button>
            <button type="button" className="rounded-lg bg-white/10 px-4 py-2 text-sm" onClick={() => setConfirm({ action: "dry-run" })}>
              Dry-run renew
            </button>
          </div>
        </form>
      </Card>

      <Card title="Installed certificates">
        {isLoading ? (
          <p>Loading...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-white/60">
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Domain</th>
                  <th className="px-3 py-2">Issuer</th>
                  <th className="px-3 py-2">Expiry</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.map((cert) => (
                  <tr key={cert.name} className="border-b border-white/5">
                    <td className="px-3 py-3">{cert.name}</td>
                    <td className="px-3 py-3">{cert.domains.join(", ")}</td>
                    <td className="px-3 py-3 text-xs">{cert.issuer}</td>
                    <td className="px-3 py-3">{new Date(cert.expiry).toLocaleString()}</td>
                    <td className="px-3 py-3">
                      <StatusBadge status={cert.status} />
                    </td>
                    <td className="px-3 py-3">
                      <button className="rounded bg-white/10 px-2 py-1" onClick={() => setConfirm({ action: "renew", name: cert.name })}>
                        Renew
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={!!confirm}
        title="Confirm certificate action"
        message={confirm?.action === "renew" ? `Renew ${confirm.name}?` : "Run certbot renew dry-run?"}
        onConfirm={runConfirm}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}

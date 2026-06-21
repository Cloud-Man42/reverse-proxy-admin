import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card } from "../components/Card";
import { MetricCard, MetricGrid, DataTable } from "../components/metrics";
import { StatusBadge } from "../components/StatusBadge";

export function SslStatisticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["metrics-ssl"],
    queryFn: api.metricsSsl,
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">SSL Statistics</h2>
        <p className="text-sm text-white/60">Certificate inventory, expiry, and renewal status.</p>
      </div>

      {isLoading || !data ? (
        <p>Loading SSL metrics...</p>
      ) : (
        <>
          <MetricGrid columns={4}>
            <MetricCard label="Total" value={String(data.total)} />
            <MetricCard label="Valid" value={String(data.valid)} tone="success" />
            <MetricCard label="Expiring soon" value={String(data.expiring_soon)} tone="warning" />
            <MetricCard label="Expired" value={String(data.expired)} tone="danger" />
          </MetricGrid>

          <Card title="Certificates">
            <DataTable
              rows={data.items}
              rowKey={(row) => row.domain}
              columns={[
                { key: "domain", label: "Domain" },
                { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
                { key: "days_remaining", label: "Days left", render: (row) => String(row.days_remaining) },
                { key: "issuer", label: "Issuer" },
                {
                  key: "expires_at",
                  label: "Expires",
                  render: (row) => new Date(row.expires_at).toLocaleDateString(),
                },
              ]}
            />
          </Card>
        </>
      )}
    </div>
  );
}

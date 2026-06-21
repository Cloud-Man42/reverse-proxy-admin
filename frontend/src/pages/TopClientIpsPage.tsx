import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { Card } from "../components/Card";
import { DataTable, MetricsPageHeader } from "../components/metrics";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { MetricsClientIpItem, MetricsRange } from "../types";

export function TopClientIpsPage() {
  const [range, setRange] = useState<MetricsRange>("24h");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const { isAdmin } = useAuth();
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["metrics-client-ips", range],
    queryFn: () => api.metricsClientIps(range),
  });

  const blockMutation = useMutation({
    mutationFn: (clientIp: string) =>
      api.createIpRule({
        scope: "global",
        rule_type: "deny",
        cidr: `${clientIp}/32`,
        enabled: true,
        notes: `Blocked from client IP analytics (${range})`,
      }),
    onSuccess: () => {
      showSuccess("IP block rule created");
      queryClient.invalidateQueries({ queryKey: ["metrics-client-ips"] });
    },
    onError: (error) => {
      showError(error instanceof ApiError ? error.message : "Could not block IP");
    },
  });

  return (
    <div className="space-y-6">
      <MetricsPageHeader
        title="Top Client IPs"
        description="Highest-traffic client addresses with optional block actions."
        range={range}
        onRangeChange={setRange}
        autoRefresh={autoRefresh}
        onAutoRefreshChange={setAutoRefresh}
        onRefresh={() => refetch()}
      />

      <Card title="Top clients">
        <DataTable<MetricsClientIpItem>
          loading={isLoading}
          rows={data?.items ?? []}
          rowKey={(row) => row.client_ip}
          columns={[
            { key: "client_ip", label: "Client IP", className: "font-mono text-xs" },
            { key: "requests", label: "Requests", render: (row) => row.requests.toLocaleString() },
            { key: "errors", label: "Errors", render: (row) => row.errors.toLocaleString() },
            {
              key: "last_seen",
              label: "Last seen",
              render: (row) => (row.last_seen ? new Date(row.last_seen).toLocaleString() : "—"),
            },
            {
              key: "actions",
              label: "Actions",
              render: (row) =>
                isAdmin ? (
                  <button
                    type="button"
                    className="rounded bg-red-600/70 px-2 py-1 text-xs"
                    onClick={() => blockMutation.mutate(row.client_ip)}
                  >
                    Block
                  </button>
                ) : (
                  "—"
                ),
            },
          ]}
        />
      </Card>
    </div>
  );
}

import { memo, useCallback, useMemo, type MouseEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Node,
  NodeProps,
  Position,
  ReactFlow,
  Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { NetworkMapNode as MapNode } from "../types";

type MapNodeData = {
  label: string;
  subtitle?: string | null;
  status: string;
  nodeType: string;
  metadata: Record<string, unknown>;
};

const STATUS_STYLES: Record<string, string> = {
  active: "border-emerald-500/60 bg-emerald-500/10",
  inactive: "border-slate-500/60 bg-slate-500/10 opacity-70",
  warning: "border-amber-500/60 bg-amber-500/10",
  unknown: "border-slate-500/60 bg-slate-500/10",
};

const TYPE_LABELS: Record<string, string> = {
  internet: "Internet",
  firewall: "Firewall",
  reverse_proxy: "Reverse Proxy",
  proxy_app: "Web App",
  upstream: "Upstream",
  admin_ui: "Admin UI",
};

function MapFlowNode({ data }: NodeProps<Node<MapNodeData>>) {
  const style = STATUS_STYLES[data.status] || STATUS_STYLES.unknown;
  const clickable = data.nodeType === "proxy_app" && data.metadata.proxy_id;

  return (
    <div
      className={`min-w-[180px] max-w-[220px] rounded-xl border px-3 py-2 shadow-md ${style} ${
        clickable ? "cursor-pointer hover:ring-2 hover:ring-accent/50" : ""
      }`}
    >
      <Handle type="target" position={Position.Left} className="!bg-accent !w-2 !h-2" />
      <p className="text-[10px] uppercase tracking-wide text-white/50">{TYPE_LABELS[data.nodeType] || data.nodeType}</p>
      <p className="truncate text-sm font-semibold">{data.label}</p>
      {data.subtitle ? <p className="truncate text-xs text-white/60">{data.subtitle}</p> : null}
      <div className="mt-1 flex flex-wrap gap-1">
        <span className="rounded-full bg-black/20 px-2 py-0.5 text-[10px] capitalize">{data.status}</span>
        {data.metadata.https_enabled ? (
          <span className="rounded-full bg-blue-500/20 px-2 py-0.5 text-[10px] text-blue-200">HTTPS</span>
        ) : null}
        {data.metadata.websocket_enabled ? (
          <span className="rounded-full bg-purple-500/20 px-2 py-0.5 text-[10px] text-purple-200">WS</span>
        ) : null}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-accent !w-2 !h-2" />
    </div>
  );
}

const nodeTypes = { mapNode: memo(MapFlowNode) };

const COLUMN_X: Record<string, number> = {
  internet: 0,
  firewall: 280,
  reverse_proxy: 560,
  proxy_app: 840,
  admin_ui: 840,
  upstream: 1120,
};

function layoutNode(node: MapNode, y: number): Node<MapNodeData> {
  const x = COLUMN_X[node.type] ?? 0;
  return {
    id: node.id,
    type: "mapNode",
    position: { x, y },
    data: {
      label: node.label,
      subtitle: node.subtitle,
      status: node.status,
      nodeType: node.type,
      metadata: node.metadata,
    },
  };
}

function buildFlowElements(mapNodes: MapNode[], mapEdges: { id: string; source: string; target: string; label?: string | null }[]) {
  const core = mapNodes.filter((n) => ["internet", "firewall", "reverse_proxy"].includes(n.type));
  const apps = mapNodes.filter((n) => n.type === "proxy_app");
  const upstreams = mapNodes.filter((n) => n.type === "upstream");
  const admin = mapNodes.find((n) => n.type === "admin_ui");

  const rowCount = Math.max(apps.length, 1);
  const baseY = 40;
  const rowHeight = 130;
  const centerY = baseY + ((rowCount - 1) * rowHeight) / 2;

  const nodes: Node<MapNodeData>[] = [];
  for (const node of core) {
    nodes.push(layoutNode(node, centerY));
  }

  apps.forEach((app, index) => {
    nodes.push(layoutNode(app, baseY + index * rowHeight));
    const upstream = upstreams.find((u) => u.metadata.proxy_id === app.metadata.proxy_id);
    if (upstream) {
      nodes.push(layoutNode(upstream, baseY + index * rowHeight));
    }
  });

  if (admin) {
    nodes.push(layoutNode(admin, baseY + apps.length * rowHeight + 20));
  }

  const edges: Edge[] = mapEdges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label || undefined,
    animated: edge.source === "nginx" && edge.target.startsWith("app-"),
    style: { stroke: "rgba(96, 165, 250, 0.8)" },
    labelStyle: { fill: "#94a3b8", fontSize: 10 },
  }));

  return { nodes, edges };
}

export function NetworkMap() {
  const navigate = useNavigate();
  const { data, isLoading, isError } = useQuery({ queryKey: ["network-map"], queryFn: api.networkMap });

  const { nodes, edges } = useMemo(
    () => (data ? buildFlowElements(data.nodes, data.edges) : { nodes: [], edges: [] }),
    [data],
  );

  const onNodeClick = useCallback(
    (_: MouseEvent, node: Node<MapNodeData>) => {
      if (node.data.nodeType === "proxy_app" && node.data.metadata.proxy_id) {
        navigate(`/proxies/${node.data.metadata.proxy_id}/edit`);
      }
    },
    [navigate],
  );

  if (isLoading) {
    return <p className="text-sm text-white/60">Loading network map...</p>;
  }

  if (isError || !data) {
    return <p className="text-sm text-red-300">Could not load network map.</p>;
  }

  return (
    <div className="h-[480px] w-full overflow-hidden rounded-xl border border-white/10 bg-black/20">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={20} size={1} color="rgba(255,255,255,0.05)" />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const status = (node.data as MapNodeData)?.status;
            if (status === "active") return "#10b981";
            if (status === "warning") return "#f59e0b";
            return "#64748b";
          }}
          maskColor="rgba(0,0,0,0.6)"
        />
      </ReactFlow>
    </div>
  );
}

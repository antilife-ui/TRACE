import { useState } from 'react';
import Panel from '../components/common/Panel.jsx';
import MetricCard from '../components/common/MetricCard.jsx';
import { LoadingState, ErrorState, EmptyState } from '../components/common/AsyncStates.jsx';
import NetworkGraph from '../components/network/NetworkGraph.jsx';
import { useNetworkState } from '../hooks/useNetworkState.js';
import { useAttackPath } from '../hooks/useAttackPath.js';
import { formatPercent, formatNumber, riskLevel, formatRelativeTime } from '../utils/formatters.js';

export default function NetworkPage() {
  const network = useNetworkState();
  const attackPath = useAttackPath();
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);

  const handleNodeClick = (n) => {
    setSelectedEdge(null);
    setSelectedNode(n);
  };
  const handleEdgeClick = (e) => {
    setSelectedNode(null);
    setSelectedEdge(e);
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-text-primary">Network</h1>
        <p className="text-xs text-text-secondary mt-0.5">
          Current network state and topology — observed traffic vs. predicted attacker paths.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Current Risk"
          value={network.loading ? '—' : formatPercent(network.data?.riskScore)}
          tone={riskLevel(network.data?.riskScore)}
        />
        <MetricCard
          label="Active Flows"
          value={network.loading ? '—' : formatNumber(network.data?.metrics?.flowCount)}
          tone="neutral"
        />
        <MetricCard
          label="Flow Rate"
          value={network.loading ? '—' : network.data?.features?.flowRate}
          unit="/s"
          tone="neutral"
          mono
        />
        <MetricCard
          label="Window Updated"
          value={network.loading ? '—' : formatRelativeTime(network.data?.timestamp)}
          tone="neutral"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
        <Panel title="Network Threat Map">
          {attackPath.loading && <LoadingState label="Reading current network topology…" />}
          {!attackPath.loading && attackPath.error && <ErrorState onRetry={attackPath.refresh} />}
          {!attackPath.loading && !attackPath.error && !attackPath.data?.nodes?.length && (
            <EmptyState title="NO ACTIVE PATH" />
          )}
          {!attackPath.loading && attackPath.data?.nodes?.length > 0 && (
            <div className="h-[360px]">
              <NetworkGraph
                nodes={attackPath.data.nodes}
                edges={attackPath.data.edges}
                height={360}
                onNodeClick={handleNodeClick}
                onEdgeClick={handleEdgeClick}
                selectedNodeId={selectedNode?.id}
              />
            </div>
          )}
          <div className="flex items-center gap-5 mt-2 pt-2.5 border-t border-border text-[11px] text-text-secondary">
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-4 h-[1.5px] bg-text-secondary" /> Observed traffic
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-4 h-[1.5px]" style={{ borderTop: '1.5px dashed #8B7FE8' }} />
              Predicted path
            </span>
            <span className="text-text-muted">Click a node or edge to inspect it</span>
          </div>
        </Panel>

        <Panel title={selectedNode ? 'Host Details' : selectedEdge ? 'Flow Details' : 'Inspector'}>
          {!selectedNode && !selectedEdge && (
            <EmptyState title="NOTHING SELECTED" message="Select a node or edge on the map to inspect it." />
          )}
          {selectedNode && (
            <dl className="space-y-2.5 text-xs">
              <Row label="Label" value={selectedNode.label} />
              <Row label="Type" value={selectedNode.type} />
              <Row label="IP" value={selectedNode.ip} mono />
            </dl>
          )}
          {selectedEdge && (
            <dl className="space-y-2.5 text-xs">
              <Row label="Source" value={selectedEdge.source} mono />
              <Row label="Destination" value={selectedEdge.target} mono />
              <Row label="Protocol" value={selectedEdge.protocol} mono />
              <Row label="Port" value={selectedEdge.port} mono />
              <Row label="Classification" value={selectedEdge.kind} />
              <Row label="Risk" value={formatPercent(selectedEdge.riskScore)} />
            </dl>
          )}
        </Panel>
      </div>
    </div>
  );
}

function Row({ label, value, mono }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-text-muted">{label}</dt>
      <dd className={`text-text-primary ${mono ? 'font-mono' : ''}`}>{value ?? '—'}</dd>
    </div>
  );
}

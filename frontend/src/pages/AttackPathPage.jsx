import { useState } from 'react';
import Panel from '../components/common/Panel.jsx';
import { LoadingState, ErrorState, EmptyState } from '../components/common/AsyncStates.jsx';
import NetworkGraph from '../components/network/NetworkGraph.jsx';
import { useAttackPath } from '../hooks/useAttackPath.js';
import { formatPercent } from '../utils/formatters.js';

export default function AttackPathPage() {
  const attackPath = useAttackPath();
  const [selectedEdge, setSelectedEdge] = useState(null);

  const nodesById = new Map((attackPath.data?.nodes ?? []).map((n) => [n.id, n]));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-text-primary">Attack Path</h1>
        <p className="text-xs text-text-secondary mt-0.5">
          The chain of hosts the attacker has traversed, and the path the model expects next.
        </p>
      </div>

      {attackPath.loading && <LoadingState label="Reconstructing attack path…" />}
      {!attackPath.loading && attackPath.error && (
        <Panel>
          <ErrorState onRetry={attackPath.refresh} />
        </Panel>
      )}

      {!attackPath.loading && attackPath.data && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
          <Panel title="Path Visualization">
            <div className="h-[380px]">
              <NetworkGraph
                nodes={attackPath.data.nodes}
                edges={attackPath.data.edges}
                height={380}
                onEdgeClick={setSelectedEdge}
              />
            </div>
          </Panel>

          <div className="space-y-4">
            <Panel title="Observed Path">
              <ol className="space-y-2">
                {attackPath.data.edges
                  .filter((e) => e.kind === 'observed')
                  .map((e, i) => (
                    <PathStep
                      key={`${e.source}-${e.target}`}
                      index={i + 1}
                      from={nodesById.get(e.source)}
                      to={nodesById.get(e.target)}
                      edge={e}
                      onClick={() => setSelectedEdge(e)}
                    />
                  ))}
              </ol>
            </Panel>

            <Panel title="Predicted Path">
              {attackPath.data.edges.filter((e) => e.kind === 'predicted').length === 0 ? (
                <EmptyState title="NO PREDICTED SEGMENTS" />
              ) : (
                <ol className="space-y-2">
                  {attackPath.data.edges
                    .filter((e) => e.kind === 'predicted')
                    .map((e, i) => (
                      <PathStep
                        key={`${e.source}-${e.target}`}
                        index={i + 1}
                        from={nodesById.get(e.source)}
                        to={nodesById.get(e.target)}
                        edge={e}
                        predicted
                        onClick={() => setSelectedEdge(e)}
                      />
                    ))}
                </ol>
              )}
            </Panel>

            {selectedEdge && (
              <Panel title="Segment Evidence">
                <dl className="space-y-2 text-xs">
                  <Row label="Protocol" value={selectedEdge.protocol} mono />
                  <Row label="Port" value={selectedEdge.port} mono />
                  <Row label="Risk" value={formatPercent(selectedEdge.riskScore)} />
                  <Row label="Classification" value={selectedEdge.kind} />
                </dl>
              </Panel>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function PathStep({ index, from, to, edge, predicted, onClick }) {
  return (
    <li>
      <button
        onClick={onClick}
        className={`w-full text-left border px-3 py-2 text-xs transition-colors ${
          predicted ? 'border-predicted/40 hover:border-predicted' : 'border-border hover:border-border-strong'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-text-primary">
            {index}. {from?.label} → {to?.label}
          </span>
          <span className="font-mono text-text-muted">{formatPercent(edge.riskScore)}</span>
        </div>
      </button>
    </li>
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

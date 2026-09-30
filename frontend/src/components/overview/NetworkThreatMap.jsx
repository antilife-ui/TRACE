import { Link } from 'react-router-dom';
import Panel from '../common/Panel.jsx';
import NetworkGraph from '../network/NetworkGraph.jsx';
import { LoadingState, ErrorState, EmptyState } from '../common/AsyncStates.jsx';

export default function NetworkThreatMap({ data, loading, error, onRetry }) {
  return (
    <Panel
      title="Network Threat Map"
      action={
        <Link to="/network" className="text-xs text-accent hover:text-accent-bright">
          Open Network →
        </Link>
      }
    >
      {loading && <LoadingState label="Reading current network topology…" />}
      {!loading && error && <ErrorState onRetry={onRetry} />}
      {!loading && !error && !data?.nodes?.length && (
        <EmptyState title="NO ACTIVE PATH" message="No attack path is currently being tracked." />
      )}
      {!loading && !error && data?.nodes?.length > 0 && (
        <>
          <div className="h-[220px]">
            <NetworkGraph nodes={data.nodes} edges={data.edges} height={220} />
          </div>
          <div className="flex items-center gap-5 mt-2 pt-2.5 border-t border-border text-[11px] text-text-secondary">
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-4 h-[1.5px] bg-text-secondary" /> Observed traffic
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-4 h-[1.5px] bg-predicted" style={{ borderTop: '1.5px dashed #8B7FE8' }} />
              Predicted path
            </span>
          </div>
        </>
      )}
    </Panel>
  );
}

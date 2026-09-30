import { useState } from 'react';
import Panel from '../components/common/Panel.jsx';
import StatusBadge from '../components/common/StatusBadge.jsx';
import { LoadingState, ErrorState, EmptyState } from '../components/common/AsyncStates.jsx';
import { useIncidents } from '../hooks/useIncidents.js';
import { formatPercent, formatRelativeTime, riskLevel } from '../utils/formatters.js';

const STATUS_LEVEL = {
  NEW: 'critical',
  INVESTIGATING: 'warning',
  CONTAINED: 'accent',
  RESOLVED: 'healthy',
  ARCHIVED: 'unknown',
};

export default function IncidentsPage() {
  const incidents = useIncidents();
  const [selected, setSelected] = useState(null);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-text-primary">Incidents</h1>
        <p className="text-xs text-text-secondary mt-0.5">
          Forecast-driven incidents — grouped by attack progression, not just individual alerts.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
        <Panel title="Active & Recent Incidents">
          {incidents.loading && <LoadingState label="Loading incidents…" />}
          {!incidents.loading && incidents.error && <ErrorState onRetry={incidents.refresh} />}
          {!incidents.loading && incidents.data?.length === 0 && (
            <EmptyState
              title="NO ACTIVE INCIDENTS"
              message="No active forecasted threat transitions were returned."
            />
          )}
          {!incidents.loading && incidents.data?.length > 0 && (
            <div className="divide-y divide-border">
              {incidents.data.map((inc) => (
                <button
                  key={inc.id}
                  onClick={() => setSelected(inc)}
                  className={`w-full text-left py-3 px-1 hover:bg-elevated/50 transition-colors ${
                    selected?.id === inc.id ? 'bg-elevated/60' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-text-primary">{inc.id}</span>
                    <StatusBadge level={STATUS_LEVEL[inc.status] || 'unknown'} label={inc.status} dense />
                  </div>
                  <div className="flex items-center justify-between mt-1.5 text-xs text-text-secondary">
                    <span>
                      {inc.currentStage} → <span className="text-predicted">{inc.forecastStage}</span>
                    </span>
                    <span className="font-mono">{formatPercent(inc.riskScore)}</span>
                  </div>
                  <div className="text-[11px] text-text-muted mt-1">
                    Updated {formatRelativeTime(inc.lastUpdated)} · {inc.affectedHosts.length} host
                    {inc.affectedHosts.length === 1 ? '' : 's'} affected
                  </div>
                </button>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Incident Detail">
          {!selected && <EmptyState title="NO INCIDENT SELECTED" message="Select an incident to see full detail." />}
          {selected && (
            <dl className="space-y-2.5 text-xs">
              <Row label="Incident" value={selected.id} mono />
              <Row label="Status" value={selected.status} />
              <Row label="Risk" value={formatPercent(selected.riskScore)} tone={riskLevel(selected.riskScore)} />
              <Row label="Current Stage" value={selected.currentStage} />
              <Row label="Forecast Stage" value={selected.forecastStage} />
              <Row label="First Observed" value={new Date(selected.firstObserved).toLocaleString()} />
              <Row label="Last Updated" value={new Date(selected.lastUpdated).toLocaleString()} />
              <div>
                <dt className="text-text-muted mb-1">Affected Hosts</dt>
                <dd className="space-y-1">
                  {selected.affectedHosts.map((h) => (
                    <div key={h} className="font-mono text-text-primary">
                      {h}
                    </div>
                  ))}
                </dd>
              </div>
            </dl>
          )}
        </Panel>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-text-muted">{label}</dt>
      <dd className="text-text-primary">{value ?? '—'}</dd>
    </div>
  );
}

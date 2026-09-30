import { useState } from 'react';
import Panel from '../components/common/Panel.jsx';
import { LoadingState, ErrorState, EmptyState } from '../components/common/AsyncStates.jsx';
import TelemetryTable from '../components/telemetry/TelemetryTable.jsx';
import { useTelemetry } from '../hooks/useTelemetry.js';
import { formatBytes, formatPercent } from '../utils/formatters.js';

const PROTOCOLS = ['TCP', 'UDP', 'ICMP'];

export default function TelemetryPage() {
  const { records, total, page, pageSize, filters, setFilters, setPage, loading, error, refresh } =
    useTelemetry();
  const [selected, setSelected] = useState(null);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-text-primary">Telemetry</h1>
        <p className="text-xs text-text-secondary mt-0.5">
          Flow-level network telemetry backing the current risk assessment. Server-paginated —
          the browser never loads the full flow table.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-text-muted">Protocol:</span>
        <button
          onClick={() => setFilters({ ...filters, protocol: undefined })}
          className={`text-xs px-2.5 py-1 border ${
            !filters.protocol ? 'border-accent text-accent' : 'border-border text-text-secondary'
          }`}
        >
          All
        </button>
        {PROTOCOLS.map((p) => (
          <button
            key={p}
            onClick={() => setFilters({ ...filters, protocol: p })}
            className={`text-xs px-2.5 py-1 border font-mono ${
              filters.protocol === p ? 'border-accent text-accent' : 'border-border text-text-secondary'
            }`}
          >
            {p}
          </button>
        ))}
        <span className="text-xs text-text-muted ml-3">Min risk:</span>
        {[0, 0.5, 0.75].map((r) => (
          <button
            key={r}
            onClick={() => setFilters({ ...filters, minRisk: r || undefined })}
            className={`text-xs px-2.5 py-1 border ${
              (filters.minRisk ?? 0) === r ? 'border-accent text-accent' : 'border-border text-text-secondary'
            }`}
          >
            {r === 0 ? 'Any' : `${r * 100}%+`}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-4">
        <Panel
          title={`Flow Records (${total})`}
          action={
            <div className="flex items-center gap-2 text-xs text-text-secondary">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="px-2 py-0.5 border border-border disabled:opacity-30"
              >
                ‹
              </button>
              Page {page} / {totalPages}
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="px-2 py-0.5 border border-border disabled:opacity-30"
              >
                ›
              </button>
            </div>
          }
        >
          {loading && <LoadingState label="Loading telemetry…" />}
          {!loading && error && <ErrorState onRetry={refresh} />}
          {!loading && !error && records.length === 0 && (
            <EmptyState title="DATA UNAVAILABLE" message="The backend did not return telemetry for this window." />
          )}
          {!loading && records.length > 0 && (
            <TelemetryTable records={records} onSelectRow={setSelected} selectedId={selected?.id} />
          )}
        </Panel>

        <Panel title="Flow Detail">
          {!selected && <EmptyState title="NO FLOW SELECTED" message="Select a row to inspect its detail." />}
          {selected && (
            <dl className="space-y-2.5 text-xs">
              <Row label="Flow ID" value={selected.id} mono />
              <Row label="Source" value={`${selected.sourceIp}:${selected.sourcePort}`} mono />
              <Row label="Destination" value={`${selected.destinationIp}:${selected.destinationPort}`} mono />
              <Row label="Protocol" value={selected.protocol} mono />
              <Row label="Duration" value={`${selected.flowDuration} ms`} mono />
              <Row label="Packets" value={selected.packets} mono />
              <Row label="Bytes" value={formatBytes(selected.bytes)} mono />
              <Row label="Risk" value={formatPercent(selected.riskScore)} />
              <Row label="Stage" value={selected.stage} />
            </dl>
          )}
        </Panel>
      </div>
    </div>
  );
}

function Row({ label, value, mono }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-text-muted shrink-0">{label}</dt>
      <dd className={`text-text-primary text-right truncate ${mono ? 'font-mono' : ''}`}>{value ?? '—'}</dd>
    </div>
  );
}

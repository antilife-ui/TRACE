import Panel from '../components/common/Panel.jsx';
import MetricCard from '../components/common/MetricCard.jsx';
import StatusBadge from '../components/common/StatusBadge.jsx';
import { LoadingState, ErrorState } from '../components/common/AsyncStates.jsx';
import KStepErrorChart from '../components/model/KStepErrorChart.jsx';
import { useModelStatus } from '../hooks/useModelStatus.js';
import { formatNumber, formatRelativeTime } from '../utils/formatters.js';

function Bar({ used, total, label }) {
  const pct = total ? Math.min(100, (used / total) * 100) : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-text-secondary">{label}</span>
        <span className="font-mono text-text-muted">
          {formatNumber(used)} / {formatNumber(total)} MB
        </span>
      </div>
      <div className="h-1.5 bg-elevated w-full">
        <div className={`h-full ${pct > 85 ? 'bg-critical' : pct > 60 ? 'bg-warning' : 'bg-accent'}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function ModelPage() {
  const { data: m, loading, error, refresh } = useModelStatus();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-text-primary">Model</h1>
        <p className="text-xs text-text-secondary mt-0.5">
          World Model configuration, health, and evaluation metrics.
        </p>
      </div>

      {loading && (
        <Panel>
          <LoadingState label="Reading model status…" />
        </Panel>
      )}
      {!loading && error && (
        <Panel>
          <ErrorState onRetry={refresh} />
        </Panel>
      )}

      {!loading && m && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricCard label="World Model" value={m.type} tone="accent" />
            <MetricCard
              label="Status"
              value={
                <span className="text-base">
                  <StatusBadge level={m.status === 'ready' ? 'healthy' : 'critical'} label={m.status.toUpperCase()} />
                </span>
              }
            />
            <MetricCard label="Version" value={m.version} mono />
            <MetricCard label="Device" value={m.device?.toUpperCase()} mono />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Panel title="Configuration">
              <dl className="grid grid-cols-2 gap-y-3 text-xs">
                <Row label="State Features" value={m.stateFeatures} />
                <Row label="Sequence Length" value={`${m.sequenceLength} windows`} />
                <Row label="Window Duration" value={`${m.windowDurationSec}s`} />
                <Row label="Forecast Horizon" value={`${m.forecastHorizon} steps`} />
                <Row label="Inference Latency" value={`${m.inferenceLatencyMs} ms`} />
                <Row label="Last Trained" value={formatRelativeTime(m.lastTrained)} />
              </dl>
              <div className="mt-3 pt-3 border-t border-border">
                <div className="text-[10px] uppercase tracking-wide text-text-muted mb-1">Training Corpus</div>
                <div className="text-xs text-text-primary">
                  {m.trainingCorpus?.name} — {formatNumber(m.trainingCorpus?.recordCount)} flow records
                </div>
                <p className="text-[11px] text-text-muted mt-1">
                  The full corpus is used for training only. Inference operates on a rolling
                  window of {m.sequenceLength} states × {m.stateFeatures} features, not the raw
                  dataset.
                </p>
              </div>
            </Panel>

            <Panel title="Resource Usage">
              <div className="space-y-4">
                <Bar used={m.memory?.gpuVramUsedMb} total={m.memory?.gpuVramTotalMb} label="GPU VRAM" />
                <Bar used={m.memory?.ramUsedMb} total={m.memory?.ramTotalMb} label="System RAM" />
              </div>
            </Panel>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Panel title="Evaluation Metrics">
              <div className="grid grid-cols-3 gap-3">
                <MetricCard label="F1" value={m.performance?.f1?.toFixed(2)} tone="healthy" />
                <MetricCard label="Precision" value={m.performance?.precision?.toFixed(2)} />
                <MetricCard label="Recall" value={m.performance?.recall?.toFixed(2)} />
                <MetricCard label="ROC-AUC" value={m.performance?.rocAuc?.toFixed(2)} />
                <MetricCard label="Lead Time" value={`+${m.performance?.leadTimeSec}`} unit="sec" tone="accent" />
              </div>
            </Panel>

            <Panel title="K-Step Forecast Error">
              {m.performance?.kStepError?.length > 0 ? (
                <KStepErrorChart data={m.performance.kStepError} />
              ) : (
                <p className="text-xs text-text-muted">No forecast-error evaluation available.</p>
              )}
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div>
      <dt className="text-text-muted mb-0.5">{label}</dt>
      <dd className="text-text-primary font-mono">{value ?? '—'}</dd>
    </div>
  );
}

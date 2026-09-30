import { useState } from 'react';
import Panel from '../components/common/Panel.jsx';
import MetricCard from '../components/common/MetricCard.jsx';
import { LoadingState, ErrorState, EmptyState } from '../components/common/AsyncStates.jsx';
import RiskForecastChart from '../components/forecast/RiskForecastChart.jsx';
import FutureStateTimeline from '../components/forecast/FutureStateTimeline.jsx';
import { useForecast, useRiskTimeline } from '../hooks/useForecast.js';
import { useNetworkState } from '../hooks/useNetworkState.js';
import { useModelStatus } from '../hooks/useModelStatus.js';
import { formatPercent, riskLevel } from '../utils/formatters.js';

export default function ForecastPage() {
  const network = useNetworkState();
  const forecast = useForecast(5);
  const riskTimeline = useRiskTimeline();
  const model = useModelStatus();
  const [selected, setSelected] = useState(null);

  // Real, backend-computed lead time (index-based early-warning estimate,
  // converted via a nominal window duration -- see live_engine._compute_performance),
  // never a fabricated placeholder. Shown only when the backend actually
  // has one; otherwise the card reads "—".
  const leadTimeSec = model.data?.performance?.leadTimeSec;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-text-primary">Forecast</h1>
        <p className="text-xs text-text-secondary mt-0.5">
          The World Model's rollout of network state S<sub>t</sub> through S<sub>t+K</sub>. Risk score is a
          heuristic anomaly measure, not a calibrated probability of attack.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Forecast Risk Score"
          value={forecast.loading ? '—' : formatPercent(forecast.data?.riskScore)}
          tone={riskLevel(forecast.data?.riskScore)}
          sub={forecast.data?.modelStable === false ? 'degraded — see states below' : undefined}
        />
        <MetricCard
          label="Peak Forecast Risk"
          value={forecast.loading ? '—' : formatPercent(forecast.data?.peakRisk)}
          tone={riskLevel(forecast.data?.peakRisk)}
        />
        <MetricCard
          label="Horizon"
          value={forecast.loading ? '—' : `+${forecast.data?.horizon ?? '—'}`}
          unit="windows"
        />
        <MetricCard
          label="Estimated Lead Time"
          value={leadTimeSec != null ? `+${leadTimeSec}` : '—'}
          unit={leadTimeSec != null ? 'sec' : undefined}
          sub="Nominal, index-based estimate from the last model evaluation — not measured wall-clock time."
        />
      </div>

      <Panel title="Risk Timeline — Observed vs. Forecast">
        {riskTimeline.loading && <LoadingState label="Computing forecast…" />}
        {!riskTimeline.loading && riskTimeline.error && <ErrorState onRetry={riskTimeline.refresh} />}
        {!riskTimeline.loading && riskTimeline.data && <RiskForecastChart timeline={riskTimeline.data} />}
      </Panel>

      <Panel title="K-Step World Model — Predicted Future States">
        {forecast.loading && <LoadingState label="Rolling out future network states…" />}
        {!forecast.loading && forecast.error && <ErrorState onRetry={forecast.refresh} />}
        {!forecast.loading && forecast.data && (
          <FutureStateTimeline
            current={network.data}
            states={forecast.data.states}
            selectedStep={selected?.step}
            onSelect={setSelected}
          />
        )}
      </Panel>

      <Panel title="State Inspector">
        {!selected && (
          <EmptyState title="NO STATE SELECTED" message="Select a state above to inspect its detail." />
        )}
        {selected && (
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <Row label="Window" value={selected.windowId} mono />
            <Row label="Risk" value={formatPercent(selected.riskScore)} />
            <Row label="Predicted Stage" value={selected.stage ?? (selected.isCurrent ? undefined : 'unstable — held steady')} />
            <Row label="Offset" value={selected.isCurrent ? 'Current' : `+${selected.step} windows`} />
          </dl>
        )}
      </Panel>
    </div>
  );
}

function Row({ label, value, mono }) {
  return (
    <div>
      <dt className="text-text-muted mb-0.5">{label}</dt>
      <dd className={`text-text-primary ${mono ? 'font-mono' : ''}`}>{value ?? '—'}</dd>
    </div>
  );
}

import { useState } from 'react';
import { Link } from 'react-router-dom';
import Panel from '../components/common/Panel.jsx';
import MetricCard from '../components/common/MetricCard.jsx';
import SectionHeader from '../components/common/SectionHeader.jsx';
import { LoadingState, ErrorState } from '../components/common/AsyncStates.jsx';
import NetworkThreatMap from '../components/overview/NetworkThreatMap.jsx';
import RiskForecastChart from '../components/forecast/RiskForecastChart.jsx';
import AttackProgressionTimeline from '../components/forecast/AttackProgressionTimeline.jsx';
import ExplanationPanel from '../components/explainability/ExplanationPanel.jsx';
import { useNetworkState } from '../hooks/useNetworkState.js';
import { useAttackPath } from '../hooks/useAttackPath.js';
import { useForecast, useRiskTimeline, useAttackStages } from '../hooks/useForecast.js';
import { useIncidents } from '../hooks/useIncidents.js';
import { useModelStatus } from '../hooks/useModelStatus.js';
import { useExplanation } from '../hooks/useExplanation.js';
import { formatPercent, riskLevel } from '../utils/formatters.js';

export default function Overview() {
  const network = useNetworkState();
  const attackPath = useAttackPath();
  const forecast = useForecast(5);
  const riskTimeline = useRiskTimeline();
  const attackStages = useAttackStages();
  const incidents = useIncidents();
  const modelStatus = useModelStatus();
  const explanation = useExplanation();
  const [selectedStage, setSelectedStage] = useState(null);

  const currentRisk = network.data?.riskScore;
  const forecastRisk = forecast.data?.riskScore;
  const activeIncidentCount = incidents.data?.filter((i) => i.status !== 'RESOLVED')?.length;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-text-primary">Overview</h1>
        <p className="text-xs text-text-secondary mt-0.5">
          Current network posture and where the model expects it to move next.
        </p>
      </div>

      {/* Threat posture row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard
          label="Current Risk"
          value={network.loading ? '—' : formatPercent(currentRisk)}
          tone={riskLevel(currentRisk)}
        />
        <MetricCard
          label="Forecast Risk"
          value={forecast.loading ? '—' : formatPercent(forecastRisk)}
          tone={riskLevel(forecastRisk)}
          sub={forecast.data ? `+${forecast.data.horizon} windows out` : undefined}
        />
        <MetricCard
          label="Current Stage"
          value={network.loading ? '—' : network.data?.stage?.name ?? 'Unknown'}
          tone="accent"
        />
        <MetricCard
          label="Forecast Horizon"
          value={forecast.loading ? '—' : `+${forecast.data?.horizon ?? '—'}`}
          unit="windows"
          tone="neutral"
        />
        <MetricCard
          label="Active Incidents"
          value={incidents.loading ? '—' : activeIncidentCount ?? 0}
          tone={activeIncidentCount > 0 ? 'warning' : 'healthy'}
        />
        <MetricCard
          label="World Model"
          value={modelStatus.loading ? '—' : modelStatus.data?.status === 'ready' ? 'Active' : 'Offline'}
          tone={modelStatus.data?.status === 'ready' ? 'healthy' : 'critical'}
        />
      </div>

      {/* Network threat map — hero visual */}
      <NetworkThreatMap data={attackPath.data} loading={attackPath.loading} error={attackPath.error} onRetry={attackPath.refresh} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel
          title="Future Risk Forecast"
          action={
            <Link to="/forecast" className="text-xs text-accent hover:text-accent-bright">
              Open Forecast →
            </Link>
          }
        >
          {riskTimeline.loading && <LoadingState label="Computing forecast…" />}
          {!riskTimeline.loading && riskTimeline.error && <ErrorState onRetry={riskTimeline.refresh} />}
          {!riskTimeline.loading && riskTimeline.data && (
            <>
              <RiskForecastChart timeline={riskTimeline.data} />
              <div className="flex items-center gap-5 mt-1 text-[11px] text-text-secondary">
                <span className="flex items-center gap-1.5">
                  <span className="inline-block w-4 h-[2px] bg-accent" /> Observed
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="inline-block w-4 h-[2px] bg-predicted" style={{ borderTop: '2px dashed #8B7FE8' }} />
                  Forecast
                </span>
              </div>
            </>
          )}
        </Panel>

        <Panel
          title="Attack Progression"
          action={
            <Link to="/attack-path" className="text-xs text-accent hover:text-accent-bright">
              Open Attack Path →
            </Link>
          }
        >
          {attackStages.loading && <LoadingState label="Mapping attack-stage progression…" />}
          {!attackStages.loading && attackStages.error && <ErrorState onRetry={attackStages.refresh} />}
          {!attackStages.loading && attackStages.data && (
            <AttackProgressionTimeline
              stages={attackStages.data}
              selected={selectedStage}
              onSelect={setSelectedStage}
            />
          )}
        </Panel>
      </div>

      <Panel
        title="Why the Model Forecast This"
        action={
          <Link to="/explainability" className="text-xs text-accent hover:text-accent-bright">
            Open Explainability →
          </Link>
        }
      >
        {explanation.loading && <LoadingState label="Retrieving contributing signals…" />}
        {!explanation.loading && explanation.error && <ErrorState onRetry={explanation.refresh} />}
        {!explanation.loading && !explanation.error && (
          <ExplanationPanel explanation={explanation.data} compact />
        )}
      </Panel>
    </div>
  );
}

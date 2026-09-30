import { EmptyState } from '../common/AsyncStates.jsx';

/** explanation: { forecastId, method, features: [{ name, value, contribution, direction }] } | null */
export default function ExplanationPanel({ explanation, compact = false }) {
  if (!explanation || !explanation.features?.length) {
    return <EmptyState title="EXPLANATION UNAVAILABLE" message="The model did not return contributing signals for this forecast." />;
  }

  const maxContribution = Math.max(...explanation.features.map((f) => Math.abs(f.contribution)));
  const rows = compact ? explanation.features.slice(0, 4) : explanation.features;

  return (
    <div>
      <div className="space-y-2.5">
        {rows.map((f) => {
          const pct = maxContribution ? (Math.abs(f.contribution) / maxContribution) * 100 : 0;
          const barColor = f.direction === 'negative' ? 'bg-healthy' : 'bg-accent';
          return (
            <div key={f.name}>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-text-secondary">{f.name}</span>
                <span className="font-mono text-text-muted">
                  {f.direction === 'negative' ? '−' : '+'}
                  {f.contribution.toFixed(2)}
                </span>
              </div>
              <div className="h-1.5 bg-elevated w-full">
                <div className={`h-full ${barColor}`} style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
      {!compact && (
        <p className="text-xs text-text-muted mt-4 leading-relaxed">
          These are contributing signals identified by the model's{' '}
          <span className="font-mono">{explanation.method}</span> explanation method — supporting
          evidence, not a confirmed cause.
        </p>
      )}
    </div>
  );
}

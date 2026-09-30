const TONE = {
  critical: 'text-critical',
  warning: 'text-warning',
  healthy: 'text-healthy',
  accent: 'text-accent',
  neutral: 'text-text-primary',
};

/**
 * A single operational metric. Value is the hero; label sits below in
 * small caps to match the instrument-panel convention used throughout
 * the app for risk/state readouts.
 */
export default function MetricCard({ label, value, unit, tone = 'neutral', sub, mono = false }) {
  const toneClass = TONE[tone] || TONE.neutral;
  return (
    <div className="border border-border bg-surface px-4 py-3.5 min-w-0">
      <div
        className={`text-2xl font-semibold tabular ${toneClass} ${mono ? 'font-mono' : ''} truncate`}
      >
        {value}
        {unit && <span className="text-base ml-1 text-text-secondary">{unit}</span>}
      </div>
      <div className="mt-1 text-xs tracking-wide uppercase text-text-secondary">{label}</div>
      {sub && <div className="mt-0.5 text-xs text-text-muted">{sub}</div>}
    </div>
  );
}

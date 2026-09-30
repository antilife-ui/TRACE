import { formatPercent, riskLevel } from '../../utils/formatters.js';

const TONE_BORDER = {
  critical: 'border-t-critical',
  warning: 'border-t-warning',
  healthy: 'border-t-healthy',
};

/** states: [{ step, windowId, riskScore, stage }], plus a synthetic "current" card */
export default function FutureStateTimeline({ current, states, selectedStep, onSelect }) {
  const cards = [{ step: 0, windowId: current?.windowId, riskScore: current?.riskScore, stage: current?.stage?.name, isCurrent: true }, ...states];

  return (
    <div className="flex gap-3 overflow-x-auto pb-1">
      {cards.map((c) => {
        const tone = riskLevel(c.riskScore);
        const selected = selectedStep === c.step;
        return (
          <button
            key={c.step}
            onClick={() => onSelect?.(c)}
            className={`shrink-0 w-[150px] text-left bg-surface border border-border border-t-2 ${
              TONE_BORDER[tone] || 'border-t-border'
            } px-3 py-3 transition-colors ${selected ? 'ring-1 ring-accent' : 'hover:border-border-strong'}`}
          >
            <div className="text-[10px] uppercase tracking-wide text-text-muted">
              {c.isCurrent ? 'Current State' : `+${c.step} Window${c.step > 1 ? 's' : ''}`}
            </div>
            <div className="text-xl font-semibold tabular mt-1.5">{formatPercent(c.riskScore)}</div>
            <div className="text-[11px] text-text-secondary mt-1 truncate">{c.stage ?? '—'}</div>
          </button>
        );
      })}
    </div>
  );
}

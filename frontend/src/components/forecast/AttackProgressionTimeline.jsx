const STATUS_STYLE = {
  observed: { dot: 'bg-text-secondary', text: 'text-text-secondary', line: 'bg-text-secondary' },
  current: { dot: 'bg-critical', text: 'text-critical', line: 'bg-critical' },
  predicted: { dot: 'bg-predicted border border-predicted', text: 'text-predicted', line: 'bg-predicted/40' },
};

/** stages: [{ name, status: 'observed'|'current'|'predicted', score, confidence }] */
export default function AttackProgressionTimeline({ stages, onSelect, selected }) {
  return (
    <div className="flex items-start">
      {stages.map((s, i) => {
        const style = STATUS_STYLE[s.status] || STATUS_STYLE.observed;
        const isLast = i === stages.length - 1;
        return (
          <div key={s.name} className="flex items-start flex-1 min-w-0 last:flex-none">
            <div className="flex flex-col items-center min-w-[90px]">
              <button
                onClick={() => onSelect?.(s)}
                className={`w-3 h-3 rounded-full ${style.dot} ${
                  selected?.name === s.name ? 'ring-2 ring-offset-2 ring-offset-surface ring-accent' : ''
                }`}
                aria-label={`${s.name}: ${s.status}`}
              />
              <div className={`mt-2 text-xs font-medium text-center ${style.text}`}>{s.name}</div>
              <div className="text-[10px] uppercase text-text-muted mt-0.5">{s.status}</div>
              {s.confidence != null && (
                <div className="text-[10px] font-mono text-text-muted mt-0.5">
                  conf {Math.round(s.confidence * 100)}%
                </div>
              )}
            </div>
            {!isLast && <div className={`h-[2px] ${style.line} flex-1 mt-[5px] mx-1`} />}
          </div>
        );
      })}
    </div>
  );
}

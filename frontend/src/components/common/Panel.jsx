/**
 * Panel is the one structural surface used throughout TRACE.
 * Deliberately NOT a rounded "SaaS card": sharp corners, a hairline border,
 * and an optional accent-colored left edge to communicate status without
 * tinting the whole surface.
 */
export default function Panel({
  children,
  className = '',
  accent, // 'critical' | 'warning' | 'healthy' | 'accent' | undefined
  title,
  action,
}) {
  const accentBorder = accent
    ? {
        critical: 'border-l-critical',
        warning: 'border-l-warning',
        healthy: 'border-l-healthy',
        accent: 'border-l-accent',
        predicted: 'border-l-predicted',
      }[accent]
    : 'border-l-border';

  return (
    <div
      className={`bg-surface border border-border ${accent ? `border-l-2 ${accentBorder}` : ''} ${className}`}
    >
      {(title || action) && (
        <div className="flex items-center justify-between px-4 pt-3.5 pb-2.5 border-b border-border">
          {title && (
            <h3 className="text-xs tracking-wide text-text-secondary uppercase">{title}</h3>
          )}
          {action}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}

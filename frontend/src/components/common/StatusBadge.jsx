import { AlertTriangle, ShieldAlert, ShieldCheck, HelpCircle, Circle } from 'lucide-react';

const LEVELS = {
  critical: { icon: ShieldAlert, color: 'text-critical', dot: 'bg-critical' },
  warning: { icon: AlertTriangle, color: 'text-warning', dot: 'bg-warning' },
  healthy: { icon: ShieldCheck, color: 'text-healthy', dot: 'bg-healthy' },
  observed: { icon: Circle, color: 'text-text-secondary', dot: 'bg-text-secondary' },
  predicted: { icon: Circle, color: 'text-predicted', dot: 'bg-predicted' },
  unknown: { icon: HelpCircle, color: 'text-text-muted', dot: 'bg-text-muted' },
};

/**
 * level: 'critical' | 'warning' | 'healthy' | 'observed' | 'predicted' | 'unknown'
 * Always pairs color with an icon and text label — never color alone.
 */
export default function StatusBadge({ level = 'unknown', label, dense = false }) {
  const cfg = LEVELS[level] ?? LEVELS.unknown;
  const Icon = cfg.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 ${cfg.color} ${
        dense ? 'text-xs' : 'text-sm'
      } font-medium`}
    >
      <Icon size={dense ? 12 : 14} strokeWidth={2.25} />
      {label}
    </span>
  );
}

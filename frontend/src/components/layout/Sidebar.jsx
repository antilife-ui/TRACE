import { NavLink } from 'react-router-dom';
import {
  LayoutGrid,
  Network,
  TrendingUp,
  Route,
  Radio,
  Lightbulb,
  ShieldAlert,
  Cpu,
} from 'lucide-react';

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutGrid, end: true },
  { to: '/network', label: 'Network', icon: Network },
  { to: '/forecast', label: 'Forecast', icon: TrendingUp },
  { to: '/attack-path', label: 'Attack Path', icon: Route },
  { to: '/telemetry', label: 'Telemetry', icon: Radio },
  { to: '/explainability', label: 'Explainability', icon: Lightbulb },
  { to: '/incidents', label: 'Incidents', icon: ShieldAlert },
  { to: '/model', label: 'Model', icon: Cpu },
];

export default function Sidebar() {
  return (
    <nav className="w-[196px] shrink-0 border-r border-border bg-surface flex flex-col">
      <div className="flex-1 py-3">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-2.5 mx-2 px-3 py-2 mb-0.5 text-sm transition-colors ${
                isActive
                  ? 'bg-elevated text-accent border-l-2 border-accent -ml-[2px] pl-[14px]'
                  : 'text-text-secondary hover:text-text-primary hover:bg-elevated/60'
              }`
            }
          >
            <Icon size={16} strokeWidth={2} />
            {label}
          </NavLink>
        ))}
      </div>
      <div className="px-4 py-3 border-t border-border text-[11px] text-text-muted leading-relaxed">
        SIH26153
        <br />
        Network Attack Forecasting
      </div>
    </nav>
  );
}

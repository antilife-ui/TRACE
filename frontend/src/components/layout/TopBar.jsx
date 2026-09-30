import { DEMO_MODE } from '../../api/client.js';

function Dot({ className }) {
  return <span className={`inline-block w-1.5 h-1.5 rounded-full ${className}`} />;
}

export default function TopBar() {
  return (
    <header className="h-14 shrink-0 border-b border-border bg-surface flex items-center justify-between px-5">
      <div className="flex items-center gap-3">
        <span className="text-[15px] font-semibold tracking-wide text-text-primary">
          TRACE
        </span>
        <span className="text-[11px] text-text-muted hidden md:inline">
          Network Attack Forecasting
        </span>
      </div>

      <div className="flex items-center gap-5 text-xs">
        <div className="flex items-center gap-1.5 text-text-secondary">
          <Dot className="bg-healthy animate-pulseDot" />
          {DEMO_MODE ? 'DEMO MODE' : 'LIVE'}
        </div>
        <div className="hidden sm:flex items-center gap-1.5 text-text-secondary">
          <Dot className="bg-accent" />
          WORLD MODEL: ACTIVE
        </div>
        <div className="hidden lg:flex items-center gap-1.5 text-text-secondary">
          <Dot className="bg-accent animate-pulseDot" />
          TELEMETRY: STREAMING
        </div>
      </div>
    </header>
  );
}

import { Loader2, WifiOff, Inbox } from 'lucide-react';

export function LoadingState({ label = 'Loading data…' }) {
  return (
    <div className="flex items-center gap-2.5 text-text-secondary text-sm py-8 justify-center">
      <Loader2 size={16} className="animate-spin" />
      {label}
    </div>
  );
}

export function ErrorState({ title = 'DATA UNAVAILABLE', message, onRetry }) {
  return (
    <div className="flex flex-col items-center text-center gap-2 py-8">
      <WifiOff size={20} className="text-critical" />
      <div className="text-sm font-semibold text-text-primary">{title}</div>
      <div className="text-xs text-text-secondary max-w-xs">
        {message || 'The backend did not return data for this view.'}
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 text-xs px-3 py-1.5 border border-border-strong text-text-secondary hover:text-text-primary hover:border-accent transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title = 'No data', message }) {
  return (
    <div className="flex flex-col items-center text-center gap-2 py-8">
      <Inbox size={20} className="text-text-muted" />
      <div className="text-sm font-semibold text-text-secondary">{title}</div>
      {message && <div className="text-xs text-text-muted max-w-xs">{message}</div>}
    </div>
  );
}

// Small shared UI primitives: loading / error / empty states, cards, metric tiles, regime badges, JSON.
import type { ReactNode } from 'react';
import type { ApiError } from '../services/apiClient';

export function Card({ title, children, actions }: { title?: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="card">
      {(title || actions) && (
        <header className="card-head">
          {title && <h2>{title}</h2>}
          {actions && <div className="card-actions">{actions}</div>}
        </header>
      )}
      <div className="card-body">{children}</div>
    </section>
  );
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="state loading" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" /> {label}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  return (
    <div className="state error" role="alert">
      <strong>Request failed{error.status ? ` (HTTP ${error.status})` : ''}.</strong>
      <div className="error-detail">{error.detail}</div>
      <div className="error-type">type: {error.error_type}</div>
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ message = 'Nothing here yet.' }: { message?: string }) {
  return (
    <div className="state empty" role="status">
      {message}
    </div>
  );
}

export function MetricTile({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="tile">
      <div className="tile-value">{value}</div>
      <div className="tile-label">{label}</div>
      {hint && <div className="tile-hint">{hint}</div>}
    </div>
  );
}

const REGIME_STYLES: Record<string, string> = {
  SYNTHETIC: 'badge-synthetic',
  DEMO: 'badge-demo',
  REAL: 'badge-real',
  NOT_YET_MEASURED: 'badge-pending',
  DEFERRED: 'badge-deferred',
};

export function RegimeBadge({ regime, title }: { regime: string; title?: string }) {
  const cls = REGIME_STYLES[regime.toUpperCase()] ?? 'badge-neutral';
  return (
    <span className={`badge ${cls}`} title={title ?? regime}>
      {regime}
    </span>
  );
}

export function JsonBlock({ value }: { value: unknown }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}
